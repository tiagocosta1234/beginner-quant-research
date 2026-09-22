"""
Round 33: is Round 31/32's 83-86% success figure robust, or a single-MC-seed
fluke? Re-run the SAME combined portfolio (MNQ $225 / MGC $600) at the same
N_EVAL_DAYS=20 horizon across 10 independent Monte Carlo seeds (the underlying
historical trade pool is unchanged -- only which block-bootstrap draws get
sampled changes). If the real edge is robust, results should cluster tightly;
if they scatter widely, Round 31's headline number was oversold.
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, resample_causal
from round19_random_entry import causal_atr15_lookup
from round31_combined_portfolio import (
    build_mnq_daily, build_mgc_daily, combined_daily_series, simulate,
)
from round28_withdrawal_deadline import N_EVAL_DAYS

if __name__ == "__main__":
    mnq_path = os.path.join("..","data","MNQ_CONTINUOUS.txt")
    mgc_path = os.path.join("..","data","MGC_CONTINUOUS.txt")
    df1m_mnq = load_1m(mnq_path); atr15_mnq = causal_atr15_lookup(df1m_mnq)
    df1m_mgc = load_1m(mgc_path); h15_mgc = resample_causal(df1m_mgc, "15min"); atr15_mgc = causal_atr15_lookup(df1m_mgc)
    print("data loaded", flush=True)

    mnq_seeds = build_mnq_daily(df1m_mnq, atr15_mnq, 225, n_seeds=15)
    mgc_daily = build_mgc_daily(df1m_mgc, h15_mgc, atr15_mgc, 600)
    combined_series = [combined_daily_series(s, mgc_daily) for s in mnq_seeds]

    results = []
    for mc_seed in range(1, 11):
        res = simulate(combined_series, N_EVAL_DAYS, n_paths=8000, mc_seed=mc_seed)
        results.append(res)
        print(f"MC_SEED={mc_seed}: P(ruin)={res['p_ruin']:.1%} P(success)={res['p_success']:.1%} "
              f"P(neither)={res['p_neither']:.1%} median_final=${res['median_final']:,.2f}", flush=True)

    p_success = np.array([r['p_success'] for r in results])
    p_ruin = np.array([r['p_ruin'] for r in results])
    print(f"\nAcross 10 independent MC seeds:")
    print(f"  P(success): mean={p_success.mean():.1%} std={p_success.std():.2%} min={p_success.min():.1%} max={p_success.max():.1%}")
    print(f"  P(ruin):    mean={p_ruin.mean():.1%} std={p_ruin.std():.2%} min={p_ruin.min():.1%} max={p_ruin.max():.1%}")
