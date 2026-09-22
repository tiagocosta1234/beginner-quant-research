"""
Round 18: stack the least-bad components found across Rounds 12/13/17 on MNQ 15m HTF,
the best-performing configuration to date (Round 17's weekly-bias x confirmation-FVG
result was the closest-to-breakeven of the entire 89-variant search: -$10.52/trade).

Treated as likely the final systematic round of this campaign (session goal: find a
validated edge before the October deadline). Reuses every causal building block
directly from Rounds 11/12/13/17 rather than reimplementing (FVG detection,
confirmation-candle entry, confirmation-strictness grid, weekly-open bias filter) --
the only genuinely new element is a causal daily-volatility floor (Level D), a filter
type not present in any of the 89 prior variants.

Stacking levels, each independently walk-forward tested so the incremental effect of
each addition is visible, not just the final combined number:
  Level A: base confirmation-candle FVG entry (Round 12 Arm B, 15m, body=0.60/beyond=0.0,
           zone-edge stop) -- rr grid only.
  Level B: Level A's signals + weekly-open bias filter (Round 17's combo) -- rr grid only.
  Level C: Level B's mechanism, but (body_ratio, beyond_frac) ALSO grid-searched jointly
           with rr per fold (train-only selection, applied unchanged OOS) -- tests
           whether Round 13's strictness improvement (found mainly at 30m) stacks with
           the weekly-bias filter at 15m, rather than assuming Round 12's original
           (0.60, 0.0) choice is still optimal once the bias filter changes the sample.
  Level D: Level C + a causal daily-ATR(14) floor -- only trade on days whose realized
           volatility (computed from FULLY COMPLETED prior days only, shift(1)) is at or
           above a train-only-selected expanding percentile threshold. Grid: q in
           {0.0 (no filter), 0.25, 0.5}, selected jointly with (body_ratio, beyond_frac,
           rr) per fold via train expectancy, applied unchanged OOS.

Every level uses identical costs/sizing/folds to every prior round (imported directly
from round11_fvg_bias.py, not redefined): $1.24/contract round-trip commission, 2-tick
round-trip slippage, $400/$600 target risk, one trade/day cap, 6 expanding-window OOS
folds 2024-01 -> 2026-09. Tail-concentration check applied to any level whose aggregate
profit is positive, exactly as every prior round -- no exception for a "combined best
pieces" candidate despite it being, by construction, the most overfitting-prone
formulation tested all session.
"""
import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from round11_fvg_bias import (
    load_1m, resample_causal, detect_fvgs, POINT_VALUE, TICK_SIZE,
    COMMISSION_RT, BUFFER, FOLDS, one_per_day, fold_stats, tail_concentration,
)
from round12_fvg_confirmation import resolve_outcomes_plain
from round13_fvg_refinements import confirmed_entries_v2
from round17_prior_ref import weekly_open_series, apply_weekly_bias_filter

SYMBOL = "MNQ"
HTF_RULE = "15min"
RR_GRID = (1.5, 2.0)
RISK_LEVELS = (400, 600)
BODY_GRID = (0.60, 0.75)
BEYOND_GRID = (0.0, 0.15)
VOLQ_GRID = (0.0, 0.25, 0.5)


def daily_atr_causal(df1m, window=14):
    daily = df1m.groupby(df1m.index.date).agg(high=("high", "max"), low=("low", "min"))
    daily.index = pd.to_datetime(daily.index)
    daily = daily.sort_index()
    rng = daily["high"] - daily["low"]
    atr = rng.rolling(window).mean().shift(1)  # only fully-completed prior days
    return atr


def vol_floor_dates(atr_daily, q):
    """Returns the set of calendar dates (np.datetime64) that pass the vol floor for a
    given quantile q, using an expanding (causal, no future-date) quantile threshold."""
    if q <= 0:
        return None  # sentinel: no filter
    thresh = atr_daily.expanding(min_periods=20).quantile(q)
    passed = atr_daily >= thresh
    return set(pd.to_datetime(atr_daily.index[passed.values]).date)


def filter_by_dates(sig_df, allowed_dates):
    if allowed_dates is None:
        return sig_df
    if len(sig_df) == 0:
        return sig_df
    d = pd.to_datetime(sig_df["ts"]).dt.date
    return sig_df[d.isin(allowed_dates)].reset_index(drop=True)


def walk_forward_fixed(sig_all, df1m, symbol, rr_grid, risk_levels):
    """Level A/B: signal set fixed, only rr is grid-searched per fold."""
    out = {}
    for risk in risk_levels:
        fold_rows = []
        for train_end, test_end in FOLDS:
            train_sig = sig_all[sig_all["ts"] < train_end]
            test_sig = sig_all[(sig_all["ts"] >= train_end) & (sig_all["ts"] < test_end)]
            if len(train_sig) < 20 or len(test_sig) == 0:
                fold_rows.append((train_end, test_end, None, None))
                continue
            best_rr, best_exp = None, -1e18
            for rr in rr_grid:
                tr = resolve_outcomes_plain(train_sig, df1m, symbol, rr, risk)
                if len(tr) == 0:
                    continue
                exp = tr["pnl"].mean()
                if exp > best_exp:
                    best_exp, best_rr = exp, rr
            if best_rr is None:
                fold_rows.append((train_end, test_end, None, None))
                continue
            te = resolve_outcomes_plain(test_sig, df1m, symbol, best_rr, risk)
            fold_rows.append((train_end, test_end, best_rr, te))
        out[risk] = fold_rows
    return out


