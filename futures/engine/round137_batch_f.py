"""
Round 137, batch F: walk-forward machine learning across 9 futures markets.
Pre-registered 2026-09-26 -- features, models, hyperparameters, trading rule and
verdict rule committed before any result is run.

Why: batches A-E proposed one pattern at a time, each raising the bar. Here one
fixed pipeline learns from all signals together, and every prediction it trades is
on a year the model has not seen (expanding-window walk-forward). Each model
counts as ONE ledger entry.

Data: batch D's daily frames (round135_batch_d.market_frame: 18:00 ET open ->
settlement, a legal Broker hold; the data-quality rule; R units; costs) for ES,
NQ, YM, RTY (2017-), GC (2008-), CL, HG (2005-), 6E, ZN. Silver excluded (2011 only).

Features for market m on day t -- all known at the 18:00 open (from settlements
through day t-1):
  own trend z_k = sum of the last k open->close returns / (20-day SD * sqrt(k)),
    k in {1, 5, 20, 60}; vol regime = log(20-day SD / 100-day SD)
  cross-market z_1 of ES, ZN, 6E, CL, GC (yesterday, in their own SD units; 0 if missing)
  calendar: day of week; FOMC statement day (data/events); jobs-report day (BLS
    timing rule, as batch E); pre-holiday (as batch D); last-2 / first-2 trading
    days of the month (NYSE calendar from SPY)
  market one-hot
Target: sign of day t's open->close return. One pooled model for all markets.

Walk-forward: for each year Y = 2008 .. 2026, train on every row dated before
1 Jan Y (from 2001), predict year Y.
Models (fixed): (a) L2 logistic regression, C=0.1, standardized features;
(b) HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200,
min_samples_leaf=200, l2_regularization=1.0, random_state=0).
Trade rule: long if p > 0.5, short if p < 0.5, but only when |p - 0.5| is in the
top 30% of the model's own |p - 0.5| on its TRAINING rows (a causal threshold).
Each trade: open -> close, R units, costs as batch D.

Verdict (batch D's judge): predictions 2008-12 = "in-sample" slot, 2013-26 =
"out-of-sample" slot, 2020-26 on its own. 2 variants take the ledger from k=136
to k=138: candidate = net and before-cost mean R > 0, P(edge>0) >= 0.95 on
2008-12, >= 1 - 0.01/138 on 2013-26, and 2020-26 mean R > 0.
"""
import os, sys, json, subprocess, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import HistGradientBoostingClassifier
import idea_harness as H
import round135_batch_d as D
import round136_batch_e as E
from round122b_tom_long_history import load_daily

warnings.filterwarnings("ignore")
MARKETS = ["ES=F", "NQ=F", "YM=F", "RTY=F", "GC=F", "CL=F", "HG=F", "6E=F", "ZN=F"]
CROSS = ["ES=F", "ZN=F", "6E=F", "CL=F", "GC=F"]
N_VARIANTS = 2


def build_panel():
    frames = {s: D.market_frame(s) for s in MARKETS}
    z1 = {}
    for s, d in frames.items():
        z1[s] = (d["r"] / d["sd"]).rename(s)
    z1 = pd.concat(z1.values(), axis=1)  # yesterday's move is z1.shift(1) on each market's own calendar
    nyse = load_daily("SPY").index
    nxt = pd.Series(nyse[1:], index=nyse[:-1])
    pre_holiday = {d for d, n in nxt.items() if np.busday_count(d.date() + pd.Timedelta(days=1), n.date()) >= 1}
    ym = nyse.year * 12 + nyse.month
    pos = pd.Series(1, index=nyse).groupby(ym).cumcount().values
    rpos = pd.Series(1, index=nyse)[::-1].groupby(ym[::-1]).cumcount()[::-1].values
    month_end, month_start = set(nyse[rpos <= 1]), set(nyse[pos <= 1])
    fomc = set(pd.read_csv(E.EVENTS, parse_dates=["date"])["date"])
    jobs = set(E.jobs_report_dates())
    rows = []
    for s, d in frames.items():
        f = pd.DataFrame(index=d.index)
        r = d["r"]
        sd100 = r.shift(1).rolling(100, min_periods=80).std()
        for k in [1, 5, 20, 60]:
            f[f"z{k}"] = r.shift(1).rolling(k, min_periods=k).sum() / (d["sd"] * np.sqrt(k))
        f["volreg"] = np.log(d["sd"] / sd100)
        for c in CROSS:
            f[f"x_{c}"] = z1[c].shift(1).reindex(d.index).fillna(0.0) if c != s else 0.0
        f["dow"] = d.index.dayofweek
        f["fomc"] = d.index.isin(fomc).astype(int)
        f["jobs"] = d.index.isin(jobs).astype(int)
        f["preh"] = d.index.isin(pre_holiday).astype(int)
        f["m_end"] = d.index.isin(month_end).astype(int)
        f["m_start"] = d.index.isin(month_start).astype(int)
        for m in MARKETS:
            f[f"mk_{m}"] = int(m == s)
        f["market"], f["r"], f["sd"], f["cost_r"] = s, r, d["sd"], d["cost_r"]
        rows.append(f)
    p = pd.concat(rows).dropna(subset=["z60", "volreg"])
    p = pd.get_dummies(p, columns=["dow"], prefix="dow", dtype=int)
    return p.sort_index()


