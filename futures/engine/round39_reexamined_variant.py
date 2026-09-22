"""
Round 39: re-examining Rounds 20-29's MNQ-only, tested-but-not-deployed entries
(FVG-confirmation + weekly-bias, and the simple 1H-EMA-slope trend entry) on MGC
specifically -- never tested there anywhere in Rounds 1-38 (Round 20's header says
"MNQ only... MGC's base effect from Round 19 didn't replicate, so not retested here",
and no later round revisited that decision for these two entries).

Motivation (mining this repo's own history for a fixable near-miss, not a new idea):
  - Round 17 found Entry 1 (weekly-bias x Round 12's confirmation-FVG), paired with a
    FIXED R:R exit, at -$10.52/trade on MNQ -- "closest to breakeven" of the whole
    90-variant campaign, rejected only because it stayed negative under that exit.
  - Round 20 then paired the SAME entry with a structurally different exit (Round 19's
    validated ATR-trailing stop) and it flipped positive on MNQ (+$38.85 @ $400 risk)
    -- confirming the exit, not the entry, was what Round 17 had wrong. That fixed
    combination (Entry 1/Entry 2 x ATR-trailing exit) was built and validated on MNQ
    only; MGC was never given the same combination a fair test.
  - Separately, Round 30's MGC swing-touch entry had a confirmed, fixed phantom-fill
    bug (EDGE_AUDIT_2026-09-20.md, fixed in round30_support_resistance.py's touches()
    2026-09-20): entries were credited at the idealized level price even when price
    only approached within a tolerance band and reversed. This round checks explicitly
    whether Entry 1 or Entry 2's OWN signal-generation code (round13_fvg_refinements.
    confirmed_entries_v2, round20_entry_comparison.build_ema_trend_entries) has the
    same "credited an untouched price" pattern -- it does not: both assign the entry
    price to c[found], the ACTUAL close of the actual bar that triggered the signal
    (never an idealized/unreached level), so the phantom-fill fix itself does not
    directly change these two entries' own numbers. What it DOES motivate is finally
    running the one combination (MNQ-validated entries x MGC data) this campaign never
    got to, using the exact same real repo functions and FOLDS schedule as every other
    round, not a re-fit.

Method: byte-for-byte reuse of round20_entry_comparison's construction (import, not
reimplement) with SYMBOL swapped to MGC:
  - Entry 1: round13_fvg_refinements.confirmed_entries_v2(body_ratio=0.60, beyond=0.0)
    + round17_prior_ref.apply_weekly_bias_filter, one/day, stop replaced by Round 19's
    ATR-based stop (byte-identical exit mechanism to every MNQ round).
  - Entry 2: round20_entry_comparison.build_ema_trend_entries (1H EMA(20) 3-bar slope,
    one/day at 10:00), same ATR-based stop.
  - Exit: round19_random_entry.resolve_trailing, UNCHANGED baseline params (1.0x ATR
    initial stop, 1.5x trailing) -- deliberately not grid-searched, per Round 24/27's
    own finding that grid-searching this exit's parameters overfits and makes buffer
    safety worse, not better, on both MNQ and MGC.
  - Walk-forward: round19_random_entry.walk_forward_fixed over the real FOLDS schedule
    (both entries have no fold-tunable parameter here, same design choice Round 20
    made explicitly to isolate entry-timing skill from a confounding grid search).
  - Buffer-safe sizing: round20_entry_comparison.find_buffer_safe_risk, unchanged.
  - Added here (not in Round 20's original): a one-sample t-test on pooled OOS trade
    P&L at the reported risk level, since this round's directive requires it explicitly.
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from round11_fvg_bias import (
    load_1m, resample_causal, detect_fvgs, BUFFER, FOLDS, one_per_day, fold_stats,
    tail_concentration,
)
from round13_fvg_refinements import confirmed_entries_v2, MIN_STOP_TICKS

# round13_fvg_refinements.MIN_STOP_TICKS only has an "MNQ" entry (that round was MNQ-only).
# confirmed_entries_v2() unconditionally computes `MIN_STOP_TICKS[symbol] * tick` even when
# tight_stop=False (this call's setting), where the value is never actually used -- it's an
# unreached-branch KeyError on MGC, not a live bug in the tight_stop=True path we don't use
# here. Extending the shared dict from the caller (not editing round13's file) is the minimal
# fix; the value is a no-op for this call since tight_stop=False throughout this round.
MIN_STOP_TICKS.setdefault("MGC", 4)
from round17_prior_ref import weekly_open_series, apply_weekly_bias_filter
from round19_random_entry import causal_atr15_lookup, resolve_trailing, walk_forward_fixed, TRAIL_ATR_MULT
from round20_entry_comparison import (
    build_atr_stop_signals, build_ema_trend_entries, run_entry, find_buffer_safe_risk,
)

SYMBOL = "MGC"
RISK_LEVELS = (400, 600)
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", f"{SYMBOL}_CONTINUOUS.txt")


def pooled_oos_trades(sig_df, df1m, symbol, risk):
    """Re-run walk_forward_fixed and return the pooled OOS trade frame at one risk
    level, plus per-fold stats -- used for the t-test / summary this round adds."""
    res = walk_forward_fixed(sig_df, df1m, symbol, resolve_trailing, {"trail_mult": TRAIL_ATR_MULT},
                              risk_levels=(risk,))[risk]
    trades, fold_info = [], []
    for train_end, test_end, _sel, te in res:
        if te is None or len(te) == 0:
            fold_info.append((train_end, test_end, 0, np.nan, 0.0, False))
            continue
        st = fold_stats(te)
        fold_info.append((train_end, test_end, st["n"], st["expectancy"], st["maxdd"], st["breach"]))
        trades.append(te)
    pooled = pd.concat(trades, ignore_index=True) if trades else pd.DataFrame(columns=["pnl"])
    return pooled, fold_info


def one_sample_ttest(pnl_series):
    if len(pnl_series) < 2:
        return dict(t=0.0, p=1.0, n=len(pnl_series))
    t, p = stats.ttest_1samp(pnl_series, popmean=0.0)
    return dict(t=float(t), p=float(p), n=len(pnl_series))


def main():
    print(f"Loading {SYMBOL} from {DATA_PATH} ...", flush=True)
    df1m = load_1m(DATA_PATH)
    print(f"{SYMBOL}: {len(df1m)} 1m bars, {df1m.index[0]} -> {df1m.index[-1]}", flush=True)

    atr15 = causal_atr15_lookup(df1m)

    # --- Entry 1: FVG-confirmation (0.60, 0.0) + weekly-open bias filter ---
    htf = resample_causal(df1m, "15min")
    fvgs = detect_fvgs(htf)
    sig_fvg = confirmed_entries_v2(fvgs, df1m, 0.60, 0.0, SYMBOL, tight_stop=False)
    sig_fvg = one_per_day(sig_fvg)
    week_open = weekly_open_series(df1m)
    sig_fvg_biased = apply_weekly_bias_filter(sig_fvg, df1m, week_open)
    entry1 = build_atr_stop_signals(sig_fvg_biased, atr15)
    print(f"Entry 1 (FVG-confirm + weekly-bias) on {SYMBOL}: {len(sig_fvg_biased)} raw "
          f"-> {len(entry1)} with valid ATR stop", flush=True)

    # --- Entry 2: 1H EMA(20) 3-bar slope trend, one/day at 10:00 ---
    raw_ema = build_ema_trend_entries(df1m)
    entry2 = build_atr_stop_signals(raw_ema, atr15)
    print(f"Entry 2 (1H EMA slope) on {SYMBOL}: {len(raw_ema)} raw -> {len(entry2)} with valid ATR stop",
          flush=True)

    results_1 = run_entry(f"ENTRY 1: FVG-confirmation + weekly-bias on {SYMBOL} + ATR-trailing exit",
                           entry1, df1m, SYMBOL)
    results_2 = run_entry(f"ENTRY 2: 1H EMA-slope trend on {SYMBOL} + ATR-trailing exit",
                           entry2, df1m, SYMBOL)

    print(f"\n\n### PART 1 SUMMARY: MNQ-validated entries x ATR-trailing exit, on {SYMBOL} (never tested) ###",
          flush=True)
    print("For reference -- Round 19's MGC random-entry baseline (same exit): -$2.99 to -$4.16/trade, "
          "sign-flipped from MNQ, 3/8 or fewer of 8 seeds positive.", flush=True)
    print("For reference -- Round 27's MGC-own-grid-search on this exit family: rejected (tail20=131.7%, "
          "textbook false positive; buffer floor $5,856-12,959 never clears $4,937.50 at any size).", flush=True)
    for label, res in [("Entry 1 (FVG+weekly-bias)", results_1), ("Entry 2 (1H EMA slope)", results_2)]:
        for risk in RISK_LEVELS:
            r = res.get(risk)
            if r:
                print(f"  {label} risk=${risk}: n={r['n']} exp=${r['exp']:.2f} win%={r['winrate']:.1%} "
                      f"worst_maxdd=${r['worst_maxdd']:.2f} folds_breaching={r['n_breach']}/{r['n_folds']}",
                      flush=True)
            else:
                print(f"  {label} risk=${risk}: no trades", flush=True)

    # --- t-stats on pooled OOS trades at $400 risk for both entries ---
    print("\n\n### t-TESTS on pooled OOS trade P&L (H0: mean pnl == 0), risk=$400 ###", flush=True)
    ttest_summary = {}
    for label, sig in [("Entry 1 (FVG+weekly-bias)", entry1), ("Entry 2 (1H EMA slope)", entry2)]:
        pooled, fold_info = pooled_oos_trades(sig, df1m, SYMBOL, 400)
        if len(pooled) == 0:
            print(f"  {label}: no OOS trades", flush=True)
            continue
        tt = one_sample_ttest(pooled["pnl"].values)
        worst_maxdd = max((fi[4] for fi in fold_info), default=0.0)
        n_breach = sum(1 for fi in fold_info if fi[5])
        tc10 = tail_concentration(pooled, 10) if pooled["pnl"].sum() > 0 else None
        tc20 = tail_concentration(pooled, 20) if pooled["pnl"].sum() > 0 else None
        ttest_summary[label] = dict(pooled=pooled, tt=tt, worst_maxdd=worst_maxdd, n_breach=n_breach,
                                     n_folds=len(fold_info), tc10=tc10, tc20=tc20)
        print(f"  {label}: n={tt['n']} mean=${pooled['pnl'].mean():.2f} t={tt['t']:.3f} p={tt['p']:.4g} "
              f"worst_maxdd=${worst_maxdd:.2f} folds_breaching={n_breach}/{len(fold_info)} "
              f"tail10={tc10} tail20={tc20}", flush=True)
        for train_end, test_end, n, exp, maxdd, breach in fold_info:
            print(f"    fold {train_end}->{test_end}: n={n} exp={'n/a' if pd.isna(exp) else f'${exp:.2f}'} "
                  f"maxdd=${maxdd:.2f} breach={breach}", flush=True)

    # --- Part 2: buffer-safe sizing on whichever performed better at $400 ---
    best_label, best_sig, best_exp_400 = None, None, -1e18
    for label, sig, res in [("Entry 1 (FVG+weekly-bias)", entry1, results_1),
                             ("Entry 2 (1H EMA slope)", entry2, results_2)]:
        r = res.get(400)
        if r and r["exp"] > best_exp_400:
            best_exp_400, best_label, best_sig = r["exp"], label, sig

    print(f"\n\n### PART 2: buffer-safe sizing for best-performing config on {SYMBOL}: {best_label} "
          f"(exp@$400=${best_exp_400:.2f}) ###", flush=True)
    if best_exp_400 <= 0:
        print(f"Best entry config on {SYMBOL} is non-positive at $400 risk -- buffer-safe sizing search "
              f"skipped. Neither MNQ-validated entry replicates a positive edge on {SYMBOL} with the "
              f"validated ATR-trailing exit.", flush=True)
    else:
        candidates = [400, 300, 250, 200, 150, 125, 100, 75, 50, 25]
        best = find_buffer_safe_risk(best_sig, df1m, SYMBOL, candidates)
        if best:
            risk, exp, worst_dd, n = best
            print(f"\nBuffer-safe size: risk=${risk}/trade, n={n} trades over 2024-01->{df1m.index.max().date()}, "
                  f"exp=${exp:.2f}/trade, worst_maxdd=${worst_dd:.2f} (within 70% margin of ${BUFFER:.2f} buffer)",
                  flush=True)
        else:
            print(f"No candidate risk level on {SYMBOL} clears the buffer-safe target even at the smallest "
                  f"size tested -- same structural floor Round 27 found for MGC's ATR-trailing exit family "
                  f"(point value $10/pt vs MNQ's $2/pt means the 1-contract floor itself exceeds the safe "
                  f"drawdown target).", flush=True)

    print("\nDONE.", flush=True)


if __name__ == "__main__":
    main()
