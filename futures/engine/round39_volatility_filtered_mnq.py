"""
Round 39: Does filtering MNQ's random-entry+ATR-trail edge by WHEN (volatility regime
or time-of-day), rather than WHICH DIRECTION, concentrate the edge?

Background (read futures/docs/EDGE_VALIDATION_RESULTS.md Rounds 19-26 and
20 first): Round 19 found the MNQ edge lives entirely in the exit (ATR-based trailing
stop, cut losses fast / let winners run), with entry timing/direction pure noise by
construction. Round 20 tested "smart" (price-informed, directional) entries against
the same exit and found they made things WORSE, not better -- so this round does NOT
touch direction or use price to pick which bar to enter. It only asks: if the random
daily entry is SKIPPED on days that fail a regime/time filter (still a coin-flip
direction, still a uniformly random bar WITHIN the allowed window), does restricting
WHEN the draw is allowed to fire improve OOS expectancy or shrink drawdown enough to
raise the buffer-safe size, versus just taking every day's draw unfiltered?

Two filter families, both distinct from the 15m ATR(14) already used for stop sizing
(a different lookback, per the standing instruction not to reuse that same signal):
  - Volatility regime: `round14_meanreversion.daily_vol_regime` -- a **daily-close**
    20-day realized-vol percentile rank against a trailing 200-day history (causal:
    day D's value only uses days < D). Reused unchanged, not reimplemented.
  - Time-of-day: which third/half of the RTH session (09:30-16:00 ET) the random bar
    landed in, from the entry bar's own clock time (no lookahead question -- the time
    of an already-chosen entry bar is trivially known at that bar).

Methodology (non-negotiable per the task): reuse `round19_random_entry`'s actual
`generate_random_entries`, `build_stop_signals`, `resolve_trailing`, and
`causal_atr15_lookup` UNCHANGED -- this script only adds a filter step between
`build_stop_signals` and `resolve_trailing`, it does not reimplement entry generation,
stop sizing, or exit management. Walk-forward uses the SAME `FOLDS` constant
(round11_fvg_bias, expanding-window, 6 OOS windows, 2024-01 -> 2026-09) as every other
round in this campaign. Per (fold, seed): every filter candidate (including "none", the
unfiltered baseline) is scored ONLY on that fold's TRAIN-window trades (expectancy at a
single reference risk, $600, via resolve_trailing); the highest-train-expectancy
candidate is then applied UNCHANGED to that fold's OOS test window -- the threshold
itself is never touched by test data. Same costs ($1.24/contract commission, 2-tick
slippage -- both inherited from resolve_trailing/POINT_VALUE/TICK_SIZE, not
reimplemented), same 8 independent seeds as Round 19, same real $4,937.50 buffer
(`BUFFER`, round11_fvg_bias) for the drawdown check.

Reported: pooled OOS expectancy/trade, trade count, one-sample t-stat (mean pnl != 0)
and per-(seed,fold) max drawdown at a risk sweep, for the filtered approach AND the
unfiltered baseline side by side -- so "does filtering help at all" is a direct,
apples-to-apples comparison, not just a filtered-only number.
"""
import sys
import os
import datetime as dt

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(__file__))
from round11_fvg_bias import load_1m, POINT_VALUE, TICK_SIZE, COMMISSION_RT, BUFFER, FOLDS, fold_stats
from round14_meanreversion import daily_vol_regime, attach_vol_regime
from round19_random_entry import (
    causal_atr15_lookup, generate_random_entries, build_stop_signals, resolve_trailing,
    SEEDS, TRAIL_ATR_MULT,
)

SYMBOL = "MNQ"
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "MNQ_CONTINUOUS.txt")

# Reference risk used ONLY to rank filter candidates on train data (single level, same
# convention as Round 14's "quick screen" -- avoids a per-risk-level x per-candidate
# combinatorial explosion; the risk actually deployed is swept separately below, after
# candidate selection, on the resulting OOS trades).
SELECT_REF_RISK = 600

# Buffer-safe sizing sweep, run on the OOS trades AFTER filter selection (selection
# itself never sees a risk-level's OOS drawdown -- only its own train expectancy).
RISK_SWEEP = [25, 50, 75, 100, 125, 150, 200, 250, 300, 400, 500, 600, 700, 800, 1000]

