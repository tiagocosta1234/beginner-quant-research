"""
Round 149, batch O: a 1:1 intraday edge, searched for by walk-forward models.
Pre-registered 2026-09-26, committed before any result is run.

the trader: "get a 1:1 risk to reward edge for the journey, find inefficiencies in the
intraday market". A 1:1 bracket (target = stop = S) wins 50% on a random walk; with
costs (~0.04R) break-even is ~52%, and the pass-speed gate needs roughly 57-64%
depending on trades per day (dry-run table below). Instead of hand-picking one more
setup, a model looks for the market states in which +S comes before -S more (or less)
often than half the time, and trades only its most confident calls.

Data: 24-hour 1-minute MNQ and MGC (idea_harness.load_days; one contract per day),
2022-12 .. 2026-09. S = 0.10 x the average full-session range of the previous 20 days
(~30 MNQ points, ~$4 gold).
Decision points: every 5 minutes (bar closes at :00, :05, ...), MNQ 09:35 -> 15:30 ET,
MGC 08:30 -> 15:30 ET (gold's active hours from the COMEX open), at least 120 bars
into the session.
Label: 1 if the price reaches entry + S before entry - S (1-minute highs/lows, by
16:00 ET); 0 if the reverse; points where neither is reached, or both in the same
minute, are left out of training.
Features, all known at the decision bar's close, distances in units of S: price moves
over the last 1, 5, 15, 30, 60, 120 minutes; distance from the session VWAP (from
18:00), from the session open, from the 09:30 open (missing before it), from the
overnight high and low (missing before 09:30), from the previous day's high, low and
close (same contract; missing otherwise); position in the day's range so far; the
day's range so far; the gap from the previous close to the 18:00 open; the SD of
1-minute moves over the last 30 minutes; volume of the last 5 minutes / the average
5 minutes of the last hour; minute of the session; weekday; instrument.
Models (one pooled model for both instruments, retrained each month on all earlier
points -- walk-forward, from 2024-01):
  O1  HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200,
      l2_regularization=1.0, min_samples_leaf=200, random_state=0)
  O2  median imputation + standardisation + LogisticRegression(C=0.1)
Trading: at a decision point, long if the predicted probability is at or above the 90th
percentile of all earlier walk-forward predictions of that model (for the first month:
of its in-sample predictions), short if at or below the 10th. 1:1 bracket entry +- S,
idea_harness.resolve_bracket (entry at the bar's close, one position at a time per
instrument, stop first on a tie, flat at 16:00 ET, no entries after 15:30), $300 risk,
whole contracts, commission + 2 ticks.
IS = walk-forward trades 2024-01 .. 2025-06; OOS = 2025-07 .. 2026-09.
2 variants take the ledger from k=181 to k=183.

Candidate (all required): net and before-cost mean > 0; IS P(edge>0) >= 0.95; OOS
P(edge>0) >= 1 - 0.01/183; net mean > 0 on MNQ and on MGC; pass-speed gate
P(pass a $50K Test within 10 trading days) >= 0.50 at the best size.
Descriptive: accuracy of the confident calls on all their decision points (traded or
not); a placebo (random calls, same count per day) through the same brackets.

Power notes (dry run, before any result): 140,255 decision points (MNQ 64,626, MGC
75,629); 104,029 in the 33 walk-forward months from 2024-01; 89% of labels resolve.
Median S: MNQ 30.4 points, gold $3.81. A placebo at the same call rate gives ~10,660
trades, ~15.6 a day (both instruments, one position each), median cost 0.032R (4
contracts). The gate needs a 1:1 win rate of about 58% at 7.8 trades a day, 56.1% at
15.6, 55.3% at 23.5 -- 5-8 points above a coin flip. With ~4,800 OOS trades, the
0.99995 bar needs roughly 54-55% (about 3 points above the ~51.6% cost break-even).
Fixed in the dry run, before any result: the 09:30-open index matched evening bars
(18:xx is "after 09:30" as a clock time); it now points at the first regular-session bar.
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import idea_harness as H
import round120_goal_judge as J
from round147_batch_m import RISK, full, load, gate_row

N_VARIANTS = 2
S_FRAC = 0.10
WINDOW = {"MNQ": (dt.time(9, 35), dt.time(15, 30)), "MGC": (dt.time(8, 30), dt.time(15, 30))}
WF_START = pd.Timestamp("2024-01-01")
Q = 0.10
FEATURES = ["r1", "r5", "r15", "r30", "r60", "r120", "d_vwap", "d_sopen", "d_rth_open", "d_onh", "d_onl",
            "d_pdh", "d_pdl", "d_pdc", "range_pos", "range_sofar", "gap", "vol30", "relvol", "minute", "dow", "inst"]
MODELS = {
    "O1": ("O1 walk-forward gradient boosting, 1:1 bracket, top/bottom 10%",
           lambda: HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, l2_regularization=1.0,
                                                  min_samples_leaf=200, random_state=0)),
    "O2": ("O2 walk-forward logistic regression, 1:1 bracket, top/bottom 10%",
           lambda: make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=0.1, max_iter=2000))),
}


def stop_sizes(days):
    rng = pd.Series([full(d)["high"].max() - full(d)["low"].min() for d in days], index=[d["tday"] for d in days])
    return (S_FRAC * rng.shift(1).rolling(20, min_periods=15).mean()).to_dict()


def first_hit(hi, lo, i, up, dn):
    """1 if up is reached before dn after bar i, 0 if dn first, nan if neither or both in one bar."""
    h, l = hi[i + 1:], lo[i + 1:]
    a = np.flatnonzero(h >= up)
    b = np.flatnonzero(l <= dn)
    ia, ib = (a[0] if len(a) else np.inf), (b[0] if len(b) else np.inf)
    if ia == ib:
        return np.nan
    return 1.0 if ia < ib else 0.0


def day_points(d, prev, S, sym):
    b = full(d)
    t = b.index
    o, h, l, c, v = (b[k].values for k in ("open", "high", "low", "close", "vol"))
    tp = (h + l + c) / 3
    vwap = np.cumsum(tp * v) / np.maximum(np.cumsum(v), 1e-9)
    hi_sofar, lo_sofar = np.maximum.accumulate(h), np.minimum.accumulate(l)
    times = t.time
    a, z = WINDOW[sym]
    on = d["on"]
    rth_i0 = len(on) if len(d["session"]) and d["session"].index[0].time() < dt.time(10, 0) else None  # first 09:30 bar
    onh, onl = on["high"].max(), on["low"].min()
    same = prev is not None and prev["contract"] == d["contract"] and (d["tday"] - prev["tday"]).days <= 5
    pb = full(prev) if same else None
    pdh, pdl, pdc = (pb["high"].max(), pb["low"].min(), pb["close"].iloc[-1]) if same else (np.nan, np.nan, np.nan)
    gap = (o[0] - d["prev_close"]) / S if d["prev_close"] == d["prev_close"] else np.nan
    rows = []
    for i in np.flatnonzero([(x.minute % 5 == 0) and (a <= x <= z) for x in times]):
        if i < 120:
            continue
        after_rth = rth_i0 is not None and i >= rth_i0
        rng = hi_sofar[i] - lo_sofar[i]
        dc = np.diff(c[i - 30:i + 1])
        rows.append(dict(
            ts=t[i], sym=sym, entry=c[i], S=S,
            r1=(c[i] - c[i - 1]) / S, r5=(c[i] - c[i - 5]) / S, r15=(c[i] - c[i - 15]) / S, r30=(c[i] - c[i - 30]) / S,
            r60=(c[i] - c[i - 60]) / S, r120=(c[i] - c[i - 120]) / S, d_vwap=(c[i] - vwap[i]) / S,
            d_sopen=(c[i] - o[0]) / S, d_rth_open=(c[i] - o[rth_i0]) / S if after_rth else np.nan,
            d_onh=(c[i] - onh) / S if after_rth else np.nan, d_onl=(c[i] - onl) / S if after_rth else np.nan,
            d_pdh=(c[i] - pdh) / S, d_pdl=(c[i] - pdl) / S, d_pdc=(c[i] - pdc) / S,
            range_pos=(c[i] - lo_sofar[i]) / rng if rng > 0 else 0.5, range_sofar=rng / S, gap=gap,
            vol30=dc.std() / S, relvol=v[i - 4:i + 1].sum() / max(v[i - 59:i + 1].sum() / 12, 1e-9),
            minute=((t[i].hour * 60 + t[i].minute) - 18 * 60) % 1440, dow=d["tday"].dayofweek,
            inst=0 if sym == "MNQ" else 1,
            y=first_hit(h, l, i, c[i] + S, c[i] - S)))
    return rows


def build_points(data):
    out = []
    for sym, (days, _) in data.items():
        S_by_day = stop_sizes(days)
        prev = None
        for d in days:
            S = S_by_day.get(d["tday"], np.nan)
            if S > 0:
                out.extend(day_points(d, prev, S, sym))
            prev = d
    p = pd.DataFrame(out)
    p["month"] = p["ts"].dt.to_period("M")
    return p


def walk_forward(points, make):
    pred = pd.Series(np.nan, index=points.index)
    hist = []
    lo_hi = {}
    for m in sorted(points.loc[points["ts"] >= WF_START, "month"].unique()):
        train = points[(points["ts"] < m.start_time) & points["y"].notna()]
        test = points["month"] == m
        model = make().fit(train[FEATURES], train["y"])
        p = model.predict_proba(points.loc[test, FEATURES])[:, 1]
        ref = np.concatenate(hist) if hist else model.predict_proba(train[FEATURES])[:, 1]
        lo_hi[m] = (np.quantile(ref, Q), np.quantile(ref, 1 - Q))
        pred[test] = p
        hist.append(p)
    return pred, lo_hi


def calls(points, pred, lo_hi):
    lo = points["month"].map(lambda m: lo_hi.get(m, (np.nan, np.nan))[0])
    hi = points["month"].map(lambda m: lo_hi.get(m, (np.nan, np.nan))[1])
    return pd.Series(np.where(pred >= hi, 1, np.where(pred <= lo, -1, 0)), index=points.index)


def trades_from_calls(data, points, direction):
    parts = []
    for sym, (_, bars) in data.items():
        m = (points["sym"] == sym) & (direction != 0)
        p, dr = points[m], direction[m]
        sig = pd.DataFrame({"ts": p["ts"].values, "direction": dr.values, "entry": p["entry"].values,
                            "sl": (p["entry"] - dr * p["S"]).values, "tp": (p["entry"] + dr * p["S"]).values})
        tr = H.resolve_bracket(sig, bars, sym, risk=RISK)
        tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
        tr["sym"] = sym
        parts.append(tr)
    return pd.concat(parts, ignore_index=True)


def needed_win_rate_1to1(n_per_day, cost_r, target_sharpe=0.36):
    for p in np.arange(0.50, 0.9999, 0.0005):
        if (2 * p - 1 - cost_r) / (2 * np.sqrt(p * (1 - p))) * np.sqrt(n_per_day) >= target_sharpe:
            return p
    return np.nan


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k = H.ledger_count() + N_VARIANTS
    print(f"k after batch O = {k}; OOS bar {H.oos_bar(k):.5f}\n", flush=True)
    data = load()
    all_days = sorted({d["tday"] for days, _ in data.values() for d in days})
    points = build_points(data)
    wf = points["ts"] >= WF_START
    if dry:
        print(f"decision points: {len(points)} (MNQ {(points['sym'] == 'MNQ').sum()}, MGC {(points['sym'] == 'MGC').sum()}); "
              f"walk-forward from 2024-01: {wf.sum()}; months {points.loc[wf, 'month'].nunique()}")
        print(f"labels: resolved {points['y'].notna().mean():.3f} (unresolved or same-minute ties left out); "
              f"median S MNQ {points.loc[points['sym'] == 'MNQ', 'S'].median():.1f} pts, MGC ${points.loc[points['sym'] == 'MGC', 'S'].median():.2f}")
        print("feature missing shares:", {f: round(points[f].isna().mean(), 3) for f in FEATURES if points[f].isna().any()})
        rng = np.random.default_rng(0)
        placebo = pd.Series(0, index=points.index)
        pick = wf.values & (rng.random(len(points)) < 2 * Q)
        placebo[pick] = rng.choice([-1, 1], pick.sum())
        tr = trades_from_calls(data, points, placebo)
        wf_days = len([d for d in all_days if d >= WF_START])
        per_day = len(tr) / wf_days
        cost_r = float((tr["cost"] / RISK).median())
        print(f"placebo calls at the same rate (counts only): {int(pick.sum())} calls -> {len(tr)} trades, {per_day:.2f}/day "
              f"(one position at a time), median cost {cost_r:.3f}R, contracts median {tr['contracts'].median():.0f}")
        for n in (per_day / 2, per_day, per_day * 1.5):
            print(f"  at {n:.1f} trades/day the gate needs a 1:1 win rate >= {needed_win_rate_1to1(n, cost_r):.1%}")
        sys.exit()
    rows = []
    for key, (name, make) in MODELS.items():
        pred, lo_hi = walk_forward(points, make)
        dirn = calls(points, pred, lo_hi).where(wf, 0)
        conf = points[(dirn != 0) & points["y"].notna()]
        acc = ((conf["y"] == 1) == (dirn[conf.index] == 1)).mean()
        tr = trades_from_calls(data, points, dirn)
        wf_days = [d for d in all_days if d >= WF_START]
        r = H.test_idea(name + ", MNQ + MGC", tr, wf_days, "MNQ", k, risk=RISK)
        per = tr.groupby("sym")["pnl"].mean()
        g, _ = gate_row(tr, wf_days)
        both = bool(len(per) == 2 and (per > 0).all())
        per_day = len(tr) / len(wf_days)
        need = needed_win_rate_1to1(per_day, float((tr["cost"] / RISK).median()))
        r.update(call_accuracy=float(acc), n_calls=int((dirn != 0).sum()), win_needed=need, gate=g, both_positive=both,
                 per_market={s: float(v) for s, v in per.items()})
        r["candidate"] = bool(r["candidate"] and both and g["pass_10d"] >= 0.50)
        e = pd.to_datetime(tr["entry_ts"])
        print(f"      calls {r['n_calls']}, accuracy on all confident calls {acc:.1%} | trades win {r['win']:.1%} "
              f"(IS {(tr.loc[e < J.OOS_START, 'pnl'] > 0).mean():.1%}, OOS {(tr.loc[e >= J.OOS_START, 'pnl'] > 0).mean():.1%}; "
              f"gate needs {need:.1%} at {per_day:.1f}/day) | " + ", ".join(f"{s} ${v:+.1f}" for s, v in per.items())
              + f" | gate: pass <= 10d {g['pass_10d']:.2f} | {'CANDIDATE' if r['candidate'] else 'no'}", flush=True)
        rows.append(r)
    rng = np.random.default_rng(0)
    placebo = pd.Series(0, index=points.index)
    pick = wf.values & (rng.random(len(points)) < 2 * Q)
    placebo[pick] = rng.choice([-1, 1], pick.sum())
    pt = trades_from_calls(data, points, placebo)
    print(f"\n  placebo (random calls, same rate): {len(pt)} trades, win {(pt['pnl'] > 0).mean():.1%}, "
          f"net ${pt['pnl'].mean():+.1f}/trade")
    lines = H.ledger_rows(rows, "Round 149 batch O (pre-registered)", commit)
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round149_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n==== {sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()} ====")