def walk_forward(panel, make_model, scale):
    feats = [c for c in panel.columns if c not in ("market", "r", "sd", "cost_r")]
    out = []
    for y in range(2008, 2027):
        tr = panel[(panel.index < pd.Timestamp(y, 1, 1)) & (panel.index >= "2001-01-01")]
        te = panel[(panel.index >= pd.Timestamp(y, 1, 1)) & (panel.index < pd.Timestamp(y + 1, 1, 1))]
        if te.empty:
            continue
        X, Xt = tr[feats].values.astype(float), te[feats].values.astype(float)
        if scale:
            sc = StandardScaler().fit(X)
            X, Xt = sc.transform(X), sc.transform(Xt)
        m = make_model().fit(X, (tr["r"] > 0).astype(int).values)
        thresh = np.quantile(np.abs(m.predict_proba(X)[:, 1] - 0.5), 0.70)
        p = m.predict_proba(Xt)[:, 1]
        take = np.abs(p - 0.5) > thresh
        dirn = np.sign(p - 0.5)
        sel = te[take]
        gross = dirn[take] * sel["r"].values / sel["sd"].values
        out.append(pd.DataFrame({"date": sel.index, "market": sel["market"].values, "gross": gross,
                                 "pnl": gross - sel["cost_r"].values, "p": p[take]}))
    return pd.concat(out, ignore_index=True)


if __name__ == "__main__":
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k = H.ledger_count() + N_VARIANTS
    panel = build_panel()
    print(f"panel: {len(panel):,} market-days, {panel.index.min().date()}..{panel.index.max().date()}, "
          f"{len([c for c in panel.columns if c not in ('market', 'r', 'sd', 'cost_r')])} features; "
          f"k after batch F = {k}, OOS bar {H.oos_bar(k):.5f}\n")
    models = [("F1a walk-forward logistic regression (L2, C=0.1)", lambda: LogisticRegression(C=0.1, max_iter=2000), True),
              ("F1b walk-forward gradient boosting (depth 3)", lambda: HistGradientBoostingClassifier(
                  max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=200, l2_regularization=1.0,
                  random_state=0), False)]
    rows = []
    for name, mk, scale in models:
        tr = walk_forward(panel, mk, scale)
        hit = ((tr["gross"] > 0).mean())
        print(f"  {name}: {len(tr):,} trades ({len(tr) / len(panel[panel.index >= '2008']):.0%} of market-days), "
              f"direction hit rate {hit:.1%}")
        rows.append(D.judge_variant(name, tr, k))
    lines = [f"| {n} | 2026-09-26 | {r['name']} (R units) | Round 137 batch F (pre-registered) | {commit} | {r['n']} "
             f"| {r['exp']:+.3f}R | {r['exp_gross']:+.3f}R | {r['p_is']:.2f} / {r['p_oos']:.3f} | "
             f"{'CANDIDATE' if r['candidate'] else 'no edge'} |" for n, r in enumerate(rows, start=H.ledger_count() + 1)]
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round137_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n==== {sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()} ====")
