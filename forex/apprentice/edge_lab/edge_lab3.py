"""Edge lab 3: the trader's idea (PREREG_EDGE_LAB_3.md): 15m bias + 5m candle in favour, 1:1, wide (3 x 5m ATR) stop.
DEV is open; HOLD-OUT stays sealed unless HOLDOUT_OK=1 and --holdout."""
import sys, os, math, argparse
import numpy as np, pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--holdout", action="store_true")
args = ap.parse_args()
if args.holdout and os.environ.get("HOLDOUT_OK") != "1":
    sys.exit("hold-out is sealed: only after a DEV finalist is chosen (set HOLDOUT_OK=1)")

SL, THRU, COMM, PV = 0.1, 0.1, 1.2, 10.0
DEV_END = pd.Timestamp("2023-12-31")
df = pd.read_parquet("D:/finance/beginner-quant-research/futures/data/databento/futures_GC.F_1m.parquet").sort_values("ts").reset_index(drop=True)
loc = df.ts.dt.tz_convert("Europe/London").dt.tz_localize(None)
T = ((loc - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)).to_numpy(np.int64)
O, H, L, C = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
N = len(T)


def sim(i, side, entry_raw, risk, mult, end_t):
    entry = entry_raw + SL * side
    stop = entry - side * risk
    tgt = entry + side * mult * risk
    for j in range(i + 1, N):
        if T[j] >= end_t:
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


g15 = T // 900
d15 = pd.DataFrame({"g": g15, "c": C}).groupby("g").c.last()
e15 = d15.ewm(span=12, adjust=False).mean()
g5 = T // 300
d5 = pd.DataFrame({"g": g5, "o": O, "h": H, "l": L, "c": C}).groupby("g").agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"))
e5 = d5.c.ewm(span=12, adjust=False).mean().to_numpy()
pc = np.r_[np.nan, d5.c.to_numpy()[:-1]]
tr = np.nanmax(np.vstack([d5.h.to_numpy() - d5.l.to_numpy(), np.abs(d5.h.to_numpy() - pc), np.abs(d5.l.to_numpy() - pc)]), axis=0)
atr5 = pd.Series(tr).rolling(14).mean().to_numpy()
g5_idx = d5.index.to_numpy()
d5o, d5c = d5.o.to_numpy(), d5.c.to_numpy()

rows = []
for d in np.unique(T // 86400):
    if (d + 3) % 7 >= 5:
        continue
    t8 = d * 86400 + 8 * 3600
    i8 = np.searchsorted(T, t8)
    if i8 >= N or T[i8] > t8 + 120:
        continue
    gg = (t8 // 900) - 1
    try:
        cc, ee, eb = d15[gg], e15[gg], e15[gg - 4]
    except KeyError:
        continue
    bias = 1 if (cc > ee and ee > eb) else -1 if (cc < ee and ee < eb) else 0
    if not bias:
        continue
    end17 = d * 86400 + 17 * 3600
    for j in range(i8, N):
        if T[j] >= d * 86400 + 11 * 3600:
            break
        if (T[j] // 60) % 5 != 4:
            continue
        g = T[j] // 300
        p = np.searchsorted(g5_idx, g)
        if p < 20 or g5_idx[p] != g or g * 300 < t8:
            continue
        ok = (d5c[p] > e5[p] and d5c[p] > d5o[p]) if bias == 1 else (d5c[p] < e5[p] and d5c[p] < d5o[p])
        if not ok:
            continue
        risk = 3 * atr5[p]
        if not risk >= 3.0:
            break
        a = sim(j, bias, C[j], risk, 1.0, end17)
        m = sim(j, -bias, C[j], risk, 1.0, end17)
        if a is not None and m is not None:
            rows.append((pd.Timestamp("1970-01-01") + pd.Timedelta(days=int(d)), bias, a, m, risk))
        break

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
    se = A.std(ddof=1) / math.sqrt(n)
    print(f"  {label}: n={n} win={100 * (A > 0).mean():.0f}% meanR={A.mean():+.3f} (SE {se:.3f}) | mirror {M.mean():+.3f} | random-side mean {means.mean():+.3f} P={p:.4f}")
    return n, A.mean(), p


dev = [r for r in rows if r[0] <= DEV_END]
ho = [r for r in rows if r[0] > DEV_END]
use = ho if args.holdout else dev
print(f"IDEA 3 (the trader): 15m bias + 5m candle in favour, 1:1, 3xATR stop  [{'HOLD-OUT 2024-01..2026-09' if args.holdout else 'DEV 2019-06..2023-12'}]")
res = stats(use, "all")
stats([r for r in use if r[1] == 1], "longs")
stats([r for r in use if r[1] == -1], "shorts")
if not args.holdout:
    yrs = {}
    for y in (2020, 2021, 2022, 2023):
        sub = [r for r in dev if r[0].year == y]
        yrs[y] = (len(sub), float(np.mean([r[2] for r in sub])) if sub else float("nan"))
    print("  by year (n, meanR):", {y: (n_, round(m_, 3)) for y, (n_, m_) in yrs.items()})
    print("  median stop (pts): %.1f" % np.median([r[4] for r in dev]))
    if res:
        n, m, p = res
        pos = sum(1 for y, (nn, mm) in yrs.items() if nn > 0 and mm > 0)
        ok = n >= 150 and m >= 0.10 and p <= 0.0045 and pos >= 3
        print(f"  finalist rule: n>=150 {n >= 150} | mean>=+0.10 {m >= 0.10} | P<=0.0045 {p <= 0.0045} | positive years {pos}/4 -> {'FINALIST' if ok else 'no'}")
