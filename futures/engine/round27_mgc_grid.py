"""
Round 27: grid-search MGC's OWN (stop_mult, trail_mult) for the Round 19 validated
exit style, independent of the MNQ-specific parameters (1.0x ATR stop, 1.5x ATR
trail) that Round 19 already found do NOT replicate on MGC (-$2.99 to -$4.16/trade).
That result is "MNQ's numbers don't work on MGC," not "no version of this exit
works on MGC" -- gold's volatility/point-value profile differs from a Nasdaq index
future, so this is a genuinely open question, not a re-test of something rejected.

Reuses Round 24's grid-search machinery directly (build_signals, resolve_vectorized,
run_part1, buffer_safe_search) rather than reimplementing it -- that machinery is
already generic in `symbol` (keyed cost lookups via POINT_VALUE[symbol]/TICK_SIZE
[symbol]), it was just never CALLED with symbol="MGC" for Part 1's grid search in
Round 24 (that round's Part 1 was MNQ-only; MGC only got baseline-params testing in
its Part 2, a different question about session-restriction).

STOP_MULT_GRID/TRAIL_MULT_GRID are multipliers on the instrument's OWN ATR, not
absolute price levels, so they are scale-invariant between MNQ and MGC by
construction -- reusing Round 24's exact grid bounds is correct, not an oversight.

Extra scrutiny applied per this round's own directive: Round 24 found that on MNQ, a
grid-search-selected tighter stop looked better on raw expectancy but was a real
risk-inflation trap (tighter stop -> more contracts per fixed $ risk -> the same
buffer gets hit harder and more often). Checked explicitly for the same pattern here
before reporting any result as a win.
"""
import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from round11_fvg_bias import load_1m, POINT_VALUE, TICK_SIZE, FOLDS, fold_stats, tail_concentration
from round19_random_entry import (
    causal_atr15_lookup, generate_random_entries, build_stop_signals, resolve_trailing,
    STOP_ATR_MULT as BASELINE_STOP_MULT, TRAIL_ATR_MULT as BASELINE_TRAIL_MULT,
)
from round24_grid_and_session import (
    build_signals, resolve_vectorized, run_part1, buffer_safe_search,
    STOP_MULT_GRID, TRAIL_MULT_GRID, RISK_MAIN,
)
from round23_multi_trade_v2 import SEEDS_WIDE, SIZING_GRID


def validate_vectorized_reproduces_round19_on_mgc(df1m, atr15, seeds=(0, 1, 3)):
    """Round 24 validated the vectorized resolver against Round 19's scalar
    resolve_trailing on MNQ only. Extend that validation to MGC before trusting the
    grid search here -- a symbol-specific cost/contract-sizing bug would otherwise
    be invisible (this is exactly the kind of thing this campaign's discipline
    (Round 9c, Round 23) exists to catch before it produces a fake result)."""
    for seed in seeds:
        raw = generate_random_entries(df1m, seed)
        sig_new = build_signals(raw, atr15, BASELINE_STOP_MULT)
        mine = resolve_vectorized(sig_new, df1m, "MGC", RISK_MAIN, BASELINE_TRAIL_MULT)

        sig_orig = build_stop_signals(raw, atr15)
        theirs = resolve_trailing(sig_orig, df1m, "MGC", RISK_MAIN, BASELINE_TRAIL_MULT)

        if len(mine) != len(theirs):
            raise AssertionError(f"MGC seed={seed}: n mismatch mine={len(mine)} theirs={len(theirs)}")
        if abs(mine["pnl"].sum() - theirs["pnl"].sum()) > 0.01:
            raise AssertionError(
                f"MGC seed={seed}: pnl sum mismatch mine={mine['pnl'].sum():.2f} theirs={theirs['pnl'].sum():.2f}"
            )
    return True


def risk_inflation_check(df1m, atr15, seeds, combo_a, combo_b, risk=RISK_MAIN):
    """Compare mean contracts/trade and worst-case drawdown between two
    (stop_mult, trail_mult) combos at the SAME dollar risk -- a tighter stop that
    only 'wins' by buying more contracts per fixed risk (Round 24's MNQ finding)
    should show up here as combo_b having both more contracts AND a worse maxdd
    despite possibly higher raw expectancy."""
    out = {}
    for label, (sm, tm) in [("A", combo_a), ("B", combo_b)]:
        all_trades = []
        for s in seeds:
            raw = generate_random_entries(df1m, s)
            sig = build_signals(raw, atr15, sm)
            trades = resolve_vectorized(sig, df1m, "MGC", risk, tm)
            all_trades.append(trades)
        pooled = pd.concat(all_trades, ignore_index=True)
        breach_rows = []
        for s, t in zip(seeds, all_trades):
            for train_end, test_end in FOLDS:
                fold_t = t[(t["ts"] >= pd.Timestamp(train_end)) & (t["ts"] < pd.Timestamp(test_end))]
                if len(fold_t) == 0:
                    continue
                st = fold_stats(fold_t)
                breach_rows.append(st["maxdd"])
        out[label] = dict(
            combo=(sm, tm), mean_contracts=float(pooled["contracts"].mean()) if len(pooled) else None,
            mean_exp=float(pooled["pnl"].mean()) if len(pooled) else None,
            worst_maxdd=max(breach_rows) if breach_rows else None,
        )
    return out


