"""Edge lab 2: six pre-registered slower gold ideas (PREREG_EDGE_LAB_2.md).
DEV is open; HOLD-OUT stays sealed unless HOLDOUT_OK=1 and --holdout NAME."""
import sys, os, math, argparse
import numpy as np, pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--holdout", default=None)
args = ap.parse_args()
if args.holdout and os.environ.get("HOLDOUT_OK") != "1":
    sys.exit("hold-out is sealed: only after a DEV finalist is chosen (set HOLDOUT_OK=1)")

SL, THRU, COMM, PV = 0.1, 0.1, 1.2, 10.0
MIN_RISK = 3.0
DEV_END = pd.Timestamp("2023-12-31")
df = pd.read_parquet("D:/finance/beginner-quant-research/futures/data/databento/futures_GC.F_1m.parquet").sort_values("ts").reset_index(drop=True)
loc = df.ts.dt.tz_convert("America/New_York").dt.tz_localize(None)
TE = ((loc - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)).to_numpy(np.int64)
O, H, L, C = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))


def make_bars(size):
    g = (TE + 25200) // size  # 17:00 ET maps to a bar boundary for 1h, 4h and 1d
    d = pd.DataFrame({"g": g, "o": O, "h": H, "l": L, "c": C}).groupby("g").agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"))
    b = {k: d[k].to_numpy(float) for k in ("o", "h", "l", "c")}
    b["gid"] = d.index.to_numpy()
    b["ts"] = pd.to_datetime(d.index.to_numpy() * size - 25200, unit="s")
    pc = np.r_[np.nan, b["c"][:-1]]
    tr = np.nanmax(np.vstack([b["h"] - b["l"], np.abs(b["h"] - pc), np.abs(b["l"] - pc)]), axis=0)
    b["atr"] = pd.Series(tr).rolling(14).mean().to_numpy()
    b["n"] = len(b["c"])
    return b


def roll(a, w, fn):
    s = pd.Series(a)
    return getattr(s.rolling(w), fn)().shift(1).to_numpy()


def run(b, side, k, risk, mult, exit_cond, fixed_exit, max_bars):
    entry = b["c"][k] + SL * side
    stop = entry - side * risk
    tgt = entry + side * mult * risk if mult else None
    n = b["n"]
    for m in range(k + 1, min(n, k + max_bars + 1)):
        o, h, l, c = b["o"][m], b["h"][m], b["l"][m], b["c"][m]
        if side == 1:
            if o <= stop:
                ex, kind = o - SL, "stop"
                break
            if l <= stop:
                ex, kind = stop - SL, "stop"
                break
            if tgt is not None and h >= tgt + THRU:
                ex, kind = tgt, "tgt"
                break
        else:
            if o >= stop:
                ex, kind = o + SL, "stop"
                break
            if h >= stop:
                ex, kind = stop + SL, "stop"
                break
            if tgt is not None and l <= tgt - THRU:
                ex, kind = tgt, "tgt"
                break
        done = (m >= fixed_exit) if fixed_exit is not None else (exit_cond(m, side) if exit_cond else False)
        if done or m == k + max_bars:
            ex, kind = c - SL * side, "close"
            break
    else:
        return None
    R = (ex - entry) * side / risk - COMM / (risk * PV)
    return R, m, kind


def trades(b, sig_fn, risk_fn, exit_cond, mult, max_bars, flip=False, start=210):
    out, flat_until = [], -1
    for k in range(start, b["n"] - 1):
        if k <= flat_until:
            continue
        s = sig_fn(k)
        if not s:
            continue
        risk = risk_fn(k, s)
        if risk is None or not risk >= MIN_RISK:
            continue
        a = run(b, s, k, risk, mult, exit_cond, None, max_bars)
        if a is None:
            continue
        mir = run(b, -s, k, risk, mult, None, a[1], max_bars)
        if mir is None:
            continue
        out.append((b["ts"][k], s, a[0], mir[0]))
        flat_until = a[1] - 1 if (flip and a[2] == "close") else a[1]
    return out


B1, B4, BD = make_bars(3600), make_bars(14400), make_bars(86400)
ideas = {}

