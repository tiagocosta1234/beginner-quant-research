"""MPROFILE exactly as in PREREG_MPROFILE.md (market-profile plays on every MT5 broker market).
   python -m forex.ea_research.mprofile --dry     counts, truncation test, hand check (no P&L)
   python -m forex.ea_research.mprofile           real run + placebo-level worlds 95-97"""
import glob
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

END = pd.Timestamp("2026-01-01").timestamp()           # 2026 sealed
NB, VA_SHARE = 50, 0.70
WORLDS = ("real", 95, 96, 97)
CELLS = ("VA80", "DRIVE", "EDGE", "NPOC")
DEV = ("2022-01-01", "2024-12-31")
VAL = ("2025-01-01", "2025-12-31")
YEARS = ("2022", "2023", "2024", "2025")
OUT = Path("D:/finance/si_ledgers")
SYMS = sorted(Path(p).name.replace("_M1_rates.parquet", "") for p in glob.glob("forex/data_mt5/*_M1_rates.parquet"))


def load(sym, end=END):
    d = pd.read_parquet(f"forex/data_mt5/{sym}_M1_rates.parquet")
    d = d[(d.t < end) & (d.bo > 0) & (d.ao >= d.bo)].drop_duplicates("t").sort_values("t")
    return {c: d[c].to_numpy() for c in ("t", "bo", "bh", "bl", "ao", "ah", "al", "bc", "ac")}


def profile(mh, ml):
    lo, hi = ml.min(), mh.max()
    w = (hi - lo) / NB
    if not w > 0:
        return None
    il = np.clip(((ml - lo) / w).astype(int), 0, NB - 1)
    ih = np.clip(((mh - lo) / w).astype(int), 0, NB - 1)
    ih = np.maximum(ih, il)
    wt = 1.0 / (ih - il + 1)
    diff = np.zeros(NB + 1)
    np.add.at(diff, il, wt)
    np.add.at(diff, ih + 1, -wt)
    prof = np.cumsum(diff)[:NB]
    p = int(np.argmax(prof))
    l = r = p
    acc, tot = prof[p], prof.sum()
    while acc < VA_SHARE * tot:
        up = prof[r + 1] if r + 1 < NB else -1.0
        dn = prof[l - 1] if l > 0 else -1.0
        if up >= dn:
            r += 1
            acc += up
        else:
            l -= 1
            acc += dn
    return lo + (p + 0.5) * w, lo + (r + 1) * w, lo + l * w      # POC, VAH, VAL


def sim(D, k, side, stop, target, kend):
    """bracket from the open of bar k to the open of bar kend at the latest; returns (net R, gross R) or None."""
    if side > 0:
        e = D["ao"][k]
        if not (stop < e < target):
            return None
        sl = np.flatnonzero(D["bl"][k:kend] <= stop)
        tp = np.flatnonzero(D["bh"][k:kend] >= target)
        i_s = sl[0] if len(sl) else 10**9
        i_t = tp[0] if len(tp) else 10**9
        if i_s == 10**9 and i_t == 10**9:
            x, xs = D["bo"][kend], D["ao"][kend] - D["bo"][kend]
        elif i_s <= i_t:
            x, xs = min(stop, D["bo"][k + i_s]), D["ao"][k + i_s] - D["bo"][k + i_s]
        else:
            x, xs = target, D["ao"][k + i_t] - D["bo"][k + i_t]
        risk = e - stop
        net = (x - e) / risk
    else:
        e = D["bo"][k]
        if not (target < e < stop):
            return None
        sl = np.flatnonzero(D["ah"][k:kend] >= stop)
        tp = np.flatnonzero(D["al"][k:kend] <= target)
        i_s = sl[0] if len(sl) else 10**9
        i_t = tp[0] if len(tp) else 10**9
        if i_s == 10**9 and i_t == 10**9:
            x, xs = D["ao"][kend], D["ao"][kend] - D["bo"][kend]
        elif i_s <= i_t:
            x, xs = max(stop, D["ao"][k + i_s]), D["ao"][k + i_s] - D["bo"][k + i_s]
        else:
            x, xs = target, D["ao"][k + i_t] - D["bo"][k + i_t]
        risk = stop - e
        net = (e - x) / risk
    es = D["ao"][k] - D["bo"][k]
    return net, net + (es + xs) / 2 / risk


def first_at(tt, sec):
    """index of the first bar at or after day-second `sec` (tt = seconds of day of the day's bars)."""
    j = np.searchsorted(tt, sec)
    return j if j < len(tt) else None