MIN_TRAIN = 30            # minimum unfiltered train-fold trades to attempt any selection
MIN_TRAIN_FILTERED = 15   # minimum trades a candidate needs in-fold to be eligible at all

# Volatility-regime bands (percentile rank 0..1, from daily_vol_regime -- causal daily
# realized vol, a different signal AND a different lookback than the 15m ATR(14) used
# for stop distance).
VOL_BANDS = {
    "vol_top50":    (0.50, 1.01),
    "vol_bottom50": (-0.01, 0.50),
    "vol_top33":    (0.667, 1.01),
    "vol_bottom33": (-0.01, 0.333),
    "vol_mid33":    (0.333, 0.667),
}

# Time-of-day bands, plain clock time on the entry bar itself (RTH 09:30-16:00 ET,
# confirmed from the raw data). Thirds are split by elapsed minutes (390 min session),
# not by round clock numbers, so each band covers a comparable slice of the session.
_OPEN = dt.time(9, 30)
_T1 = dt.time(11, 40)
_T2 = dt.time(13, 50)
_CLOSE = dt.time(16, 0)
_MID = dt.time(12, 45)
TOD_BANDS = {
    "tod_first_third": (_OPEN, _T1),
    "tod_mid_third":   (_T1, _T2),
    "tod_last_third":  (_T2, _CLOSE),
    "tod_first_half":  (_OPEN, _MID),
    "tod_second_half": (_MID, _CLOSE),
}

CANDIDATES = ["none"] + list(VOL_BANDS) + list(TOD_BANDS)


def apply_candidate(sig, candidate):
    """sig must already have a 'vol_pct' column (attach_vol_regime) and a 'ts' column.
    Direction and bar choice are NEVER touched here -- this only drops rows (whole
    random draws) that fail the WHEN filter; every surviving row keeps its original
    random direction/time/entry/stop untouched, per the task's standing instruction
    not to reintroduce a directional/price-informed entry (Round 20 already showed
    that makes it worse)."""
    if candidate == "none":
        return sig
    if candidate in VOL_BANDS:
        lo, hi = VOL_BANDS[candidate]
        return sig[(sig["vol_pct"] >= lo) & (sig["vol_pct"] < hi)]
    if candidate in TOD_BANDS:
        lo, hi = TOD_BANDS[candidate]
        t = sig["ts"].dt.time
        return sig[(t >= lo) & (t < hi)]
    raise ValueError(candidate)


def select_candidate(train_sig, df1m):
    """Rank every candidate by TRAIN-only expectancy (resolve_trailing, reused
    unchanged) at SELECT_REF_RISK. Returns (best_candidate, per_candidate_train_exp)."""
    scores = {}
    for cand in CANDIDATES:
        tf = apply_candidate(train_sig, cand)
        if len(tf) < MIN_TRAIN_FILTERED:
            continue
        tr = resolve_trailing(tf, df1m, SYMBOL, SELECT_REF_RISK, TRAIL_ATR_MULT)
        if len(tr) == 0:
            continue
        scores[cand] = (tr["pnl"].mean(), len(tr))
    if not scores:
        return "none", scores
    best = max(scores.items(), key=lambda kv: kv[1][0])[0]
    return best, scores


def pooled_stats(trades_by_seed_fold, risk):
    """trades_by_seed_fold: list of (seed, train_end, test_end, trades_df) at this
    risk. Pools every trade across seeds/folds for expectancy/t-stat, and separately
    tracks the worst single (seed, fold) max drawdown -- the buffer check this repo
    applies everywhere (fold_stats/BUFFER from round11_fvg_bias), not a continuous
    across-fold equity curve."""
    all_trades = [t for (_, _, _, t) in trades_by_seed_fold if t is not None and len(t) > 0]
    if not all_trades:
        return None
    pooled = pd.concat(all_trades, ignore_index=True)
    n = len(pooled)
    mean_pnl = pooled["pnl"].mean()
    std_pnl = pooled["pnl"].std(ddof=1)
    if n > 1 and std_pnl > 0:
        t_stat, p_val = stats.ttest_1samp(pooled["pnl"].values, popmean=0.0)
    else:
        t_stat, p_val = float("nan"), float("nan")

    worst_dd = 0.0
    worst_fold = None
    n_breach = 0
    n_windows = 0
    for seed, train_end, test_end, t in trades_by_seed_fold:
        if t is None or len(t) == 0:
            continue
        n_windows += 1
        st = fold_stats(t)
        if st["breach"]:
            n_breach += 1
        if st["maxdd"] > worst_dd:
            worst_dd = st["maxdd"]
            worst_fold = (seed, train_end, test_end)

    return dict(
        n=n, expectancy=mean_pnl, total=pooled["pnl"].sum(), std=std_pnl,
        t_stat=t_stat, p_val=p_val, worst_dd=worst_dd, worst_fold=worst_fold,
        n_breach=n_breach, n_windows=n_windows,
    )


