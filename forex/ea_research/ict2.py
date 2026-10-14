"""ICT2 exactly as in PREREG_ICT2.md: SMT divergence, the ICT 2022 model (sweep -> MSS -> FVG), NWOG.
   python -m forex.ea_research.ict2 --dry     counts, truncation test, hand check (no P&L)
   python -m forex.ea_research.ict2           real run + placebo worlds 41-43"""
import glob
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass

END = pd.Timestamp("2026-01-01").timestamp()           # 2026 sealed
H = 3600
KZ = {"LONDON": (2 * H, 5 * H, -4 * H, 0), "NYAM": (7 * H, 10 * H, 2 * H, 5 * H)}   # kz start/end, ref start/end (NY seconds of day)
PAIRS = (("EURUSD", "GBPUSD"), ("AUDUSD", "NZDUSD"), ("EURJPY", "GBPJPY"), ("NSDQ", "SP"), ("SP", "DOW"), ("XAUUSD", "XAGUSD"), ("BTCUSD", "ETHUSD"))
SEEDS = (41, 42, 43)
DEV = ("2022-01-01", "2024-12-31")
VAL = ("2025-01-01", "2025-12-31")
YEARS = (2022, 2023, 2024, 2025)
OUT = Path("D:/finance/si_ledgers")
SYMS = sorted(Path(p).name.replace("_M1_rates.parquet", "") for p in glob.glob("forex/data_mt5/*_M1_rates.parquet"))


