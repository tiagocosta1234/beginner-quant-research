"""PREREG_HTF_CLAUDE5M: professional HTF (weekly + daily) and fundamental (real yields + dollar) biases on the claude 5min GC setups.
Usage: python htf_claude5m.py"""
import numpy as np, pandas as pd

g = pd.read_parquet("futures/data/databento/futures_GC.F_1m.parquet", columns=["ts", "open", "high", "low", "close"])
g.index = pd.DatetimeIndex(g.ts); g = g.drop(columns="ts"); g = g[~g.index.duplicated()].sort_index()
b5 = g.resample("5min", label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
tday1 = (g.index.tz_convert("America/New_York") + pd.Timedelta(hours=7)).normalize().tz_localize(None)
D = g.groupby(tday1).agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"))
tr = pd.concat([D.high - D.low, (D.high - D.close.shift()).abs(), (D.low - D.close.shift()).abs()], axis=1).max(axis=1)
D["atr_prev"] = tr.ewm(alpha=1 / 14, adjust=False).mean().shift(1)
sma20 = D.close.rolling(20).mean()
D["trend_up"] = D.close.shift(1) > sma20.shift(1)                                   # indicator's doji tie-break
D["Dbias"] = np.where((D.close.shift(1) > sma20.shift(1)) & (sma20.shift(1) > sma20.shift(6)), 1,
             np.where((D.close.shift(1) < sma20.shift(1)) & (sma20.shift(1) < sma20.shift(6)), -1, 0))
Wk = D.close.resample("W-FRI").last().dropna(); s10 = Wk.rolling(10).mean()
Wb = pd.Series(np.where((Wk > s10) & (s10 > s10.shift(4)), 1, np.where((Wk < s10) & (s10 < s10.shift(4)), -1, 0)), index=Wk.index)
ry = pd.read_csv("data/data_macro/DFII10.csv", na_values=["."]).dropna(); ry.index = pd.to_datetime(ry.observation_date); ry = ry.DFII10.astype(float)
eu = pd.read_csv("futures/data/daily/6E=F_yahoo_daily.csv"); eu.index = pd.to_datetime(eu.date); eu = eu.close.astype(float)
eu20 = eu.rolling(20).mean()
days = pd.DataFrame(index=D.index)
days["W"] = pd.merge_asof(pd.DataFrame({"d": D.index}), pd.DataFrame({"d": Wb.index, "w": Wb.values}), on="d", direction="backward", allow_exact_matches=False).w.fillna(0).astype(int).values
ryc = (ry - ry.shift(5)); r_prev = pd.merge_asof(pd.DataFrame({"d": D.index}), pd.DataFrame({"d": ryc.index, "v": ryc.values}), on="d", direction="backward", allow_exact_matches=False).v.values
eua = (eu > eu20).astype(float); e_prev = pd.merge_asof(pd.DataFrame({"d": D.index}), pd.DataFrame({"d": eua.index, "v": eua.values}), on="d", direction="backward", allow_exact_matches=False).v.values
days["F"] = np.where((r_prev < 0) & (e_prev == 1), 1, np.where((r_prev > 0) & (e_prev == 0), -1, 0))
days["D"] = D.Dbias.values; days["HTF"] = np.where((days.W == days.D) & (days.W != 0), days.W, 0)
days["HTFF"] = np.where((days.HTF == days.F) & (days.HTF != 0), days.HTF, 0)

COST, TICK = 0.32, 0.1
O, H, L, C = (b5[k].to_numpy() for k in ("open", "high", "low", "close")); T = b5.index; pos = {t: i for i, t in enumerate(T)}


def outcome(i, end_ts, atr, long_):
    o, h, l, c = O[i], H[i], L[i], C[i]
    r = max(abs(c - (l if long_ else h)) + 0.5 * (h - l), 0.03 * atr)
    sl = round((c - r if long_ else c + r) / TICK) * TICK; tp = round((c + r if long_ else c - r) / TICK) * TICK
    for j in range(i + 1, len(T)):
        if T[j] >= end_ts: x = O[j]; break
        if (L[j] <= sl) if long_ else (H[j] >= sl): x = sl; break
        if (H[j] >= tp) if long_ else (L[j] <= tp): x = tp; break
    else: return np.nan
    return ((x - c) if long_ else (c - x)) / r - COST / r


ldn = T.tz_convert("Europe/London").strftime("%Y-%m-%d %H:%M"); nyk = T.tz_convert("America/New_York").strftime("%Y-%m-%d %H:%M")
rows = []
for d in D.index:
    if pd.isna(D.at[d, "atr_prev"]): continue
    for ses, key in (("London", d.strftime("%Y-%m-%d") + " 08:00"), ("New York", d.strftime("%Y-%m-%d") + " 09:30")):
        idx = np.where((ldn if ses == "London" else nyk) == key)[0]
        if not len(idx): continue
        i = int(idx[0]); t0 = T[i]; end_ts = t0 + pd.Timedelta(minutes=60)
        cdir = 1 if C[i] > O[i] else -1 if C[i] < O[i] else (1 if D.at[d, "trend_up"] else -1)
        rows.append(dict(day=d, ses=ses, cdir=cdir, RL=outcome(i, end_ts, D.at[d, "atr_prev"], True), RS=outcome(i, end_ts, D.at[d, "atr_prev"], False)))
S = pd.DataFrame(rows).dropna(); S = S.join(days, on="day")
S.to_csv("HTF_CLAUDE5M_SETUPS.csv", index=False)


def run(side_rule):
    """side_rule(row) -> +1 / -1 / 0 (skip). One loss ends the day inside the variant. Returns the list of (day, R, RL, RS, side)."""
    out = []
    for d, grp in S.groupby("day", sort=True):
        lost = False
        for _, r in grp.sort_values("ses").iterrows():                # 'London' < 'New York'
            if r.ses == "New York" and lost: continue
            sd = side_rule(r)
            if sd == 0: continue
            R = r.RL if sd > 0 else r.RS; out.append((d, R, r.RL, r.RS, sd))
            if r.ses == "London" and R <= 0: lost = True
    return pd.DataFrame(out, columns=["day", "R", "RL", "RS", "side"])


rng = np.random.default_rng(20261027)
base = run(lambda r: r.cdir)
print("indicator alone: n %d, mean %+.3f R, total %+.1f R" % (len(base), base.R.mean(), base.R.sum()))
VARS = {"V1 W filter": lambda r: r.cdir if r.cdir == r.W else 0, "V2 HTF filter": lambda r: r.cdir if r.cdir == r.HTF else 0,
        "V3 HTF+F filter": lambda r: r.cdir if r.cdir == r.HTFF else 0, "V4 HTF override": lambda r: r.HTF, "V5 HTF+F override": lambda r: r.HTFF}
for name, rule in VARS.items():
    x = run(rule); n = len(x); m = x.R.mean() if n else np.nan
    if "filter" in name:
        pool = base.R.to_numpy(); sims = np.array([rng.choice(pool, n, replace=False).mean() for _ in range(20000)]) if 0 < n <= len(pool) else np.array([np.nan])
    else:
        flips = rng.integers(0, 2, (20000, n)); sims = np.where(flips == 1, x.RL.to_numpy(), x.RS.to_numpy()).mean(axis=1)
    p = float((sims >= m).mean()) if n else np.nan
    yrs = x.groupby(x.day.dt.year).R.mean(); ypos = int((yrs.loc[2020:2026] > 0).sum())
    ok = n >= 300 and m > 0 and p <= 0.01 and ypos >= 5
    print("%-18s n %4d, wins %4.1f%%, mean %+.3f R, total %+6.1f R, random P %.3f, years>0 (2020-26) %d/7 -> %s | %s" % (
        name, n, 100 * (x.R > 0).mean(), m, x.R.sum(), p, ypos, "WORKS" if ok else "no",
        " ".join("%d:%+.2f" % (y, v) for y, v in yrs.items())))
