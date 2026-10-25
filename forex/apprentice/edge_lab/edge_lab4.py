"""Edge lab 4: STDV PO3 London-only indicator (PREREG_EDGE_LAB_4.md), every market x timeframe. DEV only; hold-out sealed."""
import math, sys
import numpy as np, pandas as pd

DEV_END = pd.Timestamp("2023-12-31")
MARKETS = {  # parquet symbol: (tick, point value per micro)
    "ES": (0.25, 5.0), "NQ": (0.25, 2.0), "GC": (0.1, 10.0), "SI": (0.005, 1000.0),
}
COMM = 1.2
TFS = (1, 3, 5, 10, 15)


def rma(s, n):
    return s.ewm(alpha=1.0 / n, adjust=False).mean()


def bars(df, tf):
    if tf == 1:
        b = df.copy()
    else:
        b = df.resample(f"{tf}min", label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna(subset=["open"])
    return b


def run(df, tick, pv, tf):
    b = bars(df, tf)
    o, h, l, c, v = (b[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    cs, hs, ls = pd.Series(c), pd.Series(h), pd.Series(l)
    prev_c = cs.shift(1)
    tr = pd.concat([hs - ls, (hs - prev_c).abs(), (ls - prev_c).abs()], axis=1).max(axis=1)
    atr = rma(tr, 14).to_numpy()
    delta = cs.diff()
    rsi = (100 - 100 / (1 + rma(delta.clip(lower=0), 14) / rma((-delta).clip(lower=0), 14).replace(0, 1e-12))).to_numpy()
    ema = cs.ewm(span=50, adjust=False).mean().to_numpy()
    avgvol = pd.Series(v).rolling(20).mean().to_numpy()
    rh = hs.shift(1).rolling(20).max().to_numpy()
    rl = ls.shift(1).rolling(20).min().to_numpy()
    lon = b.index.tz_convert("Europe/London")
    tod = (lon.hour * 60 + lon.minute).to_numpy()
    in_sess = (tod >= 480) & (tod < 960)
    in_entry = (tod >= 480) & (tod < 930)
    sess_end = np.r_[False, (~in_sess[1:]) & in_sess[:-1]]
    swing = rh - rl
    cross_up = np.r_[False, (c[1:] > rh[1:]) & (c[:-1] <= rh[:-1])]
    cross_dn = np.r_[False, (c[1:] < rl[1:]) & (c[:-1] >= rl[:-1])]
    rng_ok = swing >= atr * 0.8
    vol_ok = v > avgvol * 1.3
    buy = in_entry & cross_up & vol_ok & (c > o) & (rsi >= 55) & (rsi <= 72) & (c > ema) & rng_ok
    sell = in_entry & cross_dn & vol_ok & (c < o) & (rsi <= 45) & (rsi >= 28) & (c < ema) & rng_ok
    tmin = (b.index.view("int64") // 60_000_000_000).astype(np.int64)
    date = b.index.tz_convert("UTC").tz_localize(None).normalize()

    def sim(k, side, entry, sl, tp):
        for j in range(k + 1, n):
            if sess_end[j]:
                return (o[j] - entry) * side
            if side == 1:
                if l[j] <= sl:
                    return sl - entry
                if h[j] >= tp:
                    return tp - entry
            else:
                if h[j] >= sl:
                    return entry - sl
                if l[j] <= tp:
                    return entry - tp
        return None

    rows = []
    busy_until = -1
    last_t = -10**12
    for k in np.where(buy | sell)[0]:
        if k <= busy_until or not (tmin[k] - last_t > 30):
            continue
        side = 1 if buy[k] else -1
        entry = c[k]
        sl = rl[k] if side == 1 else rh[k]
        tp = rh[k] + swing[k] if side == 1 else rl[k] - swing[k]
        risk = abs(entry - sl)
        if not risk > 0:
            continue
        # find exit index for busy_until
        pnl = sim(k, side, entry, sl, tp)
        mir = sim(k, -side, entry, entry + side * risk, entry - side * abs(tp - entry))
        # exit index
        ex_idx = None
        for j in range(k + 1, n):
            if sess_end[j] or (side == 1 and (l[j] <= sl or h[j] >= tp)) or (side == -1 and (h[j] >= sl or l[j] <= tp)):
                ex_idx = j
                break
        if pnl is None or mir is None or ex_idx is None:
            continue
        busy_until = ex_idx
        last_t = tmin[k]
        cost = (2 * tick + COMM / pv) / risk
        rows.append((date[k], side, pnl / risk, pnl / risk - cost, mir / risk - cost))
    return rows


def stats(rows, rng):
    if not rows:
        return None
    G = np.array([r[2] for r in rows]); A = np.array([r[3] for r in rows]); M = np.array([r[4] for r in rows])
    n = len(A)
    means = np.where(rng.random((20000, n)) < 0.5, A, M).mean(axis=1)
    p = float((means >= A.mean()).mean())
    se = A.std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
    return n, 100 * (G > 0).mean(), G.mean(), A.mean(), se, p


rng = np.random.default_rng(20261025)
print(f"{'run':8} {'n':>5} {'win%':>5} {'R gross':>8} {'R net':>8} {'SE':>6} {'P':>7} {'yrs+':>5}  finalist")
finalists = []
for sym, (tick, pv) in MARKETS.items():
    df = pd.read_parquet(f"D:/finance/beginner-quant-research/futures/data/databento/futures_{sym}.F_1m.parquet").sort_values("ts").set_index("ts")
    df = df[df.index < pd.Timestamp("2024-01-01", tz="UTC")]  # hold-out sealed
    for tf in TFS:
        rows = [r for r in run(df, tick, pv, tf) if r[0] <= DEV_END]
        s = stats(rows, rng)
        label = f"{sym} {tf}m"
        if not s:
            print(f"{label:8} no trades")
            continue
        n, win, g, a, se, p = s
        pos = sum(1 for y in (2020, 2021, 2022, 2023) if (lambda x: len(x) > 0 and np.mean(x) > 0)([r[3] for r in rows if r[0].year == y]))
        ok = n >= 100 and a >= 0.10 and p <= 0.0016 and pos >= 3
        if ok:
            finalists.append(label)
        print(f"{label:8} {n:5d} {win:5.0f} {g:+8.3f} {a:+8.3f} {se:6.3f} {p:7.4f} {pos:3d}/4  {'FINALIST' if ok else 'no'}", flush=True)
print("\nDEV finalists:", finalists if finalists else "NONE")
