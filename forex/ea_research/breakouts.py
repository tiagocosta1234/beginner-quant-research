"""BRK exactly as in PREREG_BREAKOUTS.md: opening-range, Asian-range, Bollinger-squeeze and previous-day breakouts on every MT5 broker market.
   python -m forex.ea_research.breakouts --dry     counts, truncation test, hand check (no P&L)
   python -m forex.ea_research.breakouts           real run + placebo worlds 71-73"""
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS, fix_minute, nw_t, sim

END = pd.Timestamp("2026-01-01").timestamp()           # 2026 sealed
H, M = 3600, 60
SEEDS = (71, 72, 73)
DEV = ("2022-01-01", "2024-12-31")
VAL = ("2025-01-01", "2025-12-31")
YEARS = (2022, 2023, 2024, 2025)
COLS = ["mkt", "cell", "world", "day", "side", "R", "gR", "t_entry", "fs"]


def session(sym):
    c = mclass(sym)
    if sym in ("SP", "NSDQ", "DOW") or c == "crypto":
        return "America/New_York", 9 * H + 30 * M, 16 * H
    if c == "energy":
        return "America/New_York", 9 * H, 14 * H + 30 * M
    if sym == "DAX":
        return "Europe/Berlin", 9 * H, 17 * H + 30 * M
    if sym == "NIKKEI":
        return "Asia/Tokyo", 9 * H, 15 * H
    if sym == "ASX":
        return "Australia/Sydney", 10 * H, 16 * H
    return "Europe/London", 8 * H, 17 * H


