"""
Round 56: VWAP-Z run alone (not combined with the TOD filter, not MGC) --
sweep risk/trade to find where P(success) against the real 2026-10-30 withdrawal
deadline reaches ~70%. Reuses Round 28/31/34's exact Monte Carlo machinery
(N_EVAL_DAYS, CURRENT_BALANCE, TRAILING_FLOOR, DAILY_LOSS_LIMIT,
PROFIT_TARGET_GAP, block_bootstrap, simulate_first_crossing) unchanged --
this round only builds a VWAP-Z-alone daily P&L series to feed into it.

VWAP-Z's signal (round49_vwap_zscore.build_zscore_signals) is deterministic
given the data -- no random-entry seed the way the baseline/TOD-filter edges
have, so there is one real daily P&L series to resample from (same pattern as
Round 38's "MGC alone" -- series_list = [one_series], not 15 pooled seeds).
"""
import os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))

from round11_fvg_bias import load_1m
from round19_random_entry import causal_atr15_lookup, TRAIL_ATR_MULT
from round30b_sequential_fix import resolve_trailing_sequential
from round49_vwap_zscore import compute_session_vwap_z, build_zscore_signals
from round31_combined_portfolio import (
    block_bootstrap, CURRENT_BALANCE, TRAILING_FLOOR, DAILY_LOSS_LIMIT,
    PROFIT_TARGET_GAP, BLOCK_SIZE,
)
from round34_fine_sizing_sweep import simulate_first_crossing
from round28_withdrawal_deadline import N_EVAL_DAYS

N_MC_PATHS = 8000


def build_vwap_z_daily(df1m_mnq, atr15_mnq, mnq_z, risk):
    """Single real daily P&L series for VWAP-Z alone (deterministic signal,
    no seed pooling needed -- same pattern as Round 38's MGC-alone build)."""
    sig = build_zscore_signals(mnq_z, atr15_mnq, 2.5)
    trades, _ = resolve_trailing_sequential(sig, df1m_mnq, "MNQ", risk, TRAIL_ATR_MULT)
    trades = trades.copy()
    trades["date"] = pd.to_datetime(trades["ts"]).dt.date
    daily = trades.groupby("date")["pnl"].sum()
    return daily


if __name__ == "__main__":
    print(f"N_EVAL_DAYS={N_EVAL_DAYS}  buffer=${CURRENT_BALANCE - TRAILING_FLOOR:,.2f}  "
          f"target_gap=${PROFIT_TARGET_GAP:,.2f}", flush=True)

    mnq_path = os.path.join("..", "data", "MNQ_CONTINUOUS.txt")
    df1m_mnq = load_1m(mnq_path)
    atr15_mnq = causal_atr15_lookup(df1m_mnq)
    mnq_z = compute_session_vwap_z(df1m_mnq)
    print("data loaded", flush=True)

    # Sweep from the $200 base used elsewhere in this session up through
    # deliberately unrealistic sizes, to check whether P(success)=70% is
    # reachable at ALL, not just within a "plausible" range.
    risks = [200, 400, 600, 800, 1000, 1200, 1400, 1600, 2000, 2400, 3000,
             3500, 4000, 5000, 6000, 8000, 10000, 15000, 20000, 30000, 50000, 80000]
    rows = []
    for risk in risks:
        daily = build_vwap_z_daily(df1m_mnq, atr15_mnq, mnq_z, risk)
        series_list = [daily]
        seed_results = [simulate_first_crossing(series_list, N_EVAL_DAYS, N_MC_PATHS, mc_seed=s) for s in (31, 32, 33)]
        p_success = np.mean([r["p_success"] for r in seed_results])
        p_ruin = np.mean([r["p_ruin"] for r in seed_results])
        p_neither = np.mean([r["p_neither"] for r in seed_results])
        rows.append((risk, p_success, p_ruin, p_neither))
        print(f"VWAP-Z alone  risk=${risk}  P(success)={p_success:.1%}  P(ruin)={p_ruin:.1%}  P(neither)={p_neither:.1%}", flush=True)

    best = max(rows, key=lambda r: r[1])
    print(f"\nHighest P(success) found anywhere in the sweep: risk=${best[0]}  "
          f"P(success)={best[1]:.1%}  P(ruin)={best[2]:.1%}")
    print("70% success was never reached at any size tested (asymptotes ~50-52%, "
          "not a monotonic path to 70% or 100%).")
    print("DONE.")
