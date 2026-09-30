"""
Round 228 (2026-09-30): bounded ML meta-labeling on the trader's VWAP-Z leg.
Plan: futures/docs/ML_META_LABELING_PLAN.md (written the same
day by the previous account; this is its build). PRE-REGISTRATION -- every
design decision below is fixed BEFORE any label/P&L is looked at.

QUESTION. the trader's VWAP-Z leg (round49: session-VWAP z-score >= 2.5 plus a
one-bar reversal, resolved with round19's ATR-trail exit at $1,200 risk)
is a real, non-random entry. Do a handful of causal features known at
entry time predict which of its trades win, well enough that skipping the
low-scoring ones raises real expectancy, out-of-sample, under a purged
walk-forward and a final untouched holdout? NOT an "iterate until it
finds an edge" search: one model, one feature set, one threshold rule,
zero tuning knobs. The result is reported however it lands.

BASE TRADE SET. The leg's real trade sequence, not every raw signal:
build_zscore_signals(z>=2.5) yields ~38,700 raw signals (~40/day,
heavily overlapping on consecutive bars), so labeling them all would
give thousands of near-duplicate, autocorrelated rows. Instead the leg
is resolved ALONE, one position at a time, with round204's
_resolve_trailing_sequential_per_signal_risk (the same resolver the trader's
combined sequence uses; risk 1200; TRAIL_ATR_MULT). Each resulting trade
is one row. Filtering is evaluated as taken-vs-skipped among these base
trades WITHOUT re-resolving (a deployed filter would also free slots for
later signals; that second-order effect is deliberately excluded, the
same confound Round 224 isolated).

LABEL. y = 1 if net trade P&L > 0 else 0. Deviation from the plan's
"triple-barrier": the ATR-trail exit has no fixed profit barrier, so the
triple-barrier collapses to {trail-stop, session-flatten}; session-flatten
trades are kept and labeled by their realized sign like any other trade.

FEATURES (7, fixed, all causal at the signal bar ts):
  1 z_mag        |session-VWAP z| at ts
  2 atr_rel      |entry-stop|/entry * 1e4 (the causal 15m ATR that sized
                 the stop, in bps of price; STOP_ATR_MULT is 1.0)
  3 trend_align  direction * sign(15m close - EMA50) as of the latest
                 closed 15m bar (round223.htf_trend_lookup/attach_causal)
  4 mf_align     direction * sign(same-session cumulative money-flow
                 volume) at ts (round223.session_money_flow_sign)
  5 tod          minutes since 09:30 / 390
  6,7 dow_sin/cos sin/cos(2*pi*weekday/5)
Standardized with a scaler fit on TRAIN rows only.

MODEL. sklearn LogisticRegression(penalty="l1", solver="liblinear",
C=0.1), fixed a priori, never tuned. No trees, no ensembles.

DECISION RULE. Take a test trade iff predicted P(win) > the TRAIN base
win rate. Parameter-free.

VALIDATION.
  * Walk-forward: round11_fvg_bias.FOLDS[:5] (2024-01-01 .. 2026-07-01),
    expanding window: train on all trades before the fold start.
  * PURGE: a train trade is dropped if its latest possible exit
    (entry bar + 390 bars, the resolver's max hold) is at/after the fold
    start, so no train outcome window straddles the split.
  * MIN-TRADES FLOOR: a fold counts only if it has >= 30 taken AND >= 30
    skipped test trades. Rejected folds are listed with the reason, never
    silently dropped. Pooled stats use accepted folds only.
  * FINAL HOLDOUT: trades with ts >= 2026-07-01 (through the data end,
    2026-09-23). Model trained once on all purged pre-holdout trades with
    the identical frozen config, evaluated ONCE, after the walk-forward.
    No re-tuning after seeing it, pass or fail.

CANDIDATE RULE (all must hold; stated now, not after):
  (a) pooled OOS trade-level bootstrap P(mean taken > mean skipped) >= 0.95
  (b) pooled OOS day-cluster bootstrap (resample trading days) same >= 0.95
  (c) pooled OOS one-sided two-proportion z-test, taken win rate >
      skipped win rate, p < 0.05
  (d) taken mean P&L > skipped mean P&L in >= 4 folds (a fold rejected by
      the floor cannot count toward the 4)
  (e) holdout: taken mean P&L > skipped mean P&L AND > the holdout's
      unfiltered mean P&L
  (f) label-shuffle control: fraction of 200 shuffled-label pipeline runs
      with pooled lift (mean taken - mean skipped) >= the real lift is
      <= 0.05
Also reported for comparability with this ledger: idea_harness-style
bootstrap P(edge>0) of the taken set's mean P&L (IS = folds, OOS=holdout).
Not ledger-eligible (a filter test on an existing real signal); no
ledger row. Journal it either way.

NOT DONE / DISCLOSED: one symbol (MNQ), one data source
(MNQ_CONTINUOUS.txt, 2022-12-12 .. 2026-09-23, the campaign's own
full-history file), single seed/config, slot-freeing excluded (above).

POWER NOTES (from --dry-run, counts only; no label or P&L was printed or
looked at before this pre-registration): 3,411 base trades over
2022-12-12..2026-09-23, zero NaN features. Walk-forward test sizes
408/435/459/479/472 (train 958..2,740 after purging 2-7 straddling
trades per fold); holdout 193 trades (train 3,215). Every fold can clear
the 30-per-side floor unless the model takes/skips >93% of a fold. Features
hand-checked on 2 trades against raw bars (z, direction, cumulative
money-flow sign, 15m EMA trend sign all reproduced independently). With
~450 trades/fold and a per-trade P&L sd on the order of the $1,200 risk,
a fold-level taken-vs-skipped difference needs to be several hundred
dollars/trade to be individually detectable; pooled n~2,250 is the real
source of power, the holdout (193) is deliberately only a sanity gate.
An earlier, throwaway run of this script's data-loading path
(counts of raw signals, ~38.7k, ~40/day) informed the base-trade-set
design above; no outcome data was involved.
"""
import os, sys, json, datetime as dt, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from round11_fvg_bias import load_1m, FOLDS
from round19_random_entry import causal_atr15_lookup, TRAIL_ATR_MULT
from round49_vwap_zscore import compute_session_vwap_z, build_zscore_signals
from round204_multi_account_best_strategies import _resolve_trailing_sequential_per_signal_risk
from round223_manual_confluence_filters import (
    htf_trend_lookup, attach_causal, session_money_flow_sign, VWAPZ_RISK, Z_THRESH, EMA_SPAN,
)

