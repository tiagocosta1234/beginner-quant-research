"""
Round 224 (the trader, 2026-09-30): "dig into it and focus on getting
trustworthy numbers" -- the rigorous follow-up to Round 223's headline
finding (HTF-trend confluence filter on the trader's TOD leg only: daily profit
factor 1.595 -> 1.653, mean/day $728 -> $777, holding IS and OOS).

Same discipline as Round 218 -> 219 (idealized result -> real, verified
follow-up): Round 223's number came from ONE arbitrary EMA-span choice
(50) and ONE binary IS/OOS split, on the full COMBINED sequential-
resolver trade sequence (TOD+VWAP-Z interleaved, one position at a time)
-- which means removing a TOD signal can also free a slot for a VWAP-Z
trade that wouldn't otherwise have fired, a real confound when trying to
isolate whether the TREND FILTER ITSELF discriminates good TOD setups
from bad ones. This round isolates that question cleanly and stresses it
three ways before trusting it:

  1. TOD leg in ISOLATION (round19's own standalone resolve_trailing,
     TOD signals only, no VWAP-Z interleaving at all) -- split into
     "trend-aligned" vs "trend-against" buckets by the same causal HTF-
     EMA rule, bootstrap the difference in mean per-trade P&L directly.
     This is the real question Round 223's aggregate PF number implied
     but never directly tested: do trend-aligned TOD trades actually
     have higher REAL expectancy than trend-against ones, with the
     cross-leg confound removed.
  2. EMA-SPAN ROBUSTNESS: Round 223 used span=50 without a grid search
     (deliberately, to avoid a selection bias) but also without checking
     whether the result is fragile to that one choice. Repeats bucket 1
     at spans {20, 50, 100, 150, 200} -- a small, fixed, non-cherry-
     picked grid -- and reports whether the direction and rough
     magnitude of the aligned-vs-against gap holds across all of them.
  3. FOLD-BY-FOLD CONSISTENCY: same aligned-vs-against split, restricted
     to each of round11_fvg_bias's own 6 expanding-window test periods
     (2024-01 through 2026-09, the walk-forward convention round19/round49
     themselves already use) plus the pre-2024 history as a 7th bucket --
     does trend-alignment discriminate in MOST/ALL periods, or only in
     one lucky stretch that dominates the full-history average.

Also re-verifies Round 223's own headline combined-the trader number (PF_daily,
mean/day) at every span in the same grid, so the $777/day figure isn't
trusted at a single arbitrary span either.

Nothing modified: round19/round49/round204/round223 are all imported,
never edited. This stays a research-only script.
"""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd

from round11_fvg_bias import load_1m, resample_causal, FOLDS
from round19_random_entry import generate_random_entries, build_stop_signals, causal_atr15_lookup, \
    resolve_trailing, TRAIL_ATR_MULT
from round49_vwap_zscore import compute_session_vwap_z, build_zscore_signals
from round204_multi_account_best_strategies import _resolve_trailing_sequential_per_signal_risk
from round223_manual_confluence_filters import (
    build_base_signals, session_money_flow_sign, filter_money_flow, daily_profit_factor,
    trade_profit_factor, TOD_RISK, VWAPZ_RISK,
)
import round120_goal_judge as J

HERE = os.path.dirname(os.path.abspath(__file__))
SPAN_GRID = [20, 50, 100, 150, 200]
N_BOOT = 4000


def htf_trend_lookup(mnq_1m, ema_span):
    h15 = resample_causal(mnq_1m, "15min")
    ema = h15["close"].ewm(span=ema_span, adjust=False).mean()
    return np.sign(h15["close"] - ema)


def attach_causal(sig, series):
    idx = series.index.values
    pos = np.searchsorted(idx, sig["ts"].values, side="right") - 1
    valid = pos >= 0
    out = sig[valid].copy()
    out["confluence"] = series.values[pos[valid]]
    return out.reset_index(drop=True)


