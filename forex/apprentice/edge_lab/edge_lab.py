"""Edge lab 1: four pre-registered gold ideas (PREREG_EDGE_LAB_1.md).
DEV is open; HOLD-OUT stays sealed unless HOLDOUT_OK=1 and --holdout NAME."""
import sys, os, math, argparse
import numpy as np, pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--holdout", default=None)
args = ap.parse_args()
if args.holdout and os.environ.get("HOLDOUT_OK") != "1":
    sys.exit("hold-out is sealed: only after a DEV finalist is chosen (set HOLDOUT_OK=1)")

SL, THRU, COMM, PV = 0.1, 0.1, 1.2, 10.0
DEV_END = pd.Timestamp("2023-12-31").normalize()
df = pd.read_parquet("D:/finance/beginner-quant-research/futures/data/databento/futures_GC.F_1m.parquet").sort_values("ts").reset_index(drop=True)


def naive(tz):
    return df.ts.dt.tz_convert(tz).dt.tz_localize(None)


def epoch(s):
    return ((s - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)).to_numpy(np.int64)


T = epoch(naive("Europe/London"))
TE = epoch(naive("America/New_York"))
O, H, L, C = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
N = len(T)


def wk(d):
    return (d + 3) % 7 < 5


def day_date(d):
    return pd.Timestamp("1970-01-01") + pd.Timedelta(days=int(d))


def sim(TT, i, side, entry_raw, risk, mult, end_t):
    entry = entry_raw + SL * side
    stop = entry - side * risk
    tgt = entry + side * mult * risk
    for j in range(i + 1, N):
        if TT[j] >= end_t:
            ex = C[j] - SL * side
            break
        if side == 1:
            if O[j] <= stop:
                ex = O[j] - SL
                break
            if L[j] <= stop:
                ex = stop - SL
                break
            if H[j] >= tgt + THRU:
                ex = tgt
                break
        else:
            if O[j] >= stop:
                ex = O[j] + SL
                break
            if H[j] >= stop:
                ex = stop + SL
                break
            if L[j] <= tgt - THRU:
                ex = tgt
                break
    else:
        return None
    return (ex - entry) * side / risk - COMM / (risk * PV)


def both(TT, i, side, entry_raw, stop_struct, mult, end_t, rmin, rmax):
    entry = entry_raw + SL * side
    risk = abs(entry - stop_struct)
    if not (rmin <= risk <= rmax):
        return None
    a = sim(TT, i, side, entry_raw, risk, mult, end_t)
    m = sim(TT, i, -side, entry_raw, risk, mult, end_t)  # mirror: same distances, opposite side
    if a is None or m is None:
        return None
    return a, m