def market(sym, end=END, worlds=WORLDS):
    D = load(sym, end)
    t = D["t"]
    mh = (D["bh"] + D["ah"]) / 2
    ml = (D["bl"] + D["al"]) / 2
    mc = (D["bc"] + D["ac"]) / 2
    mo = (D["bo"] + D["ao"]) / 2
    day = t // 86400
    sod = t % 86400
    hr = sod // 3600
    starts = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    bounds = np.r_[starts, len(t)]
    out = []
    prev = None
    sidx = SYMS.index(sym) if sym in SYMS else 0
    for di in range(len(starts)):
        a, b = bounds[di], bounds[di + 1]
        win = np.arange(a, b)[(hr[a:b] >= 1) & (hr[a:b] <= 22)]
        lv = profile(mh[win], ml[win]) if len(win) >= 300 else None
        if prev is None:
            prev = lv
            continue
        base = prev
        if lv is not None:
            prev = lv
        poc0, vah0, val0 = base
        tt = sod[a:b]
        k_open = first_at(tt, 2 * 3600 + 300)
        k_end = first_at(tt, 22 * 3600 + 55 * 60)
        if k_open is None:
            continue
        k_end = a + (k_end if k_end is not None else b - a - 1)     # early close: last bar of the day (no look-ahead)
        dstamp = pd.Timestamp(int(day[a]) * 86400, unit="s")
        for world in worlds:
            if world == "real":
                poc, vah, val = poc0, vah0, val0
            else:
                rng = np.random.default_rng([world, sidx, int(day[a])])
                u = rng.choice([-1.0, 1.0]) * rng.uniform(0.5, 1.5) * (vah0 - val0)
                poc, vah, val = poc0 + u, vah0 + u, val0 + u
            vaw = vah - val
            if not vaw > 0:
                continue
            op = mo[a + k_open]

            def go(cell, k, side, stop, target):
                if k is None or k >= k_end:
                    return
                if sod[k] % 3600 < 60:                    # first-minute rule: :00 -> :01
                    k += 1
                r = sim(D, k, side, stop, target, k_end)
                if r is not None:
                    out.append((sym, cell, world, dstamp, side, r[0], r[1], int(t[k])))

            # half-hour closes of the day: bars ending at :29 / :59
            hh = np.flatnonzero((tt % 1800) == 1740) + a
            outside = 1 if op > vah else (-1 if op < val else 0)
            if outside != 0:
                # 1. VA80
                c = hh[(sod[hh] >= 2 * 3600 + 29 * 60) & (sod[hh] <= 18 * 3600)]
                ins = (mc[c] > val) & (mc[c] < vah)
                j = np.flatnonzero(ins[1:] & ins[:-1])
                if len(j):
                    k = c[j[0] + 1] + 1
                    if outside > 0:
                        go("VA80", k, -1, vah + 0.5 * vaw, val)
                    else:
                        go("VA80", k, 1, val - 0.5 * vaw, vah)
                # 2. DRIVE
                c = hh[(sod[hh] >= 2 * 3600 + 29 * 60) & (sod[hh] <= 4 * 3600 + 59 * 60)]
                if len(c) == 6 and (np.all(mc[c] > vah) if outside > 0 else np.all(mc[c] < val)):
                    k = first_at(tt, 5 * 3600 + 300)
                    if k is not None:
                        k += a
                        if outside > 0:
                            e = D["ao"][k]
                            go("DRIVE", k, 1, min(vah, e - 0.25 * vaw), e + vaw)
                        else:
                            e = D["bo"][k]
                            go("DRIVE", k, -1, max(val, e + 0.25 * vaw), e - vaw)
            else:
                # 3. EDGE
                rng_ = np.arange(a, b)[(sod[a:b] >= 3 * 3600) & (sod[a:b] <= 18 * 3600)]
                up = mh[rng_] >= vah
                dn = ml[rng_] <= val
                hit = np.flatnonzero(up | dn)
                if len(hit):
                    i = hit[0]
                    if not (up[i] and dn[i]):
                        k = rng_[i] + 1
                        if up[i] and vah - poc >= 0.1 * vaw:
                            go("EDGE", k, -1, vah + 0.5 * (vah - poc), poc)
                        elif dn[i] and poc - val >= 0.1 * vaw:
                            go("EDGE", k, 1, val - 0.5 * (poc - val), poc)
            # 4. NPOC
            k = first_at(tt, 10 * 3600 + 300)
            if k is not None:
                k += a
                seen = np.arange(a, k)[sod[a:k] >= 2 * 3600]
                if len(seen) and not (ml[seen].min() <= poc <= mh[seen].max()):
                    e = mo[k]
                    dist = poc - e
                    if abs(dist) >= 0.2 * vaw:
                        go("NPOC", k, 1 if dist > 0 else -1, e - dist, poc)
    return out


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