def prep(sym, end=END):
    d = pd.read_parquet(f"forex/data_mt5/{sym}_M1_rates.parquet")
    d = d[(d.t < end) & (d.bo > 0) & (d.ao >= d.bo)].drop_duplicates("t").sort_values("t")
    D = {c: d[c].to_numpy() for c in ("t", "bo", "bh", "bl", "ao", "ah", "al", "bc", "ac")}
    t = D["t"]
    hrs = np.unique(t // H)
    srv = pd.DatetimeIndex(pd.to_datetime(hrs * H, unit="s"))
    loc = srv.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT")
    ny = loc.tz_convert("America/New_York").tz_localize(None)
    off = pd.Series((srv - ny).total_seconds().to_numpy()).ffill().bfill().to_numpy().astype(np.int64)
    D["ny"] = t - off[np.searchsorted(hrs, t // H)]
    D["mh"] = (D["bh"] + D["ah"]) / 2
    D["ml"] = (D["bl"] + D["al"]) / 2
    D["mc"] = (D["bc"] + D["ac"]) / 2
    D["mo"] = (D["bo"] + D["ao"]) / 2
    key = D["ny"] // 300
    st = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    en = np.r_[st[1:], len(t)]
    D["t5"] = key[st] * 300
    D["h5"] = np.maximum.reduceat(D["mh"], st)
    D["l5"] = np.minimum.reduceat(D["ml"], st)
    D["c5"] = D["mc"][en - 1]
    D["last1"] = en - 1
    return D


def fix_minute(D, k):
    return k + 1 if k + 1 < len(D["t"]) and D["t"][k] % H < 60 else k


def exit_index(D, k, ny_exit):
    j = np.searchsorted(D["ny"], ny_exit)
    day_end = np.searchsorted(D["ny"], (D["ny"][k] // 86400 + 1) * 86400) - 1
    return int(min(j, day_end)) if j < len(D["t"]) else int(day_end)


def sim(D, k, side, entry, stop, target, kend):
    """position filled in minute k at `entry`; returns (net R, gross R) or None."""
    if kend <= k:
        return None
    if side > 0:
        if not (stop < entry < target):
            return None
        sl = np.flatnonzero(D["bl"][k:kend] <= stop)
        tp = np.flatnonzero(D["bh"][k:kend] >= target)
    else:
        if not (target < entry < stop):
            return None
        sl = np.flatnonzero(D["ah"][k:kend] >= stop)
        tp = np.flatnonzero(D["al"][k:kend] <= target)
    i_s = sl[0] if len(sl) else 10**9
    i_t = tp[0] if len(tp) else 10**9
    if i_s == 10**9 and i_t == 10**9:
        j = kend
        x = D["bo"][j] if side > 0 else D["ao"][j]
    elif i_s <= i_t:
        j = k + i_s
        x = min(stop, D["bo"][j]) if side > 0 else max(stop, D["ao"][j])
    else:
        j = k + i_t
        x = target
    risk = abs(entry - stop)
    net = side * (x - entry) / risk
    sp = (D["ao"][k] - D["bo"][k] + D["ao"][j] - D["bo"][j]) / 2
    return net, net + sp / risk


def market_entry(D, k, side, stop_dist_frac, mult, kend):
    k = fix_minute(D, k)
    e = D["ao"][k] if side > 0 else D["bo"][k]
    stop = e - side * stop_dist_frac * e
    return k, e, stop, e + side * mult * stop_dist_frac * e, kend


def rec(sym, cell, world, D, k, side, r, extra=""):
    return (sym, cell, world, pd.Timestamp(int(D["ny"][k] // 86400) * 86400, unit="s"), side, r[0], r[1], int(D["t"][k]), extra)


def kz_bars(D, d, kz):
    s, e, rs, re_ = KZ[kz]
    t5 = D["t5"]
    a, b = np.searchsorted(t5, d * 86400 + s), np.searchsorted(t5, d * 86400 + e)
    ra, rb = np.searchsorted(t5, d * 86400 + rs), np.searchsorted(t5, d * 86400 + re_)
    return a, b, ra, rb


def smt(X, Y, sx):
    """SMT trades on market X (twin Y)."""
    out = []
    days = np.unique(X["t5"] // 86400)
    for d in days:
        for kz in KZ:
            a, b, ra, rb = kz_bars(X, d, kz)
            ya, yb, yra, yrb = kz_bars(Y, d, kz)
            if b - a < 12 or rb - ra < 6 or yb - ya < 12 or yrb - yra < 6:
                continue
            rHx, rLx = X["h5"][ra:rb].max(), X["l5"][ra:rb].min()
            rHy, rLy = Y["h5"][yra:yrb].max(), Y["l5"][yra:yrb].min()
            tx = X["t5"][a:b]
            pos = np.searchsorted(Y["t5"][ya:yb], tx)
            ok = (pos < yb - ya)
            ok[ok] = Y["t5"][ya:yb][pos[ok]] == tx[ok]
            if ok.sum() < 12:
                continue
            ix = np.arange(a, b)[ok]
            iy = ya + pos[ok]
            hx, lx = np.maximum.accumulate(X["h5"][ix]), np.minimum.accumulate(X["l5"][ix])
            hy, ly = np.maximum.accumulate(Y["h5"][iy]), np.minimum.accumulate(Y["l5"][iy])
            bear = (hx > rHx) & (hy <= rHy) & (X["c5"][ix] < rHx)
            bull = (lx < rLx) & (ly >= rLy) & (X["c5"][ix] > rLx)
            sig = np.flatnonzero(bear | bull)
            if not len(sig):
                continue
            j = sig[0]
            if bear[j] and bull[j]:
                continue
            side = -1 if bear[j] else 1
            k = fix_minute(X, X["last1"][ix[j]] + 1)
            e = X["ao"][k] if side > 0 else X["bo"][k]
            stop = hx[j] if side < 0 else lx[j]
            if abs(e - stop) < 2 * (X["ao"][k] - X["bo"][k]):
                continue
            kend = exit_index(X, k, d * 86400 + KZ[kz][1] + 3 * H)
            r = sim(X, k, side, e, stop, e + side * 2 * abs(e - stop), kend)
            if r is not None:
                out.append(rec(sx, "SMT", "real", X, k, side, r, kz) + (abs(e - stop) / e, 2.0))
    return out


def mss(D, sym):
    out = []
    days = np.unique(D["t5"] // 86400)
    h5, l5, c5 = D["h5"], D["l5"], D["c5"]
    for d in days:
        for kz in KZ:
            a, b, ra, rb = kz_bars(D, d, kz)
            if b - a < 12 or rb - ra < 6 or a < 5:
                continue
            rH, rL = h5[ra:rb].max(), l5[ra:rb].min()
            up, dn = h5[a:b] > rH, l5[a:b] < rL
            sw = np.flatnonzero(up | dn)
            if not len(sw):
                continue
            i = a + sw[0]
            if up[sw[0]] and dn[sw[0]]:
                continue
            side = -1 if up[sw[0]] else 1
            swing = l5[i - 5:i].min() if side < 0 else h5[i - 5:i].max()
            ms = [m for m in range(i + 1, min(i + 13, b)) if (c5[m] < swing if side < 0 else c5[m] > swing)]
            if not ms:
                continue
            m = ms[0]
            fv = [k for k in range(max(i + 2, m - 2), min(m + 3, b)) if (h5[k] < l5[k - 2] if side < 0 else l5[k] > h5[k - 2])]
            if not fv:
                continue
            k5 = fv[0]
            lim = (h5[k5] + l5[k5 - 2]) / 2 if side < 0 else (l5[k5] + h5[k5 - 2]) / 2
            ext = h5[i:k5 + 1].max() if side < 0 else l5[i:k5 + 1].min()
            s1 = D["last1"][k5] + 1
            e1 = D["last1"][min(k5 + 6, len(h5) - 1)]
            if s1 > e1:
                continue
            hit = np.flatnonzero(D["bh"][s1:e1 + 1] >= lim) if side < 0 else np.flatnonzero(D["al"][s1:e1 + 1] <= lim)
            if not len(hit):
                continue
            k = s1 + hit[0]
            e = max(lim, D["bo"][k]) if side < 0 else min(lim, D["ao"][k])
            if abs(e - ext) < 2 * (D["ao"][k] - D["bo"][k]):
                continue
            kend = exit_index(D, k, d * 86400 + KZ[kz][1] + 3 * H)
            r = sim(D, k, side, e, ext, e + side * 2 * abs(e - ext), kend)
            if r is not None:
                out.append(rec(sym, "MSS2022", "real", D, k, side, r, kz) + (abs(e - ext) / e, 2.0))
    return out


def nwog(D, sym):
    out = []
    t = D["t"]
    day = t // 86400
    sod = t % 86400
    wd = (day + 3) % 7
    udays = np.unique(day)
    for m in udays[(udays + 3) % 7 == 0]:
        f = m - 3
        fr = np.flatnonzero((day == f) & (sod < 23 * H))
        if not len(fr):
            continue
        C = D["mc"][fr[-1]]
        mo_ = np.flatnonzero(day == m)
        if not len(mo_):
            continue
        k1 = mo_[np.searchsorted(sod[mo_], H + 300)] if np.searchsorted(sod[mo_], H + 300) < len(mo_) else None
        p2 = np.searchsorted(sod[mo_], 2 * H + 300)
        if k1 is None or p2 >= len(mo_):
            continue
        k = mo_[p2]
        if sod[k] >= 3 * H:
            continue
        O = D["mo"][k1]
        seg = np.arange(k1, k)
        if len(seg) and (D["mh"][seg].max() >= C if C > O else D["ml"][seg].min() <= C):
            continue
        prev = np.flatnonzero((day < m) & (day >= m - 9) & (sod >= H) & (sod < 23 * H))
        if not len(prev):
            continue
        pdays = day[prev]
        last5 = np.unique(pdays)[-5:]
        adr = np.mean([D["mh"][prev[pdays == x]].max() - D["ml"][prev[pdays == x]].min() for x in last5])
        O2 = D["mo"][k]
        dist = C - O2
        if not adr > 0 or abs(dist) < 0.1 * adr:
            continue
        side = 1 if dist > 0 else -1
        k = fix_minute(D, k)
        e = D["ao"][k] if side > 0 else D["bo"][k]
        pe = np.searchsorted(sod[mo_], 22 * H + 55 * 60)
        kend = mo_[pe] if pe < len(mo_) else mo_[-1]
        r = sim(D, k, side, e, e - side * abs(C - e), C, kend)
        if r is not None:
            out.append(rec(sym, "NWOG", "real", D, k, side, r, "MON") + (abs(C - e) / e, 1.0))
    return out


def placebo(D, sym, real):
    """re-enter every real trade on a random other day of the same period, random minute of the same window."""
    out = []
    ny = D["ny"]
    nyday = ny // 86400
    days_all = np.unique(nyday)
    srv_day = D["t"] // 86400
    mondays = np.unique(srv_day[(srv_day + 3) % 7 == 0])
    for sd in SEEDS:
        rng = np.random.default_rng([sd, zlib.crc32(sym.encode())])
        for (s, cell, _, dts, side, _, _, _, kz, frac, mult) in real:
            dev = dts <= pd.Timestamp(DEV[1])
            lo, hi = (pd.Timestamp(DEV[0]), pd.Timestamp(DEV[1])) if dev else (pd.Timestamp(VAL[0]), pd.Timestamp(VAL[1]))
            if cell == "NWOG":
                cand = mondays[(mondays * 86400 >= lo.timestamp()) & (mondays * 86400 <= hi.timestamp())]
                if not len(cand):
                    continue
                m = rng.choice(cand)
                idx = np.flatnonzero(srv_day == m)
                p = np.searchsorted(D["t"][idx] % 86400, 2 * H + 300)
                if p >= len(idx):
                    continue
                k = idx[p]
                pe = np.searchsorted(D["t"][idx] % 86400, 22 * H + 55 * 60)
                kend = idx[pe] if pe < len(idx) else idx[-1]
            else:
                cand = days_all[(days_all * 86400 >= lo.timestamp()) & (days_all * 86400 <= hi.timestamp())]
                d = rng.choice(cand)
                s0, e0 = d * 86400 + KZ[kz][0], d * 86400 + KZ[kz][1]
                a, b = np.searchsorted(ny, s0), np.searchsorted(ny, e0)
                if b - a < 30:
                    continue
                k = int(rng.integers(a, b))
                kend = exit_index(D, k, e0 + 3 * H)
            k, e, stop, tgt, kend = market_entry(D, k, side, frac, mult, kend)
            r = sim(D, k, side, e, stop, tgt, kend)
            if r is not None:
                out.append(rec(sym, cell, str(sd), D, k, side, r, kz) + (frac, mult))
    return out


def work(args):
    sym, end, with_placebo = args
    D = prep(sym, end)
    real = mss(D, sym)
    if mclass(sym) != "crypto":
        real += nwog(D, sym)
    for x, y in PAIRS:
        for a_, b_ in ((x, y), (y, x)):
            if a_ == sym:
                real += smt(D, prep(b_, end), sym)
    return real + (placebo(D, sym, real) if with_placebo else [])


COLS = ["mkt", "cell", "world", "day", "side", "R", "gR", "t_entry", "kz", "frac", "mult"]


def nw_t(x, lag=1):
    x = np.asarray(x, float)
    n = len(x)
    if n < 10:
        return 0.0
    e = x - x.mean()
    s = e @ e / n
    for l in range(1, lag + 1):
        s += 2 * (1 - l / (lag + 1)) * (e[l:] @ e[:-l]) / n
    return x.mean() / np.sqrt(s / n)


def collect(end, with_placebo, syms=SYMS):
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(work, [(s, end, with_placebo) for s in syms]))
    df = pd.DataFrame([r for rr in res for r in rr], columns=COLS)
    df["world"] = df.world.astype(str)
    return df[df.day >= pd.Timestamp(DEV[0])]


def dry():
    t0 = time.time()
    df = collect(END, False)
    df["per"] = np.where(df.day <= DEV[1], "DEV", "VAL")
    print(f"{time.time() - t0:.0f}s")
    print(df.groupby(["cell", "per"]).size().unstack())
    print("SMT trades by market (DEV):", df[(df.cell == "SMT") & (df.per == "DEV")].mkt.value_counts().to_dict())
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    bad = 0
    for s in ("EURUSD", "XAUUSD", "SP", "DAX"):
        full = pd.DataFrame(work((s, END, False)), columns=COLS)
        part = pd.DataFrame(work((s, cut, False)), columns=COLS)
        f = full[full.t_entry < cut - 86400].sort_values(["t_entry", "cell"]).reset_index(drop=True)
        p = part[part.t_entry < cut - 86400].sort_values(["t_entry", "cell"]).reset_index(drop=True)
        bad += int(not (len(f) == len(p) and np.allclose(f.R, p.R) and (f.side.values == p.side.values).all()))
    print("truncation test:", "PASS" if bad == 0 else f"FAIL {bad}")
    x = df[(df.cell == "SMT") & (df.mkt == "EURUSD")].iloc[100]
    print("hand check SMT:", x.mkt, x.kz, "side", x.side, "entry (server)", pd.Timestamp(x.t_entry, unit="s"), "stop frac", round(x.frac, 5))
    X, Y = prep("EURUSD"), prep("GBPUSD")
    d = int(x.day.timestamp() // 86400)
    for nm, Dd in (("EURUSD", X), ("GBPUSD", Y)):
        a, b, ra, rb = kz_bars(Dd, d, x.kz)
        kb = np.searchsorted(Dd["t5"], Dd["ny"][np.searchsorted(Dd["t"], x.t_entry)] // 300 * 300)
        print(f"   {nm}: ref high {Dd['h5'][ra:rb].max():.5f} low {Dd['l5'][ra:rb].min():.5f} | kz high to entry {Dd['h5'][a:kb].max():.5f} low {Dd['l5'][a:kb].min():.5f}")


def run():
    t0 = time.time()
    df = collect(END, True)
    print(f"run {time.time() - t0:.0f}s, {len(df)} trades", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT / "ICT2_trades.parquet")
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
    R.to_csv(OUT / "ICT2_cells.csv", index=False)
    pd.set_option("display.width", 220)
    print(R.round(3).to_string(index=False))
    plc = R[R.world != "real"]
    ceil = np.percentile(plc.tD, 95)
    print(f"\nplacebo (9 cells): max DEV t {plc.tD.max():.2f}, 95th pct {ceil:.2f}")
    for _, r in R[R.world == "real"].iterrows():
        dv = df[(df.cell == r.cell) & (df.world == "real") & (df.day <= DEV[1])]
        bym = dv.groupby("mkt").R.sum()
        conc = bym.max() / bym.sum() if bym.sum() > 0 else np.inf
        g = [r.mD >= 0.05 and r.tD >= 2.40, r.mV > 0 and r.tV >= 1.65, sum(r[f"y{y % 100}"] > 0 for y in YEARS) >= 3, r.tD > ceil, conc <= 0.40]
        print(f"{r.cell}: DEV n {r.nD} net {r.mD:+.3f}R (gross {r.gD:+.3f}) t {r.tD:+.2f} | VAL n {r.nV} net {r.mV:+.3f}R (gross {r.gV:+.3f}) t {r.tV:+.2f} | "
              f"years {r.y22:+.3f}/{r.y23:+.3f}/{r.y24:+.3f}/{r.y25:+.3f} | top market {conc:.2f} | gates {''.join('Y' if x else 'n' for x in g)} PASS {all(g)}")
        cls = dv.assign(c=dv.mkt.map(mclass)).groupby("c").agg(n=("R", "size"), R=("R", "mean"), gR=("gR", "mean"))
        print("   DEV by class:", "; ".join(f"{c} n{int(x.n)} net {x.R:+.3f} gross {x.gR:+.3f}" for c, x in cls.iterrows()))


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
