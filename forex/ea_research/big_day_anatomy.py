"""When do the +2,000 days of the installed system happen? Descriptive, with a Bonferroni across the questions asked (PREREG in the docstring).
Questions fixed before the run (16 binary/level tests, Bonferroni 0.05/16): weekday (5), event day CPI / NFP / FOMC / any (4), gold range of the previous day (tercile top / bottom: 2), gold 5-day trend into the day (up / down: 2), previous day of the system (win / loss: 2), system trailing 10-day P&L > 0 (1).
Outcome: day whose P&L high reached +2,000 (Hi >= 2000). Pools MT5 (12 months) and FT (2022-26) are tested separately and a pattern counts only if it has the same sign in both and pooled p < 0.05/16.
python -m forex.ea_research.big_day_anatomy"""
import os
os.environ["DA_Z"] = "1.5"; os.environ["NQ3_FLOOR"] = "1.67"
import numpy as np, pandas as pd
from scipy import stats
from forex.ea_research import improve_round as I, combo_grid as G
from forex.ea_research.combo_grid import bars
from forex.ea_research.event_macro import server_s
tm, bc, sp = bars; day_of = tm // 86400
d_start = np.searchsorted(day_of, np.unique(day_of)); ud = np.unique(day_of); rng = {}; ret = {}
for k, d in enumerate(ud):
    a = d_start[k]; b = d_start[k + 1] if k + 1 < len(ud) else len(tm); seg = bc[a:b]; rng[d] = np.log(seg.max() / seg.min()); ret[d] = np.log(seg[-1] / seg[0])
cal = pd.read_csv("D:/finance/data_macro/event_calendar.csv"); evd = {kind: set(int(server_s(r.date, 8, 30) // 86400) for r in cal.itertuples() if r.kind == kind) for kind in ("CPI", "NFP", "FOMC")}
rows = []
for pool in ("MT5", "FT"):
    S = G.add_dip(G.pair_series(pool, 1.5, 1.5, I.GUARD), I.Dd, I.GUARD); days = np.asarray(S["days"]); V = np.asarray(S["V"], float); Hi = np.asarray(S["Hi"], float)
    df = pd.DataFrame(dict(pool=pool, day=days, V=V, Hi=Hi)); df["big"] = df.Hi >= 2000; df["wd"] = ((df.day + 3) % 7)
    df["rng_prev"] = [rng.get(d - 1, np.nan) for d in df.day]; df["trend5"] = [sum(ret.get(d - k, 0.0) for k in range(1, 6)) for d in df.day]
    r = df.rng_prev; df["rng_hi"] = r >= r.quantile(2 / 3); df["rng_lo"] = r <= r.quantile(1 / 3); df["tr_up"] = df.trend5 > 0
    df["prev_win"] = df.V.shift(1) > 0; df["prev_loss"] = df.V.shift(1) < 0; df["trail10"] = df.V.rolling(10).sum().shift(1) > 0
    for kind in evd: df[f"ev_{kind}"] = [d in evd[kind] for d in df.day]
    df["ev_any"] = df[[f"ev_{k}" for k in evd]].any(axis=1)
    for w in range(5): df[f"wd{w}"] = df.wd == w
    rows.append(df)
D = pd.concat(rows, ignore_index=True); D = D[D.wd < 5]
tests = [f"wd{w}" for w in range(5)] + ["ev_CPI", "ev_NFP", "ev_FOMC", "ev_any", "rng_hi", "rng_lo", "tr_up", "prev_win", "prev_loss", "trail10"]
print(f"days {len(D)} | big days (Hi>=2000): MT5 {D[D.pool=='MT5'].big.mean()*100:.1f}% FT {D[D.pool=='FT'].big.mean()*100:.1f}%")
out = []
for t in tests:
    res = {}
    for pool in ("MT5", "FT", "ALL"):
        d = D if pool == "ALL" else D[D.pool == pool]; a, b = d[d[t]].big, d[~d[t]].big
        if len(a) < 5: res[pool] = (np.nan, np.nan, len(a)); continue
        tab = [[a.sum(), len(a) - a.sum()], [b.sum(), len(b) - b.sum()]]; res[pool] = (a.mean() * 100, stats.fisher_exact(tab)[1], len(a)); res[pool + "_other"] = b.mean() * 100
    out.append((t, res))
    print(f"{t:9s} MT5 {res['MT5'][0]:5.1f}% (n={res['MT5'][2]:3d}) vs {res.get('mt5_other', np.nan):5.1f}% | FT {res['FT'][0]:5.1f}% (n={res['FT'][2]:4d}) vs {res.get('FT_other', np.nan):5.1f}% | pooled p={res['ALL'][1]:.4f}", flush=True)
BONF = 0.05 / len(tests); keep = [t for t, r in out if r["ALL"][1] < BONF and (r["MT5"][0] - r["mt5_other"]) * (r["FT"][0] - r["FT_other"]) > 0]
print(f"\nBonferroni p < {BONF:.4f} and same sign in both pools: {keep if keep else 'NONE'}")