def bootstrap_p_greater(a, b, n_boot=N_BOOT, seed=0):
    """P(bootstrap mean of a > bootstrap mean of b), independent resampling."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 5 or len(b) < 5:
        return float("nan")
    rng = np.random.default_rng(seed)
    boot_a = rng.choice(a, size=(n_boot, len(a)), replace=True).mean(axis=1)
    boot_b = rng.choice(b, size=(n_boot, len(b)), replace=True).mean(axis=1)
    return float((boot_a > boot_b).mean())


def split_aligned_against(sig_tod, trend_series):
    out = attach_causal(sig_tod, trend_series)
    aligned = out[(out["confluence"] != 0) & (out["direction"] == out["confluence"])]
    against = out[(out["confluence"] != 0) & (out["direction"] == -out["confluence"])]
    neutral = out[out["confluence"] == 0]
    return aligned.drop(columns="confluence"), against.drop(columns="confluence"), neutral


def bucket_stats(label, trades, mnq_1m):
    if len(trades) == 0:
        return dict(label=label, n=0, mean=float("nan"), pf=float("nan"))
    tr = resolve_trailing(trades[["ts", "direction", "entry", "stop"]], mnq_1m, "MNQ", TOD_RISK, TRAIL_ATR_MULT)
    pf = trade_profit_factor(tr) if len(tr) else float("nan")
    return dict(label=label, n=len(tr), mean=float(tr["pnl"].mean()) if len(tr) else float("nan"), pf=pf,
                pnl=tr["pnl"].to_numpy(float) if len(tr) else np.array([]))


def random_ablation_control(sig_tod, sig_z, mnq_1m, all_days, n_removed, n_trials=20, seed=0):
    """The real control this round is built to run: does removing ANY
    n_removed TOD signals (a uniform-random subset, matched only in COUNT
    to what the trend filter removes) reproduce a similar combined-the trader
    improvement? If yes, the trend filter isn't doing anything the count
    reduction alone wouldn't -- if no, whichever specific signals it
    removes matters, which rules out simple slot-freeing as the whole
    story (though it does not, by itself, prove the removed signals are
    individually worse -- see the isolated bucket test above, which is
    the direct test of that claim)."""
    rng = np.random.default_rng(seed)
    pf_list, mean_list = [], []
    for _ in range(n_trials):
        keep_idx = np.sort(rng.choice(len(sig_tod), size=len(sig_tod) - n_removed, replace=False))
        sig_tod_rand = sig_tod.iloc[keep_idx].assign(risk=TOD_RISK, leg="TOD").reset_index(drop=True)
        combined = pd.concat([sig_tod_rand, sig_z], ignore_index=True).sort_values("ts").reset_index(drop=True)
        trades = _resolve_trailing_sequential_per_signal_risk(combined, mnq_1m, "MNQ", TRAIL_ATR_MULT)
        d = daily_profit_factor(trades, all_days)
        pf_list.append(d["profit_factor_daily"])
        mean_list.append(d["mean_per_day"])
    return np.array(pf_list), np.array(mean_list)


if __name__ == "__main__":
    mnq_1m = load_1m(os.path.join(HERE, "..", "data", "MNQ_CONTINUOUS.txt"))
    atr15 = causal_atr15_lookup(mnq_1m)
    mnq_z = compute_session_vwap_z(mnq_1m)
    sig_tod, sig_z = build_base_signals(mnq_1m, atr15, mnq_z)
    all_days = sorted(set(mnq_1m.index.normalize().date))
    oos_start_date = J.OOS_START.date()

    results = {"span_grid": [], "fold_check": [], "combined_reverify": []}

    print("=== 1+2. TOD leg in isolation, trend-aligned vs trend-against, EMA-span grid ===\n")
    for span in SPAN_GRID:
        trend = htf_trend_lookup(mnq_1m, span)
        aligned, against, neutral = split_aligned_against(sig_tod, trend)
        st_a = bucket_stats("aligned", aligned, mnq_1m)
        st_g = bucket_stats("against", against, mnq_1m)
        p_gt = bootstrap_p_greater(st_a["pnl"], st_g["pnl"])
        print(f"  span={span:>3}: aligned n={st_a['n']:>4} mean=${st_a['mean']:+7.2f} PF={st_a['pf']:.3f}  |  "
              f"against n={st_g['n']:>4} mean=${st_g['mean']:+7.2f} PF={st_g['pf']:.3f}  |  "
              f"neutral(undefined)={len(neutral)}  |  P(aligned mean > against mean)={p_gt:.4f}", flush=True)
        results["span_grid"].append(dict(span=span, aligned_n=st_a["n"], aligned_mean=st_a["mean"],
                                          aligned_pf=st_a["pf"], against_n=st_g["n"], against_mean=st_g["mean"],
                                          against_pf=st_g["pf"], p_aligned_gt_against=p_gt))

    print("\n=== 3. Fold-by-fold consistency, span=50 (Round 223's own choice) ===\n")
    span50_trend = htf_trend_lookup(mnq_1m, 50)
    aligned50, against50, _ = split_aligned_against(sig_tod, span50_trend)
    periods = [("pre-2024 (2022-12 -> 2024-01)", None, "2024-01-01")] + \
              [(f"{a} -> {b}", a, b) for a, b in FOLDS]
    for label, start, end in periods:
        a_win = aligned50[(start is None or aligned50["ts"] >= start) & (aligned50["ts"] < end)]
        g_win = against50[(start is None or against50["ts"] >= start) & (against50["ts"] < end)]
        st_a = bucket_stats("aligned", a_win, mnq_1m)
        st_g = bucket_stats("against", g_win, mnq_1m)
        p_gt = bootstrap_p_greater(st_a["pnl"], st_g["pnl"]) if st_a["n"] >= 5 and st_g["n"] >= 5 else float("nan")
        print(f"  {label:<32}: aligned n={st_a['n']:>4} mean=${st_a['mean']:+7.2f}  |  "
              f"against n={st_g['n']:>4} mean=${st_g['mean']:+7.2f}  |  "
              f"aligned better? {'yes' if st_a['mean'] > st_g['mean'] else 'no' if st_g['n'] and st_a['n'] else 'n/a'}"
              f"  P={p_gt:.3f}" if not np.isnan(p_gt) else
              f"  {label:<32}: aligned n={st_a['n']:>4} mean=${st_a['mean']:+7.2f}  |  "
              f"against n={st_g['n']:>4} mean=${st_g['mean']:+7.2f}  |  too few trades for a bootstrap read",
              flush=True)
        results["fold_check"].append(dict(label=label, aligned_n=st_a["n"], aligned_mean=st_a["mean"],
                                           against_n=st_g["n"], against_mean=st_g["mean"], p_aligned_gt_against=p_gt))

    print("\n=== Re-verify Round 223's headline combined-the trader number across the same span grid ===\n")
    for span in SPAN_GRID:
        trend = htf_trend_lookup(mnq_1m, span)
        aligned, _, _ = split_aligned_against(sig_tod, trend)
        tod_filtered = aligned.copy()
        tod_filtered["risk"] = TOD_RISK
        tod_filtered["leg"] = "TOD"
        combined = pd.concat([tod_filtered, sig_z], ignore_index=True).sort_values("ts").reset_index(drop=True)
        trades = _resolve_trailing_sequential_per_signal_risk(combined, mnq_1m, "MNQ", TRAIL_ATR_MULT)
        d_full = daily_profit_factor(trades, all_days)
        print(f"  span={span:>3}: n_trades={len(trades):>5} PF_daily={d_full['profit_factor_daily']:.3f} "
              f"mean/day=${d_full['mean_per_day']:+7.2f}  (baseline: PF_daily=1.595, mean/day=$727.96)", flush=True)
        results["combined_reverify"].append(dict(span=span, n_trades=len(trades),
                                                   pf_daily=d_full["profit_factor_daily"],
                                                   mean_per_day=d_full["mean_per_day"]))

    print("\n=== The real control: does removing a RANDOM subset of the SAME COUNT reproduce this? (span=50) ===\n")
    trend50 = htf_trend_lookup(mnq_1m, 50)
    _, against50_full, _ = split_aligned_against(sig_tod, trend50)
    n_removed = len(against50_full)
    pf_rand, mean_rand = random_ablation_control(sig_tod, sig_z, mnq_1m, all_days, n_removed, n_trials=20)
    span50_result = next(r for r in results["combined_reverify"] if r["span"] == 50)
    print(f"  removing {n_removed} random TOD signals, 20 trials:")
    print(f"    PF_daily:  mean={pf_rand.mean():.3f} std={pf_rand.std():.3f} range=[{pf_rand.min():.3f}, {pf_rand.max():.3f}]")
    print(f"    mean/day:  mean=${mean_rand.mean():+.2f} std=${mean_rand.std():.2f} "
          f"range=[${mean_rand.min():+.2f}, ${mean_rand.max():+.2f}]")
    print(f"  trend filter (span=50) got: PF_daily={span50_result['pf_daily']:.3f} "
          f"mean/day=${span50_result['mean_per_day']:+.2f}")
    print(f"  fraction of random trials reaching the trend filter's PF: {(pf_rand >= span50_result['pf_daily']).mean():.2f}")
    print(f"  fraction of random trials reaching the trend filter's mean/day: "
          f"{(mean_rand >= span50_result['mean_per_day']).mean():.2f}", flush=True)
    results["random_ablation_control"] = dict(n_removed=n_removed, n_trials=20,
                                                pf_mean=float(pf_rand.mean()), pf_std=float(pf_rand.std()),
                                                mean_per_day_mean=float(mean_rand.mean()),
                                                mean_per_day_std=float(mean_rand.std()),
                                                trend_filter_pf=span50_result["pf_daily"],
                                                trend_filter_mean_per_day=span50_result["mean_per_day"])

    with open(os.path.join(HERE, "round224_results.json"), "w") as f:
        json.dump(results, f, indent=1, default=str)
    print("\nSaved round224_results.json", flush=True)
