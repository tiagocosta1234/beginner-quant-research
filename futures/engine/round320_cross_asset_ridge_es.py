"""
Round 320 (2026-10-03, PRE-REGISTERED): walk-forward ridge on cross-asset DAILY features predicting the next-day ES close-to-close return.

Standing goal (the trader: "keep backtesting and refining until you find something better than our current best"; current best = the validated dip-reversal lead, about +35 bp a trade and sparse,
and the coin-flip bold play, about 40% 1-Step pass by 31 Dec). Ledger checked first (k = 2023): walk-forward logistic / boosting models exist on 1-minute / M15 bracket labels (137-138, 182-183,
463-464) and no ridge on daily cross-asset features predicting ES close-to-close exists.

Data (Yahoo daily closes in futures/data/daily): ES=F target; features from ZN, 6E, CL, HG, GC, SI, YM, NQ (futures) and ^VIX, ^VIX3M, all as of day t's close; target = ES close(t+1)/close(t) - 1.
FEATURES (19): 1-day and 5-day log returns of ZN, 6E, CL, HG, GC, SI; ES 1, 5, 20-day log returns and 20-day realized sigma; VIX level z-score vs its trailing 252 days; VIX 1-day change; VIX / VIX3M - 1.
(ZN's earlier settle time and ^VIX's later one never look ahead: every feature is dated t or earlier and the target is the t -> t+1 close return.)
MODEL: ridge, FIXED alpha = 1000 on features standardized with the training window's mean/sd, no tuning anywhere; expanding window from 2007-08-01, refit on the first trading day of each month using only rows
whose target date <= the day before; predictions for the month use that fit. First scored day 2013-01-02 (2007-08..2012 is warm-up only; nothing is selected on it).
RULES scored (2 hypotheses): H1 LONG/SHORT: position = sign(prediction), +/-1 ES unit; H2 LONG/FLAT: long when prediction > 0 else flat. Cost 1 bp per unit of position change.
BENCHMARKS and statistic: H1 vs 0 (mean net bp a day); H2 vs the exposure-matched always-long (net of H2's own exposure share x mean ES return, i.e. excess over holding the same fraction of days at random).
Date-block bootstrap (20-day blocks, 5,000 draws, seed 320) of the mean daily excess; P = share of draws > 0.
CANDIDATE: both halves (2013-2019 and 2020-2026-09) have a positive mean excess AND the full-period P >= 1 - 0.05/2 = 0.975 for that hypothesis. Not widened after the run (no alpha, feature or horizon changes to rescue a failure).
Ledger rows (2, k + 2) appended by hand after the run. Descriptive scale only: ES unit, no sizing; a candidate would need Round 120-style sizing before anything else.
DRY-RUN COUNTS (no P&L read): 4,812 feature rows 2007-08-01 .. 2026-09-18, 19 features (the docstring first said 15, a miscount fixed before the run), 165 scored months, 3,447 scored days from 2013-01-02, no missing targets.
Leak check (by reading, not P&L): a month's fit uses only rows dated before its first day, and the last such row's target is the return into that first day, known at its close, before any prediction made at that close.
POWER: next-day ES return sd about 110 bp; 3,447 days give a s.e. of the mean about 1.9 bp a day; with 20-day blocks about 2.2 bp. An excess below about +4 bp a day (Sharpe about 0.6) cannot be told from zero.
"""
import os, sys, json
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "data", "daily") + os.sep
ALPHA = 1000.0
START_TRAIN, START_SCORE = pd.Timestamp("2007-08-01"), pd.Timestamp("2013-01-02")


def ld(n):
    return pd.read_csv(f"{D}{n}_yahoo_daily.csv", parse_dates=["date"]).set_index("date").close