if __name__ == "__main__":
    mgc_path = os.path.join(os.path.dirname(__file__), "..", "data", "MGC_CONTINUOUS.txt")

    print("Loading MGC...", flush=True)
    df_mgc = load_1m(mgc_path)
    atr_mgc = causal_atr15_lookup(df_mgc)
    print(f"MGC: {len(df_mgc)} 1m bars, {df_mgc.index.min()} -> {df_mgc.index.max()}", flush=True)
    print(f"MGC causal 15m ATR(14): n={len(atr_mgc)}, median={atr_mgc.median():.3f}, "
          f"mean={atr_mgc.mean():.3f}, min={atr_mgc.min():.3f}, max={atr_mgc.max():.3f} "
          f"(price points; point_value=${POINT_VALUE['MGC']}/pt, tick={TICK_SIZE['MGC']})", flush=True)

    print("\nValidating vectorized resolver reproduces Round 19's scalar resolve_trailing "
          "on MGC specifically (Round 24 only validated this on MNQ)...", flush=True)
    validate_vectorized_reproduces_round19_on_mgc(df_mgc, atr_mgc)
    print("  PASS: exact match (n and total pnl to the cent) across seeds [0,1,3] on MGC", flush=True)

    print(f"\n{'='*70}\nPart 1: grid-search MGC's own (stop_mult, trail_mult)", flush=True)
    part1 = run_part1(df_mgc, atr_mgc, "MGC")

    dom = part1["dominant_combo"]
    print(f"\n{'='*70}\nRisk-inflation check: dominant grid combo vs. baseline, same $ risk", flush=True)
    if dom is not None and dom != (BASELINE_STOP_MULT, BASELINE_TRAIL_MULT):
        inflation = risk_inflation_check(
            df_mgc, atr_mgc, SEEDS_WIDE, (BASELINE_STOP_MULT, BASELINE_TRAIL_MULT), dom,
        )
        print(f"  baseline (A) combo={inflation['A']['combo']}: mean_contracts="
              f"{inflation['A']['mean_contracts']:.2f} mean_exp=${inflation['A']['mean_exp']:.2f} "
              f"worst_maxdd=${inflation['A']['worst_maxdd']:.2f}", flush=True)
        print(f"  grid-dominant (B) combo={inflation['B']['combo']}: mean_contracts="
              f"{inflation['B']['mean_contracts']:.2f} mean_exp=${inflation['B']['mean_exp']:.2f} "
              f"worst_maxdd=${inflation['B']['worst_maxdd']:.2f}", flush=True)
        contracts_up = inflation["B"]["mean_contracts"] > inflation["A"]["mean_contracts"]
        maxdd_up = inflation["B"]["worst_maxdd"] > inflation["A"]["worst_maxdd"]
        print(f"  RISK-INFLATION PATTERN (Round 24's MNQ finding) PRESENT: "
              f"{contracts_up and maxdd_up} (more contracts={contracts_up}, worse maxdd={maxdd_up})", flush=True)
    else:
        print("  dominant grid choice equals baseline or is undefined -- no separate combo to compare, "
              "skipping (the grid search did not prefer a different parameterization).", flush=True)
        inflation = None

    print(f"\n{'='*70}\nBuffer-safe sizing search (25-seed, Round 23 standard), both combos", flush=True)
    print(f"\n--- baseline: stop_mult={BASELINE_STOP_MULT} trail_mult={BASELINE_TRAIL_MULT} "
          f"(re-derivation of Round 19's rejected MGC baseline through this harness) ---", flush=True)
    sizing_base = buffer_safe_search(df_mgc, atr_mgc, "MGC", BASELINE_STOP_MULT, BASELINE_TRAIL_MULT)

    sizing_dom = pd.DataFrame()
    if dom is not None and dom != (BASELINE_STOP_MULT, BASELINE_TRAIL_MULT):
        print(f"\n--- grid-dominant: stop_mult={dom[0]} trail_mult={dom[1]} ---", flush=True)
        sizing_dom = buffer_safe_search(df_mgc, atr_mgc, "MGC", dom[0], dom[1])

    sizing_all = pd.concat([sizing_base, sizing_dom], ignore_index=True) if len(sizing_dom) else sizing_base
    out_dir = os.path.dirname(__file__)
    sizing_all.to_csv(os.path.join(out_dir, "round27_sizing_search.csv"), index=False)
    part1["pooled"].to_csv(os.path.join(out_dir, "round27_mgc_grid_trades.csv"), index=False)

    print("\n\nDONE.", flush=True)
