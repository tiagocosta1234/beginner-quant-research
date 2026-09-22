"""
Round 56: confidence-weighted position sizing for MGC's swing S/R bounce edge.

Direct follow-up to the trader's suggestion: instead of one flat risk/trade, keep a
modest baseline ($300-400) and size UP (toward $2000) on touches that look
like higher-quality setups, rather than treating every touch identically.

Two touch-quality features are tested, both exactly knowable at the touch bar
itself (no lookahead -- added to build_swing_touch_signals in
round30_support_resistance.py on 2026-09-21 specifically for this round):
  - touch_lag_bars: how many bars elapsed between a level becoming eligible
    and price actually testing it (freshness).
  - pierce_frac: (level - price)/atr signed so positive = a shallow approach
    that barely got within tolerance, ~0 = an exact touch, negative = price
    pierced clean through the level (a deeper, more decisive test).

Same walk-forward discipline as the rest of this campaign: TRAIN-only
selection of which (lag, pierce) tercile cell counts as "high confidence" per
fold, applied unchanged OOS, with an explicit cross-fold consistency check --
the same test that killed round44's day-of-week candidate (unstable pick per
seed) and confirmed round39's time-of-day filter (70.8%-consistent pick).
One degree of freedom is selected from train data (which single cell of a
3x3 grid is best), not nine independent choices.

Two separate OOS comparisons are reported, deliberately not conflated:
  1. Fixed-risk expectancy, high-confidence cell vs. the rest, both resolved
     at the SAME risk_dollar -- isolates whether the confidence signal
     predicts real per-trade edge at all, independent of sizing.
  2. The actual variable-sizing portfolio (BASE_RISK on ordinary touches,
     HIGH_RISK on the high-confidence cell) -- what this would look like
     deployed, but only worth trusting if (1) shows a real, consistent
     effect first.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
import numpy as np
import pandas as pd
from round11_fvg_bias import load_1m, resample_causal, POINT_VALUE, TICK_SIZE, COMMISSION_RT, FOLDS
from round19_random_entry import causal_atr15_lookup
from round30_support_resistance import build_swing_touch_signals

TRAIL_MULT = 1.5
BUFFER = 4937.50
BASE_RISK = 300       # the trader's suggested flat baseline
HIGH_RISK = 2000       # the trader's suggested size-up ceiling for high-confidence setups
SWING_K = 3            # round30's dominant train-selected value (5/6 folds) -- fixed here, not re-swept
TOL = 0.50             # ditto
MIN_CELL_TRADES = 15   # ignore train cells too small to trust


def resolve_trailing_variable_risk(sig_df, df1m, symbol, trail_mult, max_hold_bars=390):
    """Adapted from round30b_sequential_fix.resolve_trailing_sequential: identical
    trailing-stop mechanics and one-position-at-a-time gating, but sig_df carries
    its own per-row `risk_dollar` instead of one fixed scalar for the whole call.
    Needed so confidence tiers share a single true chronological sequencing pass --
    resolving each tier separately would break the one-position-at-a-time
    constraint, since a base-tier trade can occupy the slot a later high-confidence
    signal would otherwise have used."""
    pv = POINT_VALUE[symbol]; tick = TICK_SIZE[symbol]
    slip_dollars_rt = 2 * tick * pv
    ts = df1m.index.values; hi = df1m["high"].values; lo = df1m["low"].values; cl = df1m["close"].values
    n = len(df1m)
    results = []
    next_free_pos = 0
    sig_df = sig_df.sort_values("ts").reset_index(drop=True)
    skipped_overlap = 0
    for r in sig_df.itertuples(index=False):
        pos = np.searchsorted(ts, np.datetime64(r.ts), side="right")
        if pos >= n:
            continue
        if pos < next_free_pos:
            skipped_overlap += 1
            continue
        init_dist = abs(r.entry - r.stop)
        if init_dist <= 0:
            continue
        trail_dist = trail_mult * init_dist
        contracts = max(1, int(r.risk_dollar // (init_dist * pv)))
        commission = COMMISSION_RT * contracts
        end_pos = min(pos + max_hold_bars, n - 1)
        cur_stop = r.entry - trail_dist if r.direction == 1 else r.entry + trail_dist
        best = r.entry; exit_px = None; outcome = "timeout"; exit_i = end_pos
        for i in range(pos, end_pos + 1):
            bar_hi, bar_lo = hi[i], lo[i]
            if r.direction == 1:
                if bar_lo <= cur_stop:
                    exit_px = cur_stop; outcome = "trail_stop"; exit_i = i; break
                best = max(best, bar_hi); cur_stop = max(cur_stop, best - trail_dist)
            else:
                if bar_hi >= cur_stop:
                    exit_px = cur_stop; outcome = "trail_stop"; exit_i = i; break
                best = min(best, bar_lo); cur_stop = min(cur_stop, best + trail_dist)
        if exit_px is None:
            exit_px = cl[end_pos]; outcome = "session_flatten"; exit_i = end_pos
        move = (exit_px - r.entry) if r.direction == 1 else (r.entry - exit_px)
        pnl = move * pv * contracts - commission - slip_dollars_rt * contracts
        results.append((r.ts, symbol, r.direction, r.risk_dollar, r.confidence_tier, contracts, pnl, outcome))
        next_free_pos = exit_i + 1
    out = pd.DataFrame(results, columns=["ts", "symbol", "direction", "risk", "confidence_tier", "contracts", "pnl", "outcome"])
    return out, skipped_overlap


def tier_buckets(sig, lag_terciles, pierce_terciles):
    lag_bucket = np.where(sig["touch_lag_bars"] <= lag_terciles[0], 0,
                  np.where(sig["touch_lag_bars"] <= lag_terciles[1], 1, 2))
    pierce_bucket = np.where(sig["pierce_frac"] <= pierce_terciles[0], 0,
                     np.where(sig["pierce_frac"] <= pierce_terciles[1], 1, 2))
    return lag_bucket, pierce_bucket


def main():
    symbol = "MGC"
    df1m = load_1m(f"../data/{symbol}_CONTINUOUS.txt")
    h15 = resample_causal(df1m, "15min")
    atr15 = causal_atr15_lookup(df1m)
    print(f"{symbol}: {len(df1m)} bars {df1m.index.min()} -> {df1m.index.max()}", flush=True)

    fixed_risk_tier_rows = []   # comparison (1): same risk, high-conf cell vs rest
    variable_rows = []           # comparison (2): the actual variable-sizing portfolio

    for fi, (train_end, test_end) in enumerate(FOLDS):
        train_end_ts = pd.Timestamp(train_end)
        test_end_ts = pd.Timestamp(min(pd.Timestamp(test_end), df1m.index.max()))
        if train_end_ts >= df1m.index.max():
            continue

        train_df = df1m[df1m.index < train_end_ts]
        train_h15 = h15[h15.index < train_end_ts]
        train_atr = atr15[atr15.index < train_end_ts]
        sig_train = build_swing_touch_signals(train_df, train_h15, train_atr, SWING_K, TOL)
        if len(sig_train) < 50:
            print(f"fold {fi}: not enough train signals ({len(sig_train)}), skipping")
            continue

        lag_terciles = sig_train["touch_lag_bars"].quantile([1 / 3, 2 / 3]).values
        pierce_terciles = sig_train["pierce_frac"].quantile([1 / 3, 2 / 3]).values

        sig_train = sig_train.copy()
        sig_train["risk_dollar"] = BASE_RISK
        sig_train["confidence_tier"] = "base"
        lag_b, pierce_b = tier_buckets(sig_train, lag_terciles, pierce_terciles)
        sig_train["lag_bucket"] = lag_b
        sig_train["pierce_bucket"] = pierce_b

        tr_train, _ = resolve_trailing_variable_risk(sig_train, train_df, symbol, TRAIL_MULT)
        tr_train = tr_train.merge(sig_train[["ts", "lag_bucket", "pierce_bucket"]], on="ts", how="left")
        cell_exp = tr_train.groupby(["lag_bucket", "pierce_bucket"])["pnl"].agg(["mean", "count"])
        cell_exp = cell_exp[cell_exp["count"] >= MIN_CELL_TRADES]
        if cell_exp.empty:
            print(f"fold {fi}: no train cell has >= {MIN_CELL_TRADES} trades, skipping")
            continue
        best_lag, best_pierce = cell_exp["mean"].idxmax()
        print(f"fold {fi} [{train_end}->{test_end}]: TRAIN-selected high-confidence cell = "
              f"(lag_bucket={best_lag}, pierce_bucket={best_pierce}), "
              f"train exp=${cell_exp.loc[(best_lag, best_pierce), 'mean']:.2f} "
              f"n={int(cell_exp.loc[(best_lag, best_pierce), 'count'])}", flush=True)

        test_df = df1m[(df1m.index >= train_end_ts) & (df1m.index < test_end_ts)]
        test_h15 = h15[(h15.index >= train_end_ts) & (h15.index < test_end_ts)]
        test_atr = atr15[(atr15.index >= train_end_ts) & (atr15.index < test_end_ts)]
        if len(test_df) < 100:
            continue
        sig_oos = build_swing_touch_signals(test_df, test_h15, test_atr, SWING_K, TOL)
        if sig_oos.empty:
            continue
        sig_oos = sig_oos.copy()
        lag_b_oos, pierce_b_oos = tier_buckets(sig_oos, lag_terciles, pierce_terciles)
        sig_oos["lag_bucket"] = lag_b_oos
        sig_oos["pierce_bucket"] = pierce_b_oos
        is_high_conf = (sig_oos["lag_bucket"] == best_lag) & (sig_oos["pierce_bucket"] == best_pierce)

        # -- comparison (1): fixed risk for everyone, tier is a label only --
        sig_fixed = sig_oos.copy()
        sig_fixed["risk_dollar"] = BASE_RISK
        sig_fixed["confidence_tier"] = np.where(is_high_conf, "high", "base")
        tr_fixed, _ = resolve_trailing_variable_risk(sig_fixed, test_df, symbol, TRAIL_MULT)
        for tier, grp in tr_fixed.groupby("confidence_tier"):
            fixed_risk_tier_rows.append(dict(fold=fi, tier=tier, n=len(grp),
                                              win_rate=(grp["pnl"] > 0).mean(),
                                              exp=grp["pnl"].mean(), total_pnl=grp["pnl"].sum()))

        # -- comparison (2): the actual variable-sizing portfolio --
        sig_var = sig_oos.copy()
        sig_var["risk_dollar"] = np.where(is_high_conf, HIGH_RISK, BASE_RISK)
        sig_var["confidence_tier"] = np.where(is_high_conf, "high", "base")
        tr_var, skipped = resolve_trailing_variable_risk(sig_var, test_df, symbol, TRAIL_MULT)
        if tr_var.empty:
            continue
        peak = tr_var["pnl"].cumsum().cummax(); dd = tr_var["pnl"].cumsum() - peak; maxdd = dd.min()
        variable_rows.append(dict(fold=fi, n=len(tr_var), n_skipped_overlap=skipped,
                                   n_high_conf=int(is_high_conf.sum()), n_base=int((~is_high_conf).sum()),
                                   total_pnl=tr_var["pnl"].sum(), max_dd=maxdd, breach=maxdd <= -BUFFER))
        print(f"  OOS variable-sizing: n={len(tr_var)} (high_conf={int(is_high_conf.sum())}, "
              f"base={int((~is_high_conf).sum())}) total=${tr_var['pnl'].sum():,.0f} "
              f"maxdd=${maxdd:,.0f} breach={maxdd <= -BUFFER}", flush=True)

    fixed_df = pd.DataFrame(fixed_risk_tier_rows)
    var_df = pd.DataFrame(variable_rows)
    fixed_df.to_csv("round56_fixed_risk_tier_results.csv", index=False)
    var_df.to_csv("round56_variable_sizing_results.csv", index=False)

    print("\n=== Comparison 1: SAME risk ($%d), high-confidence cell vs. rest, per fold ===" % BASE_RISK)
    pivot = fixed_df.pivot(index="fold", columns="tier", values="exp")
    print(pivot.round(2))
    if "high" in pivot.columns and "base" in pivot.columns:
        folds_high_wins = (pivot["high"] > pivot["base"]).sum()
        total_folds = pivot["high"].notna().sum()
        print(f"\nhigh-confidence cell beats base-tier expectancy in {folds_high_wins}/{total_folds} folds")

    print("\n=== Comparison 2: variable-sizing portfolio (base=$%d, high=$%d), pooled ===" % (BASE_RISK, HIGH_RISK))
    total_n = var_df["n"].sum()
    total_pnl = var_df["total_pnl"].sum()
    print(f"total_n={total_n} total_pnl=${total_pnl:,.2f} pooled_exp=${total_pnl/total_n:,.2f} "
          f"folds_breaching={var_df['breach'].sum()}/{len(var_df)}")
    print("\nDONE.")


if __name__ == "__main__":
    main()
