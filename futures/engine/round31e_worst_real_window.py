"""
Round 31e: does the Round 31c "100% success" hold up against the ACTUAL worst
real 20-consecutive-trading-day stretch in the recent fold (no bootstrap, just
the real sequence), not just the Monte Carlo's resampled version of it?
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, resample_causal
from round19_random_entry import causal_atr15_lookup
from round31_combined_portfolio import combined_daily_series, REMAINING_BUFFER, PROFIT_TARGET_GAP, DAILY_LOSS_LIMIT
from round31c_recent_regime_oos import build_mnq_daily_recent, build_mgc_daily_recent

if __name__ == "__main__":
    mnq_path = os.path.join("..","data","MNQ_CONTINUOUS.txt")
    mgc_path = os.path.join("..","data","MGC_CONTINUOUS.txt")
    df1m_mnq = load_1m(mnq_path); atr15_mnq = causal_atr15_lookup(df1m_mnq)
    df1m_mgc = load_1m(mgc_path); h15_mgc = resample_causal(df1m_mgc, "15min"); atr15_mgc = causal_atr15_lookup(df1m_mgc)

    mnq_seeds = build_mnq_daily_recent(df1m_mnq, atr15_mnq, 225, n_seeds=15)
    mgc_daily = build_mgc_daily_recent(df1m_mgc, h15_mgc, atr15_mgc, 600)

    worst_20d_sum = None
    worst_single_day = 0
    n_windows_checked = 0
    n_would_hit_target = 0
    for s in mnq_seeds:
        combined = combined_daily_series(s, mgc_daily).values
        worst_single_day = min(worst_single_day, combined.min())
        for start in range(0, len(combined) - 20 + 1):
            window = combined[start:start+20]
            cum = window.sum()
            n_windows_checked += 1
            if worst_20d_sum is None or cum < worst_20d_sum:
                worst_20d_sum = cum
            if cum >= PROFIT_TARGET_GAP:
                n_would_hit_target += 1

    print(f"Checked {n_windows_checked} real (non-bootstrapped) consecutive 20-day windows across 15 seeds")
    print(f"Worst real single day: ${worst_single_day:,.2f}  (daily loss limit=-${DAILY_LOSS_LIMIT:,.2f})")
    print(f"Worst real 20-day cumulative: ${worst_20d_sum:,.2f}  (buffer=-${REMAINING_BUFFER:,.2f})")
    print(f"Windows that would have hit the ${PROFIT_TARGET_GAP:,.2f} target: {n_would_hit_target}/{n_windows_checked} = {n_would_hit_target/n_windows_checked:.1%}")
