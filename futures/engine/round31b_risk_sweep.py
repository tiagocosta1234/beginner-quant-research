"""
Round 31b: extend Round 31's combined MNQ+MGC sweep to higher risk levels.

Round 31 found that at each instrument's individually-buffer-safe size (MNQ $75,
MGC $200), the combined portfolio has P(ruin)=0% but also P(success)=0.4% over the
real 20-day window -- essentially too conservative to reach the $19,184.62 profit
target in the time available. This sweeps risk higher to find where the
success/ruin tradeoff actually sits, honestly, rather than stopping at the "safe"
number and calling it done.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, resample_causal
from round19_random_entry import causal_atr15_lookup, generate_random_entries, build_stop_signals, resolve_trailing
from round30_support_resistance import build_swing_touch_signals
from round30b_sequential_fix import resolve_trailing_sequential
from round28_withdrawal_deadline import N_EVAL_DAYS
from round31_combined_portfolio import (
    build_mnq_daily, build_mgc_daily, combined_daily_series, simulate,
    REMAINING_BUFFER, PROFIT_TARGET_GAP
)

if __name__ == "__main__":
    mnq_path = os.path.join("..","data","MNQ_CONTINUOUS.txt")
    mgc_path = os.path.join("..","data","MGC_CONTINUOUS.txt")
    df1m_mnq = load_1m(mnq_path); atr15_mnq = causal_atr15_lookup(df1m_mnq)
    df1m_mgc = load_1m(mgc_path); h15_mgc = resample_causal(df1m_mgc, "15min"); atr15_mgc = causal_atr15_lookup(df1m_mgc)
    print("data loaded", flush=True)

    # keep MNQ:MGC risk ratio fixed at the Round 31 baseline (75:200 = 3:8), scale both up together
    ratios = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0]
    base_mnq, base_mgc = 75, 200

    rows = []
    for mult in ratios:
        mnq_risk = round(base_mnq * mult)
        mgc_risk = round(base_mgc * mult)
        mnq_seeds = build_mnq_daily(df1m_mnq, atr15_mnq, mnq_risk, n_seeds=15)
        mgc_daily = build_mgc_daily(df1m_mgc, h15_mgc, atr15_mgc, mgc_risk)
        combined_series = [combined_daily_series(s, mgc_daily) for s in mnq_seeds]
        res = simulate(combined_series, N_EVAL_DAYS)
        rows.append((mnq_risk, mgc_risk, res['p_ruin'], res['p_success'], res['p_neither'], res['median_final']))
        print(f"MNQ=${mnq_risk} MGC=${mgc_risk}  P(ruin)={res['p_ruin']:.1%}  P(success)={res['p_success']:.1%}  "
              f"P(neither)={res['p_neither']:.1%}  median_final=${res['median_final']:,.2f}", flush=True)

    print("\nDONE.", flush=True)