days_l = np.unique(T // 86400)
days_e = np.unique(TE // 86400)

g15 = T // 900
d15 = pd.DataFrame({"g": g15, "c": C}).groupby("g").c.last()
e15 = d15.ewm(span=12, adjust=False).mean()
g5 = T // 300
d5 = pd.DataFrame({"g": g5, "o": O, "h": H, "l": L, "c": C}).groupby("g").agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"))
e5 = d5.c.ewm(span=12, adjust=False).mean()
g5_idx = d5.index.to_numpy()
d5l, d5h, d5o, d5c, e5v = d5.l.to_numpy(), d5.h.to_numpy(), d5.o.to_numpy(), d5.c.to_numpy(), e5.to_numpy()

rows = {k: [] for k in ("ASIA_BREAK", "ASIA_SWEEP_FADE", "TREND_PULLBACK", "NY_MOMENTUM")}
drift = []
for d in days_l:
    if not wk(d):
        continue
    t8, tA = d * 86400 + 8 * 3600, d * 86400
    iA, i8 = np.searchsorted(T, tA), np.searchsorted(T, t8)
    if i8 >= N or T[i8] > t8 + 120 or i8 - iA < 60:
        continue
    hi, lo = H[iA:i8].max(), L[iA:i8].min()
    end17 = d * 86400 + 17 * 3600
    i1030 = np.searchsorted(T, d * 86400 + 10.5 * 3600)
    date = day_date(d)
    i11 = np.searchsorted(T, d * 86400 + 11 * 3600) - 1
    if i11 > i8:
        drift.append((date, C[i11] - O[i8]))
    # idea 1: Asia range break
    if hi - lo >= 1.5:
        for j in range(i8, min(i1030, N)):
            if C[j] > hi or C[j] < lo:
                side = 1 if C[j] > hi else -1
                r = both(T, j, side, C[j], (hi + lo) / 2, 1.5, end17, 1.5, 12)
                if r:
                    rows["ASIA_BREAK"].append((date, side) + r)
                break
    # idea 2: Asia sweep fade
    sw_hi = sw_lo = None
    for j in range(i8, min(i1030, N)):
        if sw_hi is None and H[j] >= hi + 0.5:
            sw_hi = [j, H[j]]
        if sw_lo is None and L[j] <= lo - 0.5:
            sw_lo = [j, L[j]]
        sig = None
        if sw_hi is not None:
            sw_hi[1] = max(sw_hi[1], H[j])
            if C[j] < hi:
                sig = (-1, sw_hi[1] + 0.1)
            elif j - sw_hi[0] > 5:
                sw_hi = None
        if sig is None and sw_lo is not None:
            sw_lo[1] = min(sw_lo[1], L[j])
            if C[j] > lo:
                sig = (1, sw_lo[1] - 0.1)
            elif j - sw_lo[0] > 5:
                sw_lo = None
        if sig:
            r = both(T, j, sig[0], C[j], sig[1], 1.5, end17, 1.5, 12)
            if r:
                rows["ASIA_SWEEP_FADE"].append((date, sig[0]) + r)
            break
    # idea 3: trend pullback on 5m
    gg15 = (t8 // 900) - 1
    try:
        cc, ee, eb = d15[gg15], e15[gg15], e15[gg15 - 4]
    except KeyError:
        cc = None
    if cc is not None:
        bias = 1 if (cc > ee and ee > eb) else -1 if (cc < ee and ee < eb) else 0
        if bias:
            for j in range(i8, N):
                if T[j] >= d * 86400 + 11 * 3600:
                    break
                if (T[j] // 60) % 5 != 4:
                    continue
                g = T[j] // 300
                p = np.searchsorted(g5_idx, g)
                if p < 6 or g5_idx[p] != g or g * 300 < t8:
                    continue
                if bias == 1:
                    ok = d5l[p] <= e5v[p] and d5c[p] > e5v[p] and d5c[p] > d5o[p]
                else:
                    ok = d5h[p] >= e5v[p] and d5c[p] < e5v[p] and d5c[p] < d5o[p]
                if ok:
                    stop = d5l[p - 5:p + 1].min() - 0.1 if bias == 1 else d5h[p - 5:p + 1].max() + 0.1
                    r = both(T, j, bias, C[j], stop, 2.0, end17, 1.5, 10)
                    if r:
                        rows["TREND_PULLBACK"].append((date, bias) + r)
                    break
# idea 4: New York open momentum (America/New_York clock)
for d in days_e:
    if not wk(d):
        continue
    s = d * 86400 + 9 * 3600 + 30 * 60
    i0, i1 = np.searchsorted(TE, s), np.searchsorted(TE, s + 14 * 60)
    if i1 >= N or TE[i0] != s or TE[i1] != s + 14 * 60:
        continue
    mv = C[i1] - O[i0]
    if abs(mv) < 1.5:
        continue
    side = 1 if mv > 0 else -1
    stop = (L[i0:i1 + 1].min() - 0.1) if side == 1 else (H[i0:i1 + 1].max() + 0.1)
    r = both(TE, i1, side, C[i1], stop, 1.5, d * 86400 + 12 * 3600, 1.5, 12)
    if r:
        rows["NY_MOMENTUM"].append((day_date(d), side) + r)

rng = np.random.default_rng(20261025)


def stats(rs, label):
    if not rs:
        print(f"  {label}: no trades")
        return None
    A = np.array([r[2] for r in rs])
    M = np.array([r[3] for r in rs])
    n = len(A)
    pick = rng.random((20000, n)) < 0.5
    means = np.where(pick, A, M).mean(axis=1)
    p = float((means >= A.mean()).mean())
    se = A.std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
    print(f"  {label}: n={n} win={100 * (A > 0).mean():.0f}% meanR={A.mean():+.3f} (SE {se:.3f}) | mirror {M.mean():+.3f} | random-side mean {means.mean():+.3f} P={p:.4f}")
    return n, A.mean(), p


final = []
sealed = args.holdout is None
for name, rs in rows.items():
    if args.holdout and name != args.holdout:
        continue
    dev = [r for r in rs if r[0] <= DEV_END]
    ho = [r for r in rs if r[0] > DEV_END]
    use = dev if sealed else ho
    print(f"\n{name}  [{'DEV 2019-06..2023-12' if sealed else 'HOLD-OUT 2024-01..2026-09'}]")
    res = stats(use, "all")
    stats([r for r in use if r[1] == 1], "longs")
    stats([r for r in use if r[1] == -1], "shorts")
    if sealed:
        yrs = {}
        for y in (2020, 2021, 2022, 2023):
            sub = [r for r in dev if r[0].year == y]
            yrs[y] = (len(sub), float(np.mean([r[2] for r in sub])) if sub else float("nan"))
        print("  by year (n, meanR):", {y: (n_, round(m_, 3)) for y, (n_, m_) in yrs.items()})
        if res:
            n, m, p = res
            pos = sum(1 for y, (nn, mm) in yrs.items() if nn > 0 and mm > 0)
            ok = n >= 150 and m >= 0.10 and p <= 0.0125 and pos >= 3
            print(f"  finalist rule: n>=150 {n >= 150} | mean>=+0.10 {m >= 0.10} | P<=0.0125 {p <= 0.0125} | positive years {pos}/4 -> {'FINALIST' if ok else 'no'}")
            if ok:
                final.append(name)
if sealed:
    dd = np.array([x for dt, x in drift if dt <= DEV_END])
    print(f"\nYARDSTICK long 08:00->11:00 local on DEV: mean {dd.mean():+.2f} pts/day over {len(dd)} days ({100 * (dd > 0).mean():.0f}% up days)")
    print("\nDEV finalists:", final if final else "NONE")
