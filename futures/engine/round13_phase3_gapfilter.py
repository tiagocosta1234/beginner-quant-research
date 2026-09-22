"""
Round 13 Phase 3: 4H gap-reaction filter (Refinement 3) applied on top of the
Best Combo selected from Phases 1+2 (see round13_mnq_results_phase12.txt):

Refinement 1 (tighter stop at the confirmation candle's extreme) was DECISIVELY
REJECTED -- worse than the zone-edge stop in every comparison (e.g. 15m: exp
-$46.63 -> -$118.15 at $400 risk). Mechanism: a tighter stop forces more contracts
for the same $ risk (contracts = risk_dollar // (stop_dist * pv)), so fixed
per-contract commission+slippage costs eat a much larger share of expectancy. Not
used in Best Combo.

Refinement 2 (confirmation strictness grid) gave a modest improvement, concentrated
at 30m HTF: body_ratio=0.75, beyond_frac=0.15 was the most consistently-selected
train-optimal combo there, roughly halving the average loss at $400 risk (-$38.90
-> -$19.38) but with high fold-to-fold variance (2 of 6 folds clearly positive,
4 clearly negative -- not stable). At 15m, the grid found no meaningful improvement
over Round 12's original (0.60, 0.0) choice.

Best Combo used here: zone-edge stop (Refinement 1's loser excluded); 15m uses
(body=0.60, beyond=0.0) unchanged from Round 12; 30m uses (body=0.75, beyond=0.15)
per Refinement 2's finding.
"""
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from round11_fvg_bias import (
    load_1m, resample_causal, detect_fvgs, FOLDS, one_per_day, fold_stats, tail_concentration,
)
from round12_fvg_confirmation import resolve_outcomes_plain, walk_forward_generic, print_results
from round13_fvg_refinements import confirmed_entries_v2, gap_direction_series, attach_gap, GAP_TICKS_MIN

BEST_COMBO = {"15m": (0.60, 0.0), "30m": (0.75, 0.15)}

if __name__ == "__main__":
    symbol = "MNQ"
    path = sys.argv[1] if len(sys.argv) > 1 else "../data/MNQ_CONTINUOUS.txt"
    print(f"Loading {symbol} from {path} ...", flush=True)
    df1m = load_1m(path)
    print(f"{symbol}: {len(df1m)} 1m bars, {df1m.index.min()} -> {df1m.index.max()}", flush=True)

    gap_dir = gap_direction_series(df1m, symbol)
    n_gaps = int((gap_dir != 0).sum())
    print(f"4H bars: {len(gap_dir)}, significant gaps (>{GAP_TICKS_MIN} ticks): {n_gaps}", flush=True)

    for htf_rule, htf_name in [("15min", "15m"), ("30min", "30m")]:
        body, beyond = BEST_COMBO[htf_name]
        htf = resample_causal(df1m, htf_rule)
        fvgs = detect_fvgs(htf)
        base_sig = one_per_day(confirmed_entries_v2(fvgs, df1m, body, beyond, symbol, tight_stop=False))
        base_sig = attach_gap(base_sig, gap_dir)
        n_gapped = int((base_sig["gap"] != 0).sum())
        print(f"\n############ {symbol} HTF={htf_name} BestCombo(body={body},beyond={beyond}): "
              f"{len(base_sig)} base signals, {n_gapped} occur after a significant 4H gap ############", flush=True)

        # No-filter baseline for this exact Best Combo (for direct before/after comparison)
        res_base = walk_forward_generic(base_sig, df1m, symbol, resolve_outcomes_plain, {})
        print_results(f"BestCombo no-gap-filter HTF={htf_name}", res_base)

        # FILL: entry direction OPPOSES the most recently closed 4H gap
        sig_fill = base_sig[(base_sig["gap"] != 0) & (base_sig["direction"] == -base_sig["gap"])].copy()
        print(f"\nFILL arm signal count: {len(sig_fill)}", flush=True)
        if len(sig_fill) >= 50:
            res_fill = walk_forward_generic(sig_fill, df1m, symbol, resolve_outcomes_plain, {})
            print_results(f"R3 GAP-FILL HTF={htf_name}", res_fill)
        else:
            print(f"SKIPPED: sample size {len(sig_fill)} < 50, insufficient for a 6-fold walk-forward read", flush=True)

        # CONTINUATION: entry direction MATCHES the most recently closed 4H gap
        sig_cont = base_sig[(base_sig["gap"] != 0) & (base_sig["direction"] == base_sig["gap"])].copy()
        print(f"\nCONTINUATION arm signal count: {len(sig_cont)}", flush=True)
        if len(sig_cont) >= 50:
            res_cont = walk_forward_generic(sig_cont, df1m, symbol, resolve_outcomes_plain, {})
            print_results(f"R3 GAP-CONTINUATION HTF={htf_name}", res_cont)
        else:
            print(f"SKIPPED: sample size {len(sig_cont)} < 50, insufficient for a 6-fold walk-forward read", flush=True)

    print("\n\n############ Round 13 Phase 3 complete ############", flush=True)