HERE = os.path.dirname(os.path.abspath(__file__))
WF_FOLDS = FOLDS[:5]
HOLDOUT_START = pd.Timestamp("2026-07-01")
C_L1 = 0.1
MAX_HOLD_BARS = 390
MIN_PER_SIDE = 30
N_BOOT = 4000
N_SHUFFLE = 200
FEATURES = ["z_mag", "atr_rel", "trend_align", "mf_align", "tod", "dow_sin", "dow_cos"]


def build_trades(mnq_1m, atr15, mnq_z):
    """The leg's real sequential trades, each with its 7 causal features and
    its latest-possible-exit timestamp (for purging)."""
    sig = build_zscore_signals(mnq_z, atr15, Z_THRESH).copy()
    sig["risk"] = VWAPZ_RISK
    tr = _resolve_trailing_sequential_per_signal_risk(sig, mnq_1m, "MNQ", TRAIL_ATR_MULT)
    tr = tr.merge(sig[["ts", "entry", "stop"]], on="ts", how="left")

    z_at = mnq_z["z"].reindex(tr["ts"]).values
    feat = pd.DataFrame({"ts": tr["ts"].values})
    feat["z_mag"] = np.abs(z_at)
    feat["atr_rel"] = (tr["entry"] - tr["stop"]).abs().values / tr["entry"].values * 1e4

    trend = attach_causal(tr[["ts", "direction"]], htf_trend_lookup(mnq_1m, EMA_SPAN))
    feat = feat.merge(trend.assign(trend_align=trend["direction"] * trend["confluence"])[["ts", "trend_align"]],
                      on="ts", how="left")
    mf = session_money_flow_sign(mnq_1m).reindex(tr["ts"]).values
    feat["mf_align"] = tr["direction"].values * mf
    t = pd.DatetimeIndex(tr["ts"])
    feat["tod"] = ((t.hour * 60 + t.minute) - (9 * 60 + 30)) / 390.0
    dow = t.weekday.values
    feat["dow_sin"] = np.sin(2 * np.pi * dow / 5.0)
    feat["dow_cos"] = np.cos(2 * np.pi * dow / 5.0)

    idx = mnq_1m.index.values
    pos = np.searchsorted(idx, tr["ts"].values, side="right")
    end_pos = np.minimum(pos + MAX_HOLD_BARS, len(idx) - 1)
    out = pd.concat([tr[["ts", "direction", "contracts", "pnl"]].reset_index(drop=True),
                     feat.drop(columns="ts").reset_index(drop=True)], axis=1)
    out["latest_exit"] = pd.to_datetime(idx[end_pos])
    out["y"] = (out["pnl"] > 0).astype(int)
    return out