def walk_forward_grid(sig_cache, df1m, symbol, rr_grid, risk_levels):
    """Level C/D: sig_cache maps a key (e.g. (br,bf) or (br,bf,q)) -> full signal set.
    Grid-searches the key jointly with rr per fold, train-only, applied unchanged OOS."""
    out = {}
    for risk in risk_levels:
        fold_rows = []
        for train_end, test_end in FOLDS:
            best_combo, best_exp = None, -1e18
            for key, sig in sig_cache.items():
                train_sig = sig[sig["ts"] < train_end]
                if len(train_sig) < 20:
                    continue
                for rr in rr_grid:
                    tr = resolve_outcomes_plain(train_sig, df1m, symbol, rr, risk)
                    if len(tr) == 0:
                        continue
                    exp = tr["pnl"].mean()
                    if exp > best_exp:
                        best_exp, best_combo = exp, (key, rr)
            if best_combo is None:
                fold_rows.append((train_end, test_end, None, None))
                continue
            key, rr = best_combo
            sig = sig_cache[key]
            test_sig = sig[(sig["ts"] >= train_end) & (sig["ts"] < test_end)]
            if len(test_sig) == 0:
                fold_rows.append((train_end, test_end, (key, rr), None))
                continue
            te = resolve_outcomes_plain(test_sig, df1m, symbol, rr, risk)
            fold_rows.append((train_end, test_end, (key, rr), te))
        out[risk] = fold_rows
    return out


def print_results(label, res):
    for risk, fold_rows in res.items():
        print(f"-- {label} risk=${risk} --", flush=True)
        all_trades = []
        for train_end, test_end, sel, te in fold_rows:
            if te is None:
                print(f"  {train_end}->{test_end}: no signals (sel={sel})", flush=True)
                continue
            st = fold_stats(te)
            print(f"  {train_end}->{test_end} sel={sel} n={st['n']} win%={st['winrate']:.1%} "
                  f"exp=${st['expectancy']:.2f} total=${st['total']:.2f} maxdd=${st['maxdd']:.2f} "
                  f"breach={st['breach']}", flush=True)
            all_trades.append(te)
        if all_trades:
            combo = pd.concat(all_trades, ignore_index=True)
            tc10 = tail_concentration(combo, 10)
            tc20 = tail_concentration(combo, 20)
            print(f"  AGGREGATE n={len(combo)} total=${combo['pnl'].sum():.2f} "
                  f"exp=${combo['pnl'].mean():.2f} win%={(combo['pnl']>0).mean():.1%} "
                  f"tail10={tc10} tail20={tc20}", flush=True)
        print(flush=True)


def main():
    print(f"Loading {SYMBOL}...", flush=True)
    df1m = load_1m(f"../data/{SYMBOL}_CONTINUOUS.txt")
    print(f"{SYMBOL}: {len(df1m)} 1m bars, {df1m.index[0]} -> {df1m.index[-1]}", flush=True)

    htf = resample_causal(df1m, HTF_RULE)
    fvgs = detect_fvgs(htf)
    print(f"FVGs detected (15m): {len(fvgs)}", flush=True)

    week_open = weekly_open_series(df1m)
    atr_daily = daily_atr_causal(df1m, window=14)

    # ---- Level A: base confirmation entry (0.60, 0.0), rr grid only ----
    sig_A = confirmed_entries_v2(fvgs, df1m, 0.60, 0.0, SYMBOL, tight_stop=False)
    sig_A = one_per_day(sig_A)
    print(f"\nLevel A signals (1/day): {len(sig_A)}", flush=True)
    res_A = walk_forward_fixed(sig_A, df1m, SYMBOL, RR_GRID, RISK_LEVELS)
    print_results("LEVEL A: base confirmation (0.60,0.0)", res_A)

    # ---- Level B: Level A + weekly-open bias filter ----
    sig_B = apply_weekly_bias_filter(sig_A, df1m, week_open)
    print(f"Level B signals (weekly-bias filtered): {len(sig_B)}", flush=True)
    res_B = walk_forward_fixed(sig_B, df1m, SYMBOL, RR_GRID, RISK_LEVELS)
    print_results("LEVEL B: A + weekly-bias filter", res_B)

    # ---- Level C: (body,beyond) grid searched jointly, each combo weekly-bias-filtered ----
    sig_cache_C = {}
    for br in BODY_GRID:
        for bf in BEYOND_GRID:
            s = confirmed_entries_v2(fvgs, df1m, br, bf, SYMBOL, tight_stop=False)
            s = one_per_day(s)
            s = apply_weekly_bias_filter(s, df1m, week_open)
            sig_cache_C[(br, bf)] = s
            print(f"  Level C candidate (br={br}, bf={bf}): {len(s)} signals after weekly-bias filter", flush=True)
    res_C = walk_forward_grid(sig_cache_C, df1m, SYMBOL, RR_GRID, RISK_LEVELS)
    print_results("LEVEL C: B + strictness grid (train-only per fold)", res_C)

    # ---- Level D: Level C's cache, further split by vol-floor q, grid over (br,bf,q,rr) ----
    sig_cache_D = {}
    vol_dates_cache = {q: vol_floor_dates(atr_daily, q) for q in VOLQ_GRID}
    for (br, bf), s in sig_cache_C.items():
        for q in VOLQ_GRID:
            allowed = vol_dates_cache[q]
            s2 = filter_by_dates(s, allowed)
            sig_cache_D[(br, bf, q)] = s2
            print(f"  Level D candidate (br={br}, bf={bf}, volq={q}): {len(s2)} signals", flush=True)
    res_D = walk_forward_grid(sig_cache_D, df1m, SYMBOL, RR_GRID, RISK_LEVELS)
    print_results("LEVEL D: C + causal daily-ATR(14) volatility floor (train-only per fold)", res_D)

    print("DONE", flush=True)


if __name__ == "__main__":
    main()