# 1 and 2: Donchian
for name, b, mb in (("DONCHIAN_H4", B4, 120), ("DONCHIAN_D", BD, 60)):
    hh20, ll20 = roll(b["h"], 20, "max"), roll(b["l"], 20, "min")
    hh10, ll10 = roll(b["h"], 10, "max"), roll(b["l"], 10, "min")
    sig = lambda k, b=b, hh20=hh20, ll20=ll20: 1 if b["c"][k] > hh20[k] else (-1 if b["c"][k] < ll20[k] else 0)
    risk = lambda k, s, b=b: 2 * b["atr"][k]
    ex = lambda m, side, b=b, hh10=hh10, ll10=ll10: (b["c"][m] < ll10[m]) if side == 1 else (b["c"][m] > hh10[m])
    ideas[name] = trades(b, sig, risk, ex, None, mb)

# 3: weekly time-series momentum
wd = (BD["gid"] + 3) % 7
def sig3(k):
    if wd[k] != 4 or k < 60:
        return 0
    r = BD["c"][k] / BD["c"][k - 60] - 1
    return 1 if r > 0 else (-1 if r < 0 else 0)
ideas["TSMOM_D"] = trades(BD, sig3, lambda k, s: 2 * BD["atr"][k], lambda m, side: wd[m] == 4, None, 8)

# 4: EMA20/50 cross on 1h, always in the market
e20 = pd.Series(B1["c"]).ewm(span=20, adjust=False).mean().to_numpy()
e50 = pd.Series(B1["c"]).ewm(span=50, adjust=False).mean().to_numpy()
up = np.r_[False, (e20[1:] > e50[1:]) & (e20[:-1] <= e50[:-1])]
dn = np.r_[False, (e20[1:] < e50[1:]) & (e20[:-1] >= e50[:-1])]
ideas["EMA_CROSS_H1"] = trades(B1, lambda k: 1 if up[k] else (-1 if dn[k] else 0), lambda k, s: 3 * B1["atr"][k],
                               lambda m, side: dn[m] if side == 1 else up[m], None, 400, flip=True)

# 5: 1h trend pullback with 2R target
def sig5(k):
    b = B1
    if b["c"][k] > e50[k] and e50[k] > e50[k - 5]:
        return 1 if (b["l"][k] <= e20[k] and b["c"][k] > e20[k] and b["c"][k] > b["o"][k]) else 0
    if b["c"][k] < e50[k] and e50[k] < e50[k - 5]:
        return -1 if (b["h"][k] >= e20[k] and b["c"][k] < e20[k] and b["c"][k] < b["o"][k]) else 0
    return 0
def risk5(k, s):
    if s == 1:
        return (B1["c"][k] + SL) - (B1["l"][k - 2:k + 1].min() - 0.1)
    return (B1["h"][k - 2:k + 1].max() + 0.1) - (B1["c"][k] - SL)
ideas["H1_PULLBACK"] = trades(B1, sig5, risk5, None, 2.0, 24)

# 6: RSI(2) mean reversion on daily bars
dl = np.r_[np.nan, np.diff(BD["c"])]
ag = pd.Series(np.where(dl > 0, dl, 0.0)).ewm(alpha=0.5, adjust=False).mean().to_numpy()
al = pd.Series(np.where(dl < 0, -dl, 0.0)).ewm(alpha=0.5, adjust=False).mean().to_numpy()
rsi = 100 - 100 / (1 + ag / np.where(al == 0, 1e-9, al))
sma200 = pd.Series(BD["c"]).rolling(200).mean().to_numpy()
def sig6(k):
    if rsi[k] < 10 and BD["c"][k] > sma200[k]:
        return 1
    if rsi[k] > 90 and BD["c"][k] < sma200[k]:
        return -1
    return 0
ideas["RSI2_D"] = trades(BD, sig6, lambda k, s: 3 * BD["atr"][k], lambda m, side: rsi[m] > 70 if side == 1 else rsi[m] < 30, None, 10)

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


sealed = args.holdout is None
final = []
for name, rs in ideas.items():
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
            pos = sum(1 for y, (nn, mm) in yrs.items() if nn >= 3 and mm > 0)
            ok = n >= 40 and m >= 0.20 and p <= 0.005 and pos >= 3
            print(f"  finalist rule: n>=40 {n >= 40} | mean>=+0.20 {m >= 0.20} | P<=0.005 {p <= 0.005} | positive years {pos}/4 -> {'FINALIST' if ok else 'no'}")
            if ok:
                final.append(name)
if sealed:
    print("\nDEV finalists:", final if final else "NONE")