def fit_predict(train, test):
    """Purge already applied by caller. Returns (take_mask, p_test, base_rate)."""
    sc = StandardScaler().fit(train[FEATURES].values)
    clf = LogisticRegression(penalty="l1", solver="liblinear", C=C_L1, max_iter=1000)
    clf.fit(sc.transform(train[FEATURES].values), train["y"].values)
    p = clf.predict_proba(sc.transform(test[FEATURES].values))[:, 1]
    base = float(train["y"].mean())
    return p > base, p, base, clf.coef_.ravel()


def purged_train(trades, split_ts):
    return trades[(trades["ts"] < split_ts) & (trades["latest_exit"] < split_ts)]


def two_prop_z_greater(win_a, n_a, win_b, n_b):
    """One-sided: P(rate_a > rate_b), pooled two-proportion z-test."""
    if n_a == 0 or n_b == 0:
        return float("nan"), float("nan")
    pa, pb = win_a / n_a, win_b / n_b
    pp = (win_a + win_b) / (n_a + n_b)
    se = np.sqrt(pp * (1 - pp) * (1 / n_a + 1 / n_b))
    if se == 0:
        return float("nan"), float("nan")
    z = (pa - pb) / se
    return float(z), float(1 - stats.norm.cdf(z))


def boot_p_greater(a, b, n_boot=N_BOOT, seed=0):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 5 or len(b) < 5:
        return float("nan")
    rng = np.random.default_rng(seed)
    return float((rng.choice(a, (n_boot, len(a))).mean(1) > rng.choice(b, (n_boot, len(b))).mean(1)).mean())


def day_cluster_boot_p_greater(df, n_boot=N_BOOT, seed=0):
    """df has columns day, take, pnl. Resample whole days; P(mean taken > mean skipped)."""
    days = df["day"].unique()
    g = {d: (x.loc[x["take"], "pnl"].values, x.loc[~x["take"], "pnl"].values) for d, x in df.groupby("day")}
    rng = np.random.default_rng(seed)
    wins = 0
    valid = 0
    for _ in range(n_boot):
        pick = rng.choice(days, len(days))
        t = np.concatenate([g[d][0] for d in pick])
        s = np.concatenate([g[d][1] for d in pick])
        if len(t) == 0 or len(s) == 0:
            continue
        valid += 1
        wins += t.mean() > s.mean()
    return float(wins / valid) if valid else float("nan")


def run_walk_forward(trades, label_col="y"):
    """Returns (per_fold_rows, pooled DataFrame of accepted-fold test trades with take flag)."""
    rows, pooled = [], []
    for a, b in WF_FOLDS:
        a_ts, b_ts = pd.Timestamp(a), pd.Timestamp(b)
        train = purged_train(trades, a_ts)
        test = trades[(trades["ts"] >= a_ts) & (trades["ts"] < b_ts)]
        row = dict(fold=f"{a} -> {b}", n_train=len(train), n_test=len(test))
        if len(train) < 100 or len(test) == 0 or train[label_col].nunique() < 2:
            row.update(status="rejected: train too small or one-class")
            rows.append(row)
            continue
        take, p, base, coef = fit_predict(train.assign(y=train[label_col]), test)
        n_take, n_skip = int(take.sum()), int((~take).sum())
        row.update(n_taken=n_take, n_skipped=n_skip, base_rate=base, nonzero_coefs=int((coef != 0).sum()),
                   mean_taken=float(test.loc[take, "pnl"].mean()) if n_take else float("nan"),
                   mean_skipped=float(test.loc[~take, "pnl"].mean()) if n_skip else float("nan"),
                   mean_all=float(test["pnl"].mean()),
                   win_taken=float((test.loc[take, "pnl"] > 0).mean()) if n_take else float("nan"),
                   win_skipped=float((test.loc[~take, "pnl"] > 0).mean()) if n_skip else float("nan"))
        if n_take < MIN_PER_SIDE or n_skip < MIN_PER_SIDE:
            row["status"] = f"rejected: floor (taken={n_take}, skipped={n_skip}, need >= {MIN_PER_SIDE} each)"
            rows.append(row)
            continue
        row["status"] = "accepted"
        rows.append(row)
        pooled.append(test.assign(take=take, fold=row["fold"]))
    return rows, (pd.concat(pooled, ignore_index=True) if pooled else pd.DataFrame())


def pooled_lift(pool):
    if len(pool) == 0:
        return float("nan")
    t, s = pool.loc[pool["take"], "pnl"], pool.loc[~pool["take"], "pnl"]
    return float(t.mean() - s.mean()) if len(t) and len(s) else float("nan")


