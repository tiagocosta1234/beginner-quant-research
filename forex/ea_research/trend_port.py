"""TREND-PORT exactly as in PREREG_TREND_PORT.md.  python -m forex.ea_research.trend_port [--dry] [--hold]"""
import sys, glob, os, numpy as np, pandas as pd

HOLD = "--hold" in sys.argv
DRY = "--dry" in sys.argv
END = pd.Timestamp("2026-10-01" if HOLD else "2025-12-31")
FX = ["AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD", "CADCHF", "CADJPY", "CHFJPY", "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD",
      "EURUSD", "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD", "GBPUSD", "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
NONFX = {"SP": "US500.cash", "NSDQ": "US100.cash", "DOW": "US30.cash", "DAX": "GER40.cash", "NIKKEI": "JP225.cash", "ASX": "AUS200.cash",
         "XAUUSD": "XAUUSD", "XAGUSD": "XAGUSD", "BRENT": "UKOIL.cash", "WTI": "USOIL.cash", "BTCUSD": "BTCUSD", "ETHUSD": "ETHUSD",
         "LTCUSD": "LTCUSD", "XRPUSD": "XRPUSD", "BNBUSD": "BNBUSD", "ADAUSD": "ADAUSD", "DOGEUSD": "DOGEUSD"}
MARK = {m: m for m in FX}
MARK.update(NONFX)
cl = {}
for name, f in MARK.items():
    p = f"forex/data/{f}_D1.parquet"
    if not os.path.exists(p):
        continue
    d = pd.read_parquet(p, columns=["time", "close"])
    d["date"] = pd.to_datetime(d.time, unit="s").dt.normalize() if np.issubdtype(d.time.dtype, np.number) else pd.to_datetime(d.time).dt.normalize()
    s = d.drop_duplicates("date").set_index("date").close
    cl[name] = s[(s.index >= "2020-01-01") & (s.index <= END)]
P = pd.DataFrame(cl).sort_index()
P = P[P.index.dayofweek < 5].ffill(limit=5)
R0 = P.pct_change()      # NaN before a market's history starts (no fake zero-vol history)
R = R0.fillna(0.0)
for m in list(P.columns):   # leave a market out until its price history starts
    pass
# half-spreads from MT5 M1 (last 12 months, hours 2..21)
half = {}
for m in P.columns:
    p = f"forex/data_mt5/{m}_M1_rates.parquet"
    if not os.path.exists(p):
        half[m] = np.nan
        continue
    d = pd.read_parquet(p, columns=["t", "bo", "ao"])
    d = d[(d.t > d.t.max() - 365 * 86400) & (((d.t // 3600) % 24) >= 2) & (((d.t // 3600) % 24) <= 21) & (d.bo > 0)]
    half[m] = float(np.median((d.ao - d.bo) / ((d.ao + d.bo) / 2)) * 1e4 / 2)
half = pd.Series(half)
print("markets", P.shape[1], "of", len(MARK), "| first date", P.index[0].date(), "last", P.index[-1].date(), "| median half-spread bp: FX %.2f, non-FX %.2f" % (half[[m for m in P.columns if m in FX]].median(), half[[m for m in P.columns if m not in FX]].median()))
missing = [m for m in P.columns if np.isnan(half[m])]
print("no MT5 broker spread file:", missing)
half = half.fillna(half.median())
vol = R0.ewm(span=60, min_periods=60).std() * np.sqrt(252)
vol = vol.where(vol > 1e-4)
sig = {}
for L in (20, 60, 120, 250):
    mom = P / P.shift(L) - 1
    sig[L] = np.sign(mom).where(mom.notna() & P.notna())
sig["COMBO"] = sum(sig[L] for L in (20, 60, 120, 250)) / 4
sig["LONG"] = (P.notna() & vol.notna()).astype(float)   # drift yardstick
rebal = (P.index.dayofweek == 4)
UNI = {"ALL": list(P.columns), "FX": [m for m in P.columns if m in FX], "NONFX": [m for m in P.columns if m not in FX]}


def run(sg: pd.DataFrame, universe, cost_mult=1.0):
    s = sg[universe]
    active = s.notna() & vol[universe].notna() & P[universe].notna()
    n = active.sum(1).replace(0, np.nan)
    w = (s.where(active) * 0.10 / vol[universe]).div(n, axis=0).fillna(0.0)
    wt = w.where(pd.Series(rebal, index=w.index), np.nan).ffill().shift(1).fillna(0.0)   # set at Friday close, held from the next day
    gross = (wt * R[universe]).sum(1)
    turn = (wt.diff().abs() * (half[universe] / 1e4) * cost_mult).sum(1)
    return gross - turn, wt.abs().sum(1)


def stats(r):
    r = r.dropna()
    if len(r) < 60 or r.std() == 0:
        return dict(sh=np.nan, ann=np.nan, vol=np.nan, dd=np.nan, n=len(r))
    c = (1 + r).cumprod()
    return dict(sh=r.mean() / r.std() * np.sqrt(252), ann=r.mean() * 252, vol=r.std() * np.sqrt(252), dd=float((c / c.cummax() - 1).min()), n=len(r))


def seg(r, a, b):
    return r[(r.index >= a) & (r.index <= b)]


DEV = ("2021-01-04", "2023-12-31")
VAL = ("2024-01-01", "2025-12-31")
ALLW = ("2021-01-04", "2025-12-31")
if DRY:
    r, g = run(sig["COMBO"], UNI["ALL"])
    print("active markets by year:", {y: int(((sig["COMBO"][UNI["ALL"]].notna()) & vol[UNI["ALL"]].notna()).loc[str(y)].sum(1).mean()) for y in range(2021, 2026)})
    print("COMBO ALL: sample", stats(seg(r, *ALLW)), "avg gross leverage %.2f" % g.loc["2021":].mean())
    print("hand check one Friday weight row (first 5 nonzero):", (sig["COMBO"].loc["2023-03-03", UNI["ALL"][:5]] * 0.10 / vol.loc["2023-03-03", UNI["ALL"][:5]]).round(2).to_dict())
    sys.exit()


def boot_p(r, rng, B=2000, mean_block=21):
    x = r.to_numpy()
    n = len(x)
    if n < 100:
        return np.nan
    obs = x.mean() / x.std() * np.sqrt(252)
    cnt = 0
    xc = x - x.mean()
    for _ in range(B):
        idx = np.empty(n, int)
        i = 0
        while i < n:
            s0 = rng.integers(0, n)
            L = min(rng.geometric(1 / mean_block), n - i)
            idx[i:i + L] = (s0 + np.arange(L)) % n
            i += L
        y = xc[idx]
        cnt += y.mean() / y.std() * np.sqrt(252) >= obs
    return (cnt + 1) / (B + 1)


rng = np.random.default_rng(5)
rows = []
yard = {u: run(sig["LONG"], UNI[u])[0] for u in UNI}
print("long-only drift yardstick Sharpe (DEV / VAL / ALL):", {u: tuple(round(stats(seg(yard[u], *w))['sh'], 2) for w in (DEV, VAL, ALLW)) for u in UNI})
print(f"{'cell':14s}{'DEV sh':>7s}{'VAL sh':>7s}{'ALL sh':>7s}{'ann%':>6s}{'vol%':>6s}{'maxDD%':>7s}{'p':>7s}{'2xcost sh':>10s}{'yard':>6s}  verdict")
res = {}
for u in UNI:
    for k in (20, 60, 120, 250, "COMBO"):
        r, g = run(sig[k], UNI[u])
        r2, _ = run(sig[k], UNI[u], 2.0)
        sd, sv, sa = stats(seg(r, *DEV)), stats(seg(r, *VAL)), stats(seg(r, *ALLW))
        p = boot_p(seg(r, *ALLW), rng)
        ys = stats(seg(yard[u], *ALLW))["sh"]
        claim = sa["sh"] >= 1.2 and p <= 0.0033 and sd["sh"] >= 0.8 and sv["sh"] >= 0.5 and sa["sh"] > ys
        sugg = sd["sh"] > 0 and sv["sh"] > 0 and sa["sh"] >= 0.5 and sa["sh"] > ys
        res[(u, k)] = (sa["sh"], claim, sugg, r)
        print(f"{u + ' ' + str(k):14s}{sd['sh']:7.2f}{sv['sh']:7.2f}{sa['sh']:7.2f}{sa['ann'] * 100:6.1f}{sa['vol'] * 100:6.1f}{sa['dd'] * 100:7.1f}{p:7.4f}{stats(seg(r2, *ALLW))['sh']:10.2f}{ys:6.2f}  " + ("CLAIM" if claim else "suggestive" if sugg else "-"))
best = max(res, key=lambda z: res[z][0])
r = seg(res[best][3], *ALLW)
pl = []
blocks = np.array_split(np.arange(len(r)), max(len(r) // 60, 1))
x = r.to_numpy()
for _ in range(300):
    order = rng.permutation(len(blocks))
    y = np.concatenate([x[blocks[i]] for i in order])
    pl.append(y.mean() / y.std() * np.sqrt(252))
print("best cell", best, "Sharpe %.2f; block-reorder placebo of its own returns: 95th pct %.2f (mean reorder keeps Sharpe by construction, see note)" % (res[best][0], np.percentile(pl, 95)))
print("CLAIMS:", [k for k, v in res.items() if v[1]], "| SUGGESTIVE:", [k for k, v in res.items() if v[2] and not v[1]])