def local_clock(t, tz):
    hrs = np.unique(t // H)
    srv = pd.DatetimeIndex(pd.to_datetime(hrs * H, unit="s"))
    lt = srv.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").tz_convert(tz).tz_localize(None)
    off = pd.Series((srv - lt).total_seconds().to_numpy()).ffill().bfill().to_numpy().astype(np.int64)
    return t - off[np.searchsorted(hrs, t // H)]


def cap_exit(D, k, j):
    """exit index j, capped at 22:55 server of the entry's server day and never before k+1."""
    t = D["t"]
    lim = np.searchsorted(t, (t[k] // 86400) * 86400 + 22 * H + 55 * M)
    j = min(j, lim, len(t) - 1)
    if t[j] % 86400 >= 23 * H:
        j -= 1
    return j if j > k else None


def m5_closes(D, lc, a, b):
    """M5 buckets (local clock) of M1 indices a..b-1: (last M1 index, mid close, bucket start)."""
    if b <= a:
        return np.array([], int), np.array([]), np.array([], int)
    key = lc[a:b] // 300
    last = np.flatnonzero(np.r_[key[1:] != key[:-1], True]) + a
    return last, D["mc"][last], key[last - a] * 300


def range_break(D, lc, d, r0, r1, w0, w1, x1, sym, cell, out_rows, world="real", forced=None, rng=None):
    """generic range breakout on local day d: range [r0, r1), entry window [w0, w1), exit at x1 (local seconds of day)."""
    i = lambda s: np.searchsorted(lc, d * 86400 + s)
    ra, rb, wa, wb, xb = i(r0), i(r1), i(w0), i(w1), i(x1)
    if xb >= len(lc) or lc[xb] // 86400 != d:
        xb -= 1                                    # no bar at the close: last bar before it
    if rb - ra < 20 or wb - wa < 30 or xb >= len(lc) or lc[xb] // 86400 != d:
        return
    hi, lo = D["mh"][ra:rb].max(), D["ml"][ra:rb].min()
    if forced is None:
        last, c, _ = m5_closes(D, lc, wa, wb)
        up, dn = np.flatnonzero(c > hi), np.flatnonzero(c < lo)
        fu, fd = (up[0] if len(up) else 10**9), (dn[0] if len(dn) else 10**9)
        if fu == fd:
            return
        side = 1 if fu < fd else -1
        k = fix_minute(D, last[min(fu, fd)] + 1)
        e = D["ao"][k] if side > 0 else D["bo"][k]
        stop = lo if side > 0 else hi
    else:
        side, fs = forced
        k = fix_minute(D, int(rng.integers(wa, wb)))
        e = D["ao"][k] if side > 0 else D["bo"][k]
        stop = e - side * fs * e
    j = cap_exit(D, k, xb)
    if j is None or abs(e - stop) < 2 * (D["ao"][k] - D["bo"][k]):
        return
    r = sim(D, k, side, e, stop, e + side * 1e9, j)
    if r is not None:
        out_rows.append((sym, cell, world, pd.Timestamp(d * 86400, unit="s"), side, r[0], r[1], int(D["t"][k]), abs(e - stop) / e))


def h1_bars(D):
    t = D["t"]
    hr = (t // H) % 24
    ok = ~np.isin(hr, (23, 0))
    idx = np.flatnonzero(ok)
    key = t[idx] // H
    st = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    en = np.r_[st[1:], len(idx)]
    first = idx[st]
    hi = np.maximum.reduceat(D["mh"][idx], st)
    lo = np.minimum.reduceat(D["ml"][idx], st)
    cl = D["mc"][idx[en - 1]]
    return first, hi, lo, cl


def h1_cache(D):
    first, hi, lo, cl = h1_bars(D)
    s = pd.Series(cl)
    ma, sd = s.rolling(20).mean().to_numpy(), s.rolling(20).std(ddof=0).to_numpy()
    bw = 4 * sd / ma
    sq = bw <= pd.Series(bw).rolling(120).min().to_numpy()
    tr = np.maximum(hi - lo, np.maximum(np.abs(hi - np.r_[np.nan, cl[:-1]]), np.abs(lo - np.r_[np.nan, cl[:-1]])))
    atr = pd.Series(tr).rolling(14).mean().to_numpy()
    return first, cl, ma, sd, sq, atr


def squeeze(D, sym, out_rows, world="real", plan=None, rng=None):
    first, cl, ma, sd, sq, atr = D["h1"]
    n = len(cl)
    if plan is None:
        busy = -1
        for b in range(121, n - 13):
            if b <= busy or not sq[b - 1]:
                continue
            side = 1 if cl[b] > ma[b] + 2 * sd[b] else (-1 if cl[b] < ma[b] - 2 * sd[b] else 0)
            if side == 0 or not atr[b] > 0:
                continue
            k = fix_minute(D, first[b + 1])
            j = fix_minute(D, first[b + 13])
            e = D["ao"][k] if side > 0 else D["bo"][k]
            stop = e - side * 1.5 * atr[b]
            if abs(e - stop) < 2 * (D["ao"][k] - D["bo"][k]):
                continue
            r = sim(D, k, side, e, stop, e + side * 1e9, j)
            if r is not None:
                out_rows.append((sym, "B3", world, pd.Timestamp((D["t"][k] // 86400) * 86400, unit="s"), side, r[0], r[1], int(D["t"][k]), abs(e - stop) / e))
                busy = b + 12
    else:
        lo_t, hi_t, side, fs = plan
        cand = np.flatnonzero((D["t"][first] >= lo_t) & (D["t"][first] <= hi_t + 86400))
        cand = cand[cand < n - 13]
        if not len(cand):
            return
        b = int(rng.choice(cand))
        k, j = fix_minute(D, first[b]), fix_minute(D, first[b + 12])
        e = D["ao"][k] if side > 0 else D["bo"][k]
        r = sim(D, k, side, e, e - side * fs * e, e + side * 1e9, j)
        if r is not None:
            out_rows.append((sym, "B3", world, pd.Timestamp((D["t"][k] // 86400) * 86400, unit="s"), side, r[0], r[1], int(D["t"][k]), fs))


def day_table(D):
    t = D["t"]
    sday, sod = t // 86400, t % 86400
    st = np.flatnonzero(np.r_[True, sday[1:] != sday[:-1]])
    en = np.r_[st[1:], len(t)]
    days = []
    for a, b in zip(st, en):
        w = np.arange(a, b)[(sod[a:b] >= H) & (sod[a:b] < 23 * H)]
        days.append((int(sday[a]), a, b, D["mh"][w].max() if len(w) >= 300 else np.nan, D["ml"][w].min() if len(w) >= 300 else np.nan))
    return days


def pdhl(D, sym, out_rows, world="real", forced=None, rng=None, day_pick=None):
    t = D["t"]
    sod = t % 86400
    days = D["days"]
    rng_days = range(1, len(days)) if day_pick is None else [day_pick(len(days))]
    for di in rng_days:
        d, a, b, _, _ = days[di]
        pH, pL = days[di - 1][3], days[di - 1][4]
        if not np.isfinite(pH):
            continue
        k0 = a + np.searchsorted(sod[a:b], H + 5 * M)
        wa, wb = a + np.searchsorted(sod[a:b], 9 * H), a + np.searchsorted(sod[a:b], 20 * H)
        xb = a + np.searchsorted(sod[a:b], 22 * H + 55 * M)
        if k0 >= b or wb - wa < 60 or xb >= b:
            continue
        if forced is None:
            if not (pL < D["mo"][k0] < pH):
                continue
            last, c, _ = m5_closes(D, t, wa, wb)
            up, dn = np.flatnonzero(c > pH), np.flatnonzero(c < pL)
            fu, fd = (up[0] if len(up) else 10**9), (dn[0] if len(dn) else 10**9)
            if fu == fd:
                continue
            side = 1 if fu < fd else -1
            k = fix_minute(D, last[min(fu, fd)] + 1)
            e = D["ao"][k] if side > 0 else D["bo"][k]
            stop = (pH - 0.25 * (pH - pL)) if side > 0 else (pL + 0.25 * (pH - pL))
        else:
            side, fs = forced
            k = fix_minute(D, int(rng.integers(wa, wb)))
            e = D["ao"][k] if side > 0 else D["bo"][k]
            stop = e - side * fs * e
        j = cap_exit(D, k, xb)
        if j is None or abs(e - stop) < 2 * (D["ao"][k] - D["bo"][k]):
            continue
        r = sim(D, k, side, e, stop, e + side * 1e9, j)
        if r is not None:
            out_rows.append((sym, "B4", world, pd.Timestamp(d * 86400, unit="s"), side, r[0], r[1], int(D["t"][k]), abs(e - stop) / e))


def market(args):
    sym, end, with_placebo = args
    D = load(sym, end)
    D["mo"] = (D["bo"] + D["ao"]) / 2
    D["h1"], D["days"] = h1_cache(D), day_table(D)
    tz, op, cl = session(sym)
    lc = local_clock(D["t"], tz)
    lon = lc if tz == "Europe/London" else local_clock(D["t"], "Europe/London")
    real = []
    for d in np.unique(lc // 86400):
        range_break(D, lc, d, op, op + 30 * M, op + 30 * M, cl - 60 * M, cl, sym, "B1", real)
    if mclass(sym) in ("fx", "metal"):
        for d in np.unique(lon // 86400):
            range_break(D, lon, d, 0, 7 * H, 7 * H, 12 * H, 17 * H, sym, "B2", real)
    squeeze(D, sym, real)
    pdhl(D, sym, real)
    out = list(real)
    if with_placebo:
        ud_lc, ud_lon, ud_srv = np.unique(lc // 86400), np.unique(lon // 86400), np.unique(D["t"] // 86400)   # computed once (speed only)
        for sd in SEEDS:
            rng = np.random.default_rng([sd, zlib.crc32(sym.encode())])
            for (s, cell, _, day, side, _, _, _, fs) in real:
                lo, hi = (DEV if day <= pd.Timestamp(DEV[1]) else VAL)
                lo_t, hi_t = pd.Timestamp(lo).timestamp(), pd.Timestamp(hi).timestamp()
                if cell in ("B1", "B2"):
                    dd = ud_lc if cell == "B1" else ud_lon
                    dd = dd[(dd * 86400 >= lo_t) & (dd * 86400 <= hi_t)]
                    d = int(rng.choice(dd))
                    if cell == "B1":
                        range_break(D, lc, d, op, op + 30 * M, op + 30 * M, cl - 60 * M, cl, sym, "B1", out, str(sd), (side, fs), rng)
                    else:
                        range_break(D, lon, d, 0, 7 * H, 7 * H, 12 * H, 17 * H, sym, "B2", out, str(sd), (side, fs), rng)
                elif cell == "B3":
                    squeeze(D, sym, out, str(sd), (lo_t, hi_t, side, fs), rng)
                else:
                    cand = np.flatnonzero((ud_srv * 86400 >= lo_t) & (ud_srv * 86400 <= hi_t))
                    pdhl(D, sym, out, str(sd), (side, fs), rng, day_pick=lambda n, c=cand: max(1, int(min(rng.choice(c), n - 1))) if len(c) else 1)
    return out


def collect(end, with_placebo):
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, [(s, end, with_placebo) for s in SYMS]))
    df = pd.DataFrame([r for rr in res for r in rr], columns=COLS)
    return df[df.day >= pd.Timestamp(DEV[0])]


def dry():
    t0 = time.time()
    df = collect(END, False)
    df["per"] = np.where(df.day <= DEV[1], "DEV", "VAL")
    print(f"{time.time() - t0:.0f}s")
    print(df.groupby(["cell", "per"]).size().unstack())
    print("median stop % of price:", (df.groupby("cell").fs.median() * 100).round(3).to_dict())
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    bad = 0
    for s in ("EURUSD", "XAUUSD", "NSDQ", "BTCUSD"):
        f = pd.DataFrame(market((s, END, False)), columns=COLS)
        p = pd.DataFrame(market((s, cut, False)), columns=COLS)
        f = f[f.t_entry < cut - 2 * 86400].sort_values(["t_entry", "cell"]).reset_index(drop=True)
        p = p[p.t_entry < cut - 2 * 86400].sort_values(["t_entry", "cell"]).reset_index(drop=True)
        bad += int(not (len(f) == len(p) and np.allclose(f.R, p.R) and (f.side.values == p.side.values).all()))
    print("truncation test:", "PASS" if bad == 0 else f"FAIL {bad}")
    D = load("NSDQ")
    lc = local_clock(D["t"], "America/New_York")
    g = df[(df.mkt == "NSDQ") & (df.cell == "B1")].iloc[30]
    d = int(g.day.timestamp() // 86400)
    w = (lc >= d * 86400 + 9 * H + 30 * M) & (lc < d * 86400 + 10 * H)
    print(f"hand check NSDQ B1 {g.day.date()}: box {((D['bl'][w] + D['al'][w]) / 2).min():.1f}-{((D['bh'][w] + D['ah'][w]) / 2).max():.1f}, side {g.side}, "
          f"entry {pd.Timestamp(g.t_entry, unit='s')} server = {pd.Timestamp(lc[np.searchsorted(D['t'], g.t_entry)], unit='s')} NY, stop {g.fs * 100:.3f}%")


def run():
    t0 = time.time()
    df = collect(END, True)
    print(f"run {time.time() - t0:.0f}s, {len(df)} trades", flush=True)
    df.to_parquet("D:/finance/si_ledgers/BRK_trades.parquet")
    rows = []
    for (cell, world), g in df.groupby(["cell", "world"]):
        r = dict(cell=cell, world=world)
        for per, (a, b) in (("D", DEV), ("V", VAL)):
            x = g[(g.day >= a) & (g.day <= b)]
            r[f"n{per}"], r[f"m{per}"], r[f"g{per}"] = len(x), x.R.mean(), x.gR.mean()
            r[f"t{per}"] = nw_t(x.groupby("day").R.mean().to_numpy())
        for y in YEARS:
            r[f"y{y % 100}"] = g[g.day.dt.year == y].R.mean()
        rows.append(r)
    R = pd.DataFrame(rows)
    R.to_csv("D:/finance/si_ledgers/BRK_cells.csv", index=False)
    pd.set_option("display.width", 220)
    print(R.round(3).to_string(index=False))
    plc = R[R.world != "real"]
    ceil = np.percentile(plc.tD, 95)
    print(f"\nplacebo (12 cells): max DEV t {plc.tD.max():.2f}, 95th pct {ceil:.2f}")
    for _, r in R[R.world == "real"].iterrows():
        allr = df[(df.cell == r.cell) & (df.world == "real")]
        dv = allr[allr.day <= DEV[1]]
        bym = dv.groupby("mkt").R.sum()
        conc = bym.max() / bym.sum() if bym.sum() > 0 else np.inf
        g = [r.mD >= 0.05 and r.tD >= 2.50, r.mV > 0 and r.tV >= 1.65, sum(r[f"y{y % 100}"] > 0 for y in YEARS) >= 3, r.tD > ceil, conc <= 0.40]
        print(f"{r.cell}: DEV n {r.nD} net {r.mD:+.3f}R (gross {r.gD:+.3f}) t {r.tD:+.2f} | VAL n {r.nV} net {r.mV:+.3f}R (gross {r.gV:+.3f}) t {r.tV:+.2f} | "
              f"years {r.y22:+.3f}/{r.y23:+.3f}/{r.y24:+.3f}/{r.y25:+.3f} | top market {conc:.2f} | win {(dv.R > 0).mean():.1%} median {dv.R.median():+.2f} | gates {''.join('Y' if x else 'n' for x in g)} PASS {all(g)}")
        cls = allr.assign(c=allr.mkt.map(mclass), per=np.where(allr.day <= DEV[1], "DEV", "VAL")).groupby(["c", "per"]).agg(n=("R", "size"), R=("R", "mean"), gR=("gR", "mean"))
        print("  ", "; ".join(f"{c}/{p} n{int(x.n)} {x.R:+.3f} (g {x.gR:+.3f})" for (c, p), x in cls.iterrows()))
        bm = allr.assign(per=np.where(allr.day <= DEV[1], "D", "V")).groupby(["mkt", "per"]).R.mean().unstack()
        both = bm[(bm.D > 0) & (bm.V > 0)].round(3)
        print(f"   markets positive in both DEV and VAL: {len(both)} of {len(bm)}:", both.to_dict("index") if len(both) <= 12 else len(both))


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