def label_shuffle_control(trades, real_lift, n_shuffle=N_SHUFFLE, seed=0):
    """Same pipeline, training labels shuffled within each fold's train set.
    Tests whether the pipeline can manufacture lift from noise labels."""
    rng = np.random.default_rng(seed)
    lifts = []
    for _ in range(n_shuffle):
        pooled = []
        for a, b in WF_FOLDS:
            a_ts, b_ts = pd.Timestamp(a), pd.Timestamp(b)
            train = purged_train(trades, a_ts)
            test = trades[(trades["ts"] >= a_ts) & (trades["ts"] < b_ts)]
            if len(train) < 100 or len(test) == 0:
                continue
            tr = train.copy()
            tr["y"] = rng.permutation(tr["y"].values)
            if tr["y"].nunique() < 2:
                continue
            take, _, _, _ = fit_predict(tr, test)
            if take.sum() < MIN_PER_SIDE or (~take).sum() < MIN_PER_SIDE:
                continue
            pooled.append(test.assign(take=take))
        if pooled:
            lifts.append(pooled_lift(pd.concat(pooled, ignore_index=True)))
    lifts = np.array([x for x in lifts if not np.isnan(x)])
    return lifts, float((lifts >= real_lift).mean()) if len(lifts) else float("nan")


def dry_run(trades):
    print(f"\nBase trade set: {len(trades)} sequential VWAP-Z trades "
          f"({trades['ts'].min()} .. {trades['ts'].max()})")
    print(f"Feature NaN counts: {trades[FEATURES].isna().sum().to_dict()}")
    print("\nPer walk-forward fold (counts only, no labels/P&L):")
    for a, b in WF_FOLDS:
        a_ts, b_ts = pd.Timestamp(a), pd.Timestamp(b)
        raw_train = trades[trades["ts"] < a_ts]
        train = purged_train(trades, a_ts)
        test = trades[(trades["ts"] >= a_ts) & (trades["ts"] < b_ts)]
        print(f"  {a} -> {b}: train={len(train)} (purged {len(raw_train) - len(train)}), test={len(test)}")
    ho = trades[trades["ts"] >= HOLDOUT_START]
    ho_train = purged_train(trades, HOLDOUT_START)
    print(f"  HOLDOUT >= {HOLDOUT_START.date()}: train={len(ho_train)} "
          f"(purged {len(trades[trades['ts'] < HOLDOUT_START]) - len(ho_train)}), test={len(ho)}")
    print("\nFirst 3 trades' features (for hand-checking against the bars):")
    print(trades[["ts", "direction"] + FEATURES + ["latest_exit"]].head(3).to_string())
    print("\nFeature ranges:")
    print(trades[FEATURES].describe().loc[["min", "max"]].to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    mnq_1m = load_1m(os.path.join(HERE, "..", "data", "MNQ_CONTINUOUS.txt"))
    atr15 = causal_atr15_lookup(mnq_1m)
    mnq_z = compute_session_vwap_z(mnq_1m)
    trades = build_trades(mnq_1m, atr15, mnq_z)
    trades = trades.dropna(subset=FEATURES).reset_index(drop=True)

    if args.dry_run:
        dry_run(trades)
        sys.exit(0)

    results = {}
    print(f"Base trades: {len(trades)}; overall win rate {trades['y'].mean():.3f}, "
          f"mean P&L ${trades['pnl'].mean():+.2f}\n")

    print("=== Walk-forward (purged, expanding) ===")
    rows, pool = run_walk_forward(trades)
    for r in rows:
        if r["status"] == "accepted":
            print(f"  {r['fold']}: train={r['n_train']} test={r['n_test']} taken={r['n_taken']} skipped={r['n_skipped']} "
                  f"| mean taken ${r['mean_taken']:+.2f} vs skipped ${r['mean_skipped']:+.2f} (all ${r['mean_all']:+.2f}) "
                  f"| win taken {r['win_taken']:.3f} vs skipped {r['win_skipped']:.3f} | nonzero coefs {r['nonzero_coefs']}")
        else:
            print(f"  {r['fold']}: {r['status']}  {{{', '.join(f'{k}={v}' for k, v in r.items() if k in ('n_train', 'n_test', 'n_taken', 'n_skipped'))}}}")
    results["folds"] = rows

    accepted = [r for r in rows if r["status"] == "accepted"]
    folds_lift_positive = sum(1 for r in accepted if r["mean_taken"] > r["mean_skipped"])
    if len(pool):
        t, s = pool.loc[pool["take"], "pnl"].values, pool.loc[~pool["take"], "pnl"].values
        lift = pooled_lift(pool)
        p_trade = boot_p_greater(t, s)
        p_day = day_cluster_boot_p_greater(pool.assign(day=pool["ts"].dt.date))
        zst, zp = two_prop_z_greater((t > 0).sum(), len(t), (s > 0).sum(), len(s))
        print(f"\nPooled OOS: taken n={len(t)} mean ${t.mean():+.2f} win {np.mean(t > 0):.3f} | "
              f"skipped n={len(s)} mean ${s.mean():+.2f} win {np.mean(s > 0):.3f} | lift ${lift:+.2f}/trade")
        print(f"  (a) trade-level bootstrap P(taken > skipped) = {p_trade:.4f}")
        print(f"  (b) day-cluster bootstrap P(taken > skipped) = {p_day:.4f}")
        print(f"  (c) two-account z = {zst:.3f}, one-sided p = {zp:.4f}")
        print(f"  (d) folds with taken > skipped: {folds_lift_positive} of {len(accepted)} accepted")
        rng = np.random.default_rng(1)
        p_edge = float((rng.choice(t, (N_BOOT, len(t))).mean(1) > 0).mean())
        print(f"  ledger-style: bootstrap P(mean taken P&L > 0) = {p_edge:.4f}")
        lifts, frac = label_shuffle_control(trades, lift)
        print(f"  (f) label-shuffle control ({len(lifts)} runs): shuffled lift mean ${lifts.mean():+.2f} "
              f"sd ${lifts.std():.2f}; fraction >= real lift = {frac:.3f}")
        results["pooled"] = dict(n_taken=len(t), n_skipped=len(s), mean_taken=float(t.mean()), mean_skipped=float(s.mean()),
                                 lift=lift, p_trade_boot=p_trade, p_day_boot=p_day, z=zst, z_p=zp,
                                 folds_positive=folds_lift_positive, n_accepted=len(accepted), p_edge_taken=p_edge,
                                 shuffle_frac_ge_real=frac, shuffle_lift_mean=float(lifts.mean()),
                                 shuffle_lift_sd=float(lifts.std()))
    else:
        print("\nNo accepted folds -- nothing to pool.")
        results["pooled"] = None

    print("\n=== FINAL HOLDOUT (touched once) ===")
    ho = trades[trades["ts"] >= HOLDOUT_START]
    ho_train = purged_train(trades, HOLDOUT_START)
    take, p, base, coef = fit_predict(ho_train, ho)
    n_take, n_skip = int(take.sum()), int((~take).sum())
    ho_mean_all = float(ho["pnl"].mean())
    ho_mean_t = float(ho.loc[take, "pnl"].mean()) if n_take else float("nan")
    ho_mean_s = float(ho.loc[~take, "pnl"].mean()) if n_skip else float("nan")
    print(f"  train={len(ho_train)} test={len(ho)} taken={n_take} skipped={n_skip} base_rate={base:.3f} "
          f"nonzero coefs={int((coef != 0).sum())}")
    print(f"  mean taken ${ho_mean_t:+.2f} | skipped ${ho_mean_s:+.2f} | all ${ho_mean_all:+.2f}")
    results["holdout"] = dict(n_train=len(ho_train), n_test=len(ho), n_taken=n_take, n_skipped=n_skip,
                              mean_taken=ho_mean_t, mean_skipped=ho_mean_s, mean_all=ho_mean_all,
                              coefs=dict(zip(FEATURES, [float(c) for c in coef])))
    print(f"  coefficients (standardized): { {k: round(float(c), 3) for k, c in zip(FEATURES, coef)} }")

    if results.get("pooled"):
        pl = results["pooled"]
        checks = {
            "a_trade_boot>=0.95": pl["p_trade_boot"] >= 0.95,
            "b_day_boot>=0.95": pl["p_day_boot"] >= 0.95,
            "c_z_p<0.05": pl["z_p"] < 0.05,
            "d_folds_positive>=4": pl["folds_positive"] >= 4,
            "e_holdout": (ho_mean_t > ho_mean_s) and (ho_mean_t > ho_mean_all),
            "f_shuffle<=0.05": pl["shuffle_frac_ge_real"] <= 0.05,
        }
    else:
        checks = {"no_accepted_folds": False}
    results["candidate_checks"] = checks
    print("\n=== Candidate rule (pre-registered) ===")
    for k, v in checks.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"  VERDICT: {'CANDIDATE' if all(checks.values()) else 'NOT a candidate'}")

    with open(os.path.join(HERE, "round228_results.json"), "w") as f:
        json.dump(results, f, indent=1, default=str)
    print("\nSaved round228_results.json")