def features():
    es = ld("ES=F")
    cols = {}
    for n in ["ZN=F", "6E=F", "CL=F", "HG=F", "GC=F", "SI=F"]:
        c = ld(n).reindex(es.index, method="ffill")
        lc = np.log(c)
        cols[f"{n}_1"] = lc.diff(); cols[f"{n}_5"] = lc.diff(5)
    le = np.log(es)
    cols["ES_1"] = le.diff(); cols["ES_5"] = le.diff(5); cols["ES_20"] = le.diff(20)
    cols["ES_vol20"] = le.diff().rolling(20).std()
    vix = ld("^VIX").reindex(es.index, method="ffill"); v3 = ld("^VIX3M").reindex(es.index, method="ffill")
    cols["VIX_z"] = (vix - vix.rolling(252).mean()) / vix.rolling(252).std()
    cols["VIX_d1"] = vix.diff()
    cols["VIX_term"] = vix / v3 - 1
    X = pd.DataFrame(cols)
    y = le.shift(-1) - le
    df = X.copy(); df["y"] = y
    return df[df.index >= START_TRAIN].dropna(subset=list(cols)), list(cols)


def main(dry):
    df, cols = features()
    df = df.iloc[:-1] if df.y.isna().iloc[-1] else df
    months = sorted({(d.year, d.month) for d in df.index if d >= START_SCORE})
    if dry:
        print(f"feature rows {len(df)} from {df.index[0].date()} to {df.index[-1].date()}, features {len(cols)}, scored months {len(months)}, scored days {(df.index >= START_SCORE).sum()}")
        print("missing y:", int(df.y.isna().sum()), " first scored", df.index[df.index >= START_SCORE][0].date())
        return
    pred = pd.Series(np.nan, index=df.index)
    for (yy, mm) in months:
        first = df.index[(df.index.year == yy) & (df.index.month == mm)][0]
        tr = df[(df.index < first)].dropna(subset=["y"])
        tr = tr[tr.index + pd.Timedelta(days=0) < first]
        mu, sd = tr[cols].mean(), tr[cols].std().replace(0, 1)
        Z = ((tr[cols] - mu) / sd).values; yv = tr.y.values - tr.y.mean()
        w = np.linalg.solve(Z.T @ Z + ALPHA * np.eye(len(cols)), Z.T @ yv)
        te = df[(df.index.year == yy) & (df.index.month == mm)]
        pred.loc[te.index] = ((te[cols] - mu) / sd).values @ w + tr.y.mean()
    s = df[df.index >= START_SCORE].copy(); s["pred"] = pred.loc[s.index]
    s["ret"] = s.y * 1e4
    out = {}
    rng = np.random.default_rng(320)
    for name, pos in (("H1_LONG_SHORT", np.sign(s.pred)), ("H2_LONG_FLAT", (s.pred > 0).astype(float))):
        cost = pos.diff().abs().fillna(abs(pos.iloc[0])) * 1.0
        net = pos * s.ret - cost
        bench = (pos.mean() * s.ret.mean()) if name == "H2_LONG_FLAT" else 0.0
        exc = net - bench                      # constant benchmark per day
        def boot(x):
            v = x.values; nb = len(v) // 20
            idx = rng.integers(0, nb, (5000, nb))
            blocks = v[: nb * 20].reshape(nb, 20).mean(1)
            return float((blocks[idx].mean(1) > 0).mean())
        h1, h2 = exc[exc.index < "2020-01-01"], exc[exc.index >= "2020-01-01"]
        out[name] = dict(days=len(exc), exposure=float((pos != 0).mean()), mean_net_bp=float(net.mean()), mean_excess_bp=float(exc.mean()),
                         sharpe=float(net.mean() / net.std() * np.sqrt(252)), P_full=boot(exc), excess_2013_19=float(h1.mean()), excess_2020_26=float(h2.mean()),
                         hit=float(((np.sign(s.pred) == np.sign(s.y))).mean()),
                         candidate=bool(h1.mean() > 0 and h2.mean() > 0 and boot(exc) >= 0.975))
        print(name, {k: round(v, 3) if isinstance(v, float) else v for k, v in out[name].items()})
    print("ES buy&hold mean bp/day", round(s.ret.mean(), 2), " sharpe", round(s.ret.mean() / s.ret.std() * np.sqrt(252), 2))
    json.dump(out, open(os.path.join(HERE, "round320_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
