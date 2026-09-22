"""
Round 38: with the phantom-fill bug fixed (2026-09-20) and the combined MNQ+MGC
portfolio sizing sweep now showing no viable point (round34 re-run: ruin exceeds
success at every size from 0.5x-4.5x), check three things the combined-only
sweep can't answer:
  1. MNQ traded ALONE (its signal generator was never touched by the MGC-only
     bug; independently re-verified as a real, if modest, edge earlier today).
  2. MGC traded ALONE, post-fix, at its own sizing (not combined with MNQ,
     which doubles the effective risk drawn against one shared buffer).
  3. Both of the above at BOTH the tight 20-trading-day sub-window Round 28
     carved out of the real ~30 days to 2026-10-30 (deliberately shortened to
     leave slack for the 5 Benchmark Trading Days + withdrawal processing) AND a
     fuller 27-trading-day window (same 3-day processing reserve round36/37
     used) -- to see whether the tight window itself, not the edge, is the
     binding constraint.
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, resample_causal
from round19_random_entry import causal_atr15_lookup
from round31_combined_portfolio import build_mnq_daily, build_mgc_daily
from round34_fine_sizing_sweep import simulate_first_crossing

N_MC_PATHS = 8000
DAY_BUDGETS = (20, 27)

if __name__ == "__main__":
    mnq_path = os.path.join("..", "data", "MNQ_CONTINUOUS.txt")
    mgc_path = os.path.join("..", "data", "MGC_CONTINUOUS.txt")
    df1m_mnq = load_1m(mnq_path); atr15_mnq = causal_atr15_lookup(df1m_mnq)
    df1m_mgc = load_1m(mgc_path); h15_mgc = resample_causal(df1m_mgc, "15min"); atr15_mgc = causal_atr15_lookup(df1m_mgc)
    print("data loaded", flush=True)

    print("\n" + "=" * 70)
    print("MNQ ALONE")
    print("=" * 70)
    base_mnq = 75
    for mult in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]:
        mnq_risk = round(base_mnq * mult / 5) * 5
        mnq_seeds = build_mnq_daily(df1m_mnq, atr15_mnq, mnq_risk, n_seeds=15)
        for n_days in DAY_BUDGETS:
            seed_results = [simulate_first_crossing(mnq_seeds, n_days, N_MC_PATHS, mc_seed=s) for s in (31, 32, 33)]
            p_success = np.mean([r["p_success"] for r in seed_results])
            p_ruin = np.mean([r["p_ruin"] for r in seed_results])
            p_neither = np.mean([r["p_neither"] for r in seed_results])
            print(f"MNQ=${mnq_risk} (mult={mult:.1f})  days={n_days}  "
                  f"P(success)={p_success:.1%}  P(ruin)={p_ruin:.1%}  P(neither)={p_neither:.1%}", flush=True)

    print("\n" + "=" * 70)
    print("MGC ALONE")
    print("=" * 70)
    base_mgc = 200
    for mult in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]:
        mgc_risk = round(base_mgc * mult / 5) * 5
        mgc_daily = build_mgc_daily(df1m_mgc, h15_mgc, atr15_mgc, mgc_risk)
        series_list = [mgc_daily]
        for n_days in DAY_BUDGETS:
            seed_results = [simulate_first_crossing(series_list, n_days, N_MC_PATHS, mc_seed=s) for s in (31, 32, 33)]
            p_success = np.mean([r["p_success"] for r in seed_results])
            p_ruin = np.mean([r["p_ruin"] for r in seed_results])
            p_neither = np.mean([r["p_neither"] for r in seed_results])
            print(f"MGC=${mgc_risk} (mult={mult:.1f})  days={n_days}  "
                  f"P(success)={p_success:.1%}  P(ruin)={p_ruin:.1%}  P(neither)={p_neither:.1%}", flush=True)

    print("\nDONE.")