def run():
    print(f"Loading {SYMBOL} from {DATA_PATH} ...", flush=True)
    df1m = load_1m(DATA_PATH)
    print(f"{SYMBOL}: {len(df1m)} 1m bars, {df1m.index.min()} -> {df1m.index.max()}", flush=True)

    atr15 = causal_atr15_lookup(df1m)
    vol_pct = daily_vol_regime(df1m)
    print(f"{SYMBOL}: causal 15m ATR(14) ({len(atr15)} values), daily vol-regime "
          f"pct-rank ({len(vol_pct)} days, {vol_pct.index.min()} -> {vol_pct.index.max()})",
          flush=True)

    # candidate -> risk -> list of (seed, train_end, test_end, trades_df)
    filtered_by_risk = {risk: [] for risk in RISK_SWEEP}
    baseline_by_risk = {risk: [] for risk in RISK_SWEEP}
    fold_selection_log = []  # (seed, train_end, test_end, chosen, train_scores)
    chosen_counts = {}

    for seed in SEEDS:
        raw = generate_random_entries(df1m, seed)
        sig = build_stop_signals(raw, atr15)
        sig = attach_vol_regime(sig, vol_pct)
        sig = sig[sig["vol_pct"].notna()].reset_index(drop=True)

        for train_end, test_end in FOLDS:
            train_sig = sig[sig["ts"] < train_end]
            test_sig = sig[(sig["ts"] >= train_end) & (sig["ts"] < test_end)]
            if len(train_sig) < MIN_TRAIN or len(test_sig) == 0:
                continue

            best_cand, scores = select_candidate(train_sig, df1m)
            chosen_counts[best_cand] = chosen_counts.get(best_cand, 0) + 1
            fold_selection_log.append((seed, train_end, test_end, best_cand, scores))

            test_filtered = apply_candidate(test_sig, best_cand)
            for risk in RISK_SWEEP:
                tf_trades = (resolve_trailing(test_filtered, df1m, SYMBOL, risk, TRAIL_ATR_MULT)
                             if len(test_filtered) > 0 else None)
                filtered_by_risk[risk].append((seed, train_end, test_end, tf_trades))
                tb_trades = resolve_trailing(test_sig, df1m, SYMBOL, risk, TRAIL_ATR_MULT)
                baseline_by_risk[risk].append((seed, train_end, test_end, tb_trades))

        print(f"  seed={seed}: done ({len(fold_selection_log)} total fold-selections so far)", flush=True)

    print(f"\n{'='*78}\nFold-by-fold filter selection (train-only, {SELECT_REF_RISK=}):\n{'='*78}", flush=True)
    for seed, train_end, test_end, chosen, scores in fold_selection_log:
        score_str = ", ".join(f"{k}=${v[0]:.0f}(n={v[1]})" for k, v in sorted(scores.items(), key=lambda kv: -kv[1][0])[:4])
        print(f"  seed={seed} fold={train_end}->{test_end}: chosen={chosen} | top train candidates: {score_str}", flush=True)

    print(f"\nSelection frequency across all {len(fold_selection_log)} (seed, fold) windows:", flush=True)
    for cand, cnt in sorted(chosen_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {cand}: {cnt} ({100*cnt/len(fold_selection_log):.1f}%)", flush=True)

    print(f"\n{'='*78}\nOOS RESULTS: filtered (train-selected candidate) vs. unfiltered baseline\n{'='*78}", flush=True)
    print(f"{'risk':>6} | {'FILTERED n':>10} {'exp':>9} {'t-stat':>7} {'p':>9} {'worst_dd':>10} {'breach':>10} "
          f"|| {'BASE n':>7} {'exp':>9} {'t-stat':>7} {'p':>9} {'worst_dd':>10} {'breach':>10}", flush=True)
    summary = {}
    for risk in RISK_SWEEP:
        f_stats = pooled_stats(filtered_by_risk[risk], risk)
        b_stats = pooled_stats(baseline_by_risk[risk], risk)
        summary[risk] = (f_stats, b_stats)

        def fmt(s):
            if s is None:
                return f"{'--':>7} {'--':>9} {'--':>7} {'--':>9} {'--':>10} {'--':>10}"
            return (f"{s['n']:>7} ${s['expectancy']:>7.2f} {s['t_stat']:>7.2f} {s['p_val']:>9.2e} "
                    f"${s['worst_dd']:>8.2f} {s['n_breach']:>3}/{s['n_windows']:<6}")

        print(f"{risk:>6} | {fmt(f_stats)} || {fmt(b_stats)}", flush=True)

    # Buffer-safe risk: the largest RISK_SWEEP level with worst_dd < BUFFER across ALL
    # (seed, fold) OOS windows -- same "worst single fold/seed" convention used
    # throughout this campaign (Round 9, Round 31 etc.), not an average.
    def buffer_safe(summary, key):
        safe = 0
        for risk in RISK_SWEEP:
            s = summary[risk][key]
            if s is not None and s["worst_dd"] < BUFFER and s["n_breach"] == 0:
                safe = risk
        return safe

    filtered_safe = buffer_safe(summary, 0)
    baseline_safe = buffer_safe(summary, 1)
    print(f"\nBuffer-safe size (worst OOS seed/fold maxdd < ${BUFFER:.2f}, zero breaches):", flush=True)
    print(f"  filtered:  ${filtered_safe}", flush=True)
    print(f"  baseline:  ${baseline_safe}", flush=True)

    # Robustness check: the pooled t-stats above treat every trade across all 8 seeds
    # as an independent observation, but all 8 seeds share the SAME underlying price
    # history (only the entry bar/direction draw differs) -- a much more conservative
    # read collapses each seed to ONE mean-expectancy observation (n=8) and tests that
    # distribution instead, the same unit Round 19 itself reports significance over
    # (`summarize_across_seeds`).
    def per_seed_means(trades_by_seed_fold, risk):
        by_seed = {}
        for seed, _te, _ts, t in trades_by_seed_fold[risk]:
            if t is None or len(t) == 0:
                continue
            by_seed.setdefault(seed, []).append(t)
        means = []
        for seed, frames in sorted(by_seed.items()):
            pooled = pd.concat(frames, ignore_index=True)
            means.append(pooled["pnl"].mean())
        return means

    print(f"\n{'='*78}\nPer-seed robustness check (n=8 seed-level means, not pooled trades) "
          f"at each buffer-safe size:\n{'='*78}", flush=True)
    for label, risk, source in [("filtered", filtered_safe, filtered_by_risk),
                                 ("baseline", baseline_safe, baseline_by_risk)]:
        if risk == 0:
            print(f"  {label}: no buffer-safe size found in RISK_SWEEP", flush=True)
            continue
        means = per_seed_means(source, risk)
        means_arr = np.array(means)
        if len(means_arr) > 1:
            t_seed, p_seed = stats.ttest_1samp(means_arr, popmean=0.0)
        else:
            t_seed, p_seed = float("nan"), float("nan")
        print(f"  {label} @ ${risk}: per-seed expectancies = {[round(m,2) for m in means]}", flush=True)
        print(f"    n_seeds={len(means_arr)} mean=${means_arr.mean():.2f} std=${means_arr.std(ddof=1):.2f} "
              f"all_positive={bool((means_arr>0).all())} t_stat(n=8)={t_seed:.2f} p(n=8)={p_seed:.4f}", flush=True)

    return dict(summary=summary, filtered_safe=filtered_safe, baseline_safe=baseline_safe,
                chosen_counts=chosen_counts, fold_selection_log=fold_selection_log)


if __name__ == "__main__":
    result = run()
    print("\nDONE.", flush=True)