def frame(rows):
    return pd.DataFrame(rows, columns=["mkt", "cell", "world", "day", "side", "R", "gR", "t_entry"])


def dry():
    t0 = time.time()
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, SYMS, [END] * len(SYMS), [("real",)] * len(SYMS)))
    df = frame([r for rr in res for r in rr])
    df["per"] = np.where(df.day <= DEV[1], "DEV", "VAL")
    print(f"{len(SYMS)} markets, {time.time() - t0:.0f}s")
    print(df.groupby(["cell", "per"]).size().unstack())
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    bad = 0
    for s in ("EURUSD", "XAUUSD", "SP", "BTCUSD"):
        full = frame(market(s, END, ("real",)))
        part = frame(market(s, cut, ("real",)))
        f = full[full.t_entry < cut - 86400].reset_index(drop=True)          # trades fully resolved before the cut
        p = part[part.t_entry < cut - 86400].reset_index(drop=True)
        bad += int(not (len(f) == len(p) and np.allclose(f.R, p.R) and (f.side.values == p.side.values).all()))
        e = full[(full.t_entry >= cut - 86400) & (full.t_entry < cut)]
        pe = part[(part.t_entry >= cut - 86400) & (part.t_entry < cut)]
        bad += int(not (len(e) == len(pe) and (e.side.values == pe.side.values).all()))   # entries before the cut unchanged
    print("truncation test:", "PASS" if bad == 0 else f"FAIL {bad}")
    D = load("EURUSD")
    t = D["t"]
    dd = pd.Timestamp("2024-07-03").timestamp()
    w = np.flatnonzero((t >= dd + 3600) & (t < dd + 23 * 3600))
    print("hand check EURUSD profile 2024-07-03 (POC, VAH, VAL):", np.round(profile((D["bh"][w] + D["ah"][w]) / 2, (D["bl"][w] + D["al"][w]) / 2), 5),
          "day range", round(((D["bl"][w] + D["al"][w]) / 2).min(), 5), round(((D["bh"][w] + D["ah"][w]) / 2).max(), 5))
    x = df[(df.mkt == "EURUSD") & (df.day == "2024-07-04")]
    print("EURUSD trades on 2024-07-04:", x[["cell", "side", "t_entry"]].assign(t_entry=pd.to_datetime(x.t_entry, unit="s")).to_string(index=False))


def run():
    t0 = time.time()
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, SYMS))
    df = frame([r for rr in res for r in rr])
    df["world"] = df.world.astype(str)
    print(f"run {time.time() - t0:.0f}s, {len(df)} trades", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT / "MPROFILE_trades.parquet")
    rows = []
    for (cell, world), g in df.groupby(["cell", "world"], sort=False):
        r = dict(cell=cell, world=str(world))
        for per, (a, b) in (("D", DEV), ("V", VAL)):
            x = g[(g.day >= a) & (g.day <= b)]
            r[f"n{per}"], r[f"m{per}"], r[f"g{per}"] = len(x), x.R.mean(), x.gR.mean()
            r[f"t{per}"] = nw_t(x.groupby("day").R.mean().to_numpy())
        for y in YEARS:
            r[f"y{y[2:]}"] = g[g.day.dt.year == int(y)].R.mean()
        rows.append(r)
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "MPROFILE_cells.csv", index=False)
    pd.set_option("display.width", 220)
    print(R.round(3).to_string(index=False))
    plc = R[R.world != "real"]
    ceil = np.percentile(plc.tD, 95)
    print(f"\nplacebo levels (12 cells): max DEV t {plc.tD.max():.2f}, 95th pct {ceil:.2f}")
    for _, r in R[R.world == "real"].iterrows():
        dv = df[(df.cell == r.cell) & (df.world == "real") & (df.day <= DEV[1])]
        bym = dv.groupby("mkt").R.sum()
        conc = bym.max() / bym.sum() if bym.sum() > 0 else np.inf
        g = [r.mD >= 0.05 and r.tD >= 2.50, r.mV > 0 and r.tV >= 1.65, sum(r[f"y{y[2:]}"] > 0 for y in YEARS) >= 3, r.tD > ceil, conc <= 0.40]
        print(f"{r.cell}: DEV n {r.nD} net {r.mD:+.3f}R (gross {r.gD:+.3f}) t {r.tD:+.2f} | VAL n {r.nV} net {r.mV:+.3f}R (gross {r.gV:+.3f}) t {r.tV:+.2f} | "
              f"years {r.y22:+.3f}/{r.y23:+.3f}/{r.y24:+.3f}/{r.y25:+.3f} | top market {conc:.2f} | gates {''.join('Y' if x else 'n' for x in g)} PASS {all(g)}")


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
