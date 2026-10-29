"""Edge lab 5: London first-15m candle 1:1, every day (PREREG_EDGE_LAB_5.md). DEV only; hold-out sealed."""
import math
import numpy as np, pandas as pd

DEV_END = pd.Timestamp("2023-12-31")
MARKETS = {"ES": (0.25, 5.0), "NQ": (0.25, 2.0), "GC": (0.1, 10.0), "SI": (0.005, 1000.0)}
COMM = 1.2
RES = (1, 3, 5, 15)


def rma(s, n):
    return s.ewm(alpha=1.0 / n, adjust=False).mean()


def day_table(df):
    """Per London date: candle O/H/L/C, post-entry 1m arrays, and daily context."""
    d = df.copy()
    lon = d.index.tz_convert("Europe/London")
    d["tod"] = lon.hour * 60 + lon.minute
    d["ldate"] = lon.tz_localize(None).normalize()
    udate = d.index.tz_convert("UTC").tz_localize(None).normalize()
    daily = d.groupby(udate).agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"))
    pc = daily["close"].shift(1)
    tr = pd.concat([daily.high - daily.low, (daily.high - pc).abs(), (daily.low - pc).abs()], axis=1).max(axis=1)
    daily["atr_prev"] = rma(tr, 14).shift(1)
    daily["trend_up"] = daily["close"].shift(1) > daily["close"].rolling(20).mean().shift(1)
    daily["prev_up"] = daily["close"].shift(1) > daily["open"].shift(1)
    daily["asia_up_ref"] = daily["open"]  # 00:00 UTC open proxy = first bar of the UTC day
    days = []
    for ld, g in d.groupby("ldate"):
        cw = g[(g.tod >= 480) & (g.tod < 495)]
        if len(cw) < 3:
            continue
        post = g[(g.tod >= 495) & (g.tod <= 960)]
        if len(post) < 10 or post.tod.iloc[-1] < 960:
            continue
        if ld not in daily.index:
            continue
        r = daily.loc[ld]
        if np.isnan(r.atr_prev) or np.isnan(r.trend_up):
            continue
        end = post.tod.to_numpy()
        keep = end <= 960
        days.append(dict(
            date=ld, o=cw.open.iloc[0], h=cw.high.max(), l=cw.low.min(), c=cw.close.iloc[-1], atr=r.atr_prev,
            trend_up=bool(r.trend_up), prev_up=bool(r.prev_up), asia_up=cw.open.iloc[0] > r.asia_up_ref,
            tod=end[keep], hi=post.high.to_numpy()[keep], lo=post.low.to_numpy()[keep], op=post.open.to_numpy()[keep]))
    return days


def bin_arrays(day, res):
    if res == 1:
        return day["tod"], day["hi"], day["lo"], day["op"]
    tod, hi, lo, op = day["tod"], day["hi"], day["lo"], day["op"]
    m = tod < 960
    b = (tod[m] - 495) // res
    k = np.unique(b)
    H = np.array([hi[m][b == x].max() for x in k]); L = np.array([lo[m][b == x].min() for x in k])
    O = np.array([op[m][b == x][0] for x in k])
    # session-end bar (tod == 960) is a 1m open, same for any resolution
    return np.r_[495 + k * res, 960], np.r_[H, hi[~m][:1]], np.r_[L, lo[~m][:1]], np.r_[O, op[~m][:1]]


def sim(entry, side, risk, arrs):
    tod, hi, lo, op = arrs
    tp = entry + side * risk
    sl = entry - side * risk
    for i in range(len(tod)):
        if tod[i] >= 960:
            return (op[i] - entry) * side
        if side == 1:
            if lo[i] <= sl:
                return -risk
            if hi[i] >= tp:
                return risk
        else:
            if hi[i] >= sl:
                return -risk
            if lo[i] <= tp:
                return risk
    return 0.0


def direction(day, rule):
    if rule == "D1":
        if day["c"] > day["o"]:
            return 1
        if day["c"] < day["o"]:
            return -1
        return 1 if day["trend_up"] else -1
    if rule == "D2":
        return 1 if day["trend_up"] else -1
    if rule == "D3":
        return 1 if day["prev_up"] else -1
    return 1 if day["asia_up"] else -1


def run_variant(days, tick, pv, rule, buf, res, arr_cache):
    rows = []
    for idx, day in enumerate(days):
        side = direction(day, rule)
        rng = day["h"] - day["l"]
        # stop distance from entry (candle close): to the opposite candle extreme (+ buffer); never below the floor
        extreme = day["l"] if side == 1 else day["h"]
        risk = abs(day["c"] - extreme) + buf * rng
        risk = max(risk, 0.03 * day["atr"])
        if not risk > 0:
            continue
        key = (idx, res)
        if key not in arr_cache:
            arr_cache[key] = bin_arrays(day, res)
        arrs = arr_cache[key]
        pnl = sim(day["c"], side, risk, arrs)
        mir = sim(day["c"], -side, risk, arrs)
        cost = (2 * tick + COMM / pv) / risk
        rows.append((day["date"], side, pnl / risk, pnl / risk - cost, mir / risk - cost))
    return rows


def stats(rows, rng):
    G = np.array([r[2] for r in rows]); A = np.array([r[3] for r in rows]); M = np.array([r[4] for r in rows])
    n = len(A)
    means = np.where(rng.random((20000, n)) < 0.5, A, M).mean(axis=1)
    p = float((means >= A.mean()).mean())
    se = A.std(ddof=1) / math.sqrt(n)
    return n, 100 * (G >= 0.99).mean(), G.mean(), A.mean(), se, p


rng = np.random.default_rng(20261026)
VARS = [(r, b) for r in ("D1", "D2", "D3", "D4") for b in (0.0, 0.5)]
print(f"{'run':14} {'n':>5} {'TP%':>5} {'R gross':>8} {'R net':>8} {'SE':>6} {'P':>7} {'yrs+':>5}  finalist")
finalists, best = [], {}
for sym, (tick, pv) in MARKETS.items():
    df = pd.read_parquet(f"futures/data/databento/futures_{sym}.F_1m.parquet").sort_values("ts").set_index("ts")
    df = df[df.index < pd.Timestamp("2024-01-01", tz="UTC")][["open", "high", "low", "close"]]  # hold-out sealed
    days = day_table(df)
    days = [x for x in days if x["date"] <= DEV_END]
    cache = {}
    for rule, buf in VARS:
        rows = run_variant(days, tick, pv, rule, buf, 1, cache)
        n, tp, g, a, se, p = stats(rows, rng)
        pos = sum(1 for y in (2020, 2021, 2022, 2023) if np.mean([r[3] for r in rows if r[0].year == y]) > 0)
        ok = n >= 800 and a >= 0.05 and p <= 0.0008 and pos >= 3
        name = f"{sym} {rule} buf{buf}"
        if ok:
            finalists.append(name)
        if sym not in best or a > best[sym][0]:
            best[sym] = (a, rule, buf)
        print(f"{name:14} {n:5d} {tp:5.0f} {g:+8.3f} {a:+8.3f} {se:6.3f} {p:7.4f} {pos:3d}/4  {'FINALIST' if ok else 'no'}", flush=True)
    a, rule, buf = best[sym]
    line = []
    for res in RES:
        rows = run_variant(days, tick, pv, rule, buf, res, cache)
        line.append(f"{res}m {np.mean([r[3] for r in rows]):+.3f}")
    print(f"   {sym} best {rule} buf{buf} by exit resolution (R net): " + " | ".join(line), flush=True)
print("\nDEV finalists:", finalists if finalists else "NONE")
