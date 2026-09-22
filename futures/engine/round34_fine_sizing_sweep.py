"""
Round 34: finer sizing sweep around Round 31b's coarse peak (multiplier steps of
0.5-1.0x), now using Round 32's CORRECTED "first target crossing = eval passed"
definition throughout (not Round 31's stricter "still above target at day 20"),
since that's the real-world pass condition. Goal: find the genuinely best sizing
point for the actual Oct 30 deadline, not just confirm the coarse grid's winner.
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, resample_causal
from round19_random_entry import causal_atr15_lookup
from round31_combined_portfolio import (
    build_mnq_daily, build_mgc_daily, combined_daily_series, block_bootstrap,
    CURRENT_BALANCE, TRAILING_FLOOR, DAILY_LOSS_LIMIT, PROFIT_TARGET_GAP, BLOCK_SIZE,
)
from round28_withdrawal_deadline import N_EVAL_DAYS

N_MC_PATHS = 8000

def simulate_first_crossing(series_list, n_days, n_paths, mc_seed):
    rng = np.random.default_rng(mc_seed)
    n_success = n_ruin = n_neither = 0
    pass_days = []
    for p in range(n_paths):
        daily = block_bootstrap(series_list, n_days, BLOCK_SIZE, rng)
        cum = np.cumsum(daily)
        equity = CURRENT_BALANCE + cum
        trailing_breach = equity <= TRAILING_FLOOR
        daily_breach = daily <= -DAILY_LOSS_LIMIT
        ruin_idx = None
        if trailing_breach.any() or daily_breach.any():
            idx_t = int(np.argmax(trailing_breach)) if trailing_breach.any() else n_days
            idx_d = int(np.argmax(daily_breach)) if daily_breach.any() else n_days
            ruin_idx = min(idx_t, idx_d)
        target_cross = np.argmax(cum >= PROFIT_TARGET_GAP) if (cum >= PROFIT_TARGET_GAP).any() else None
        if target_cross is not None and (ruin_idx is None or target_cross <= ruin_idx):
            n_success += 1
            pass_days.append(target_cross + 1)
        elif ruin_idx is not None:
            n_ruin += 1
        else:
            n_neither += 1
    return dict(p_success=n_success/n_paths, p_ruin=n_ruin/n_paths, p_neither=n_neither/n_paths,
                median_pass_day=float(np.median(pass_days)) if pass_days else None)

if __name__ == "__main__":
    mnq_path = os.path.join("..","data","MNQ_CONTINUOUS.txt")
    mgc_path = os.path.join("..","data","MGC_CONTINUOUS.txt")
    df1m_mnq = load_1m(mnq_path); atr15_mnq = causal_atr15_lookup(df1m_mnq)
    df1m_mgc = load_1m(mgc_path); h15_mgc = resample_causal(df1m_mgc, "15min"); atr15_mgc = causal_atr15_lookup(df1m_mgc)
    print("data loaded", flush=True)

    base_mnq, base_mgc = 75, 200
    multipliers = [2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75, 4.0, 4.25, 4.5]

    rows = []
    for mult in multipliers:
        mnq_risk = round(base_mnq * mult / 5) * 5  # round to nearest $5 for realistic order sizing
        mgc_risk = round(base_mgc * mult / 5) * 5
        mnq_seeds = build_mnq_daily(df1m_mnq, atr15_mnq, mnq_risk, n_seeds=15)
        mgc_daily = build_mgc_daily(df1m_mgc, h15_mgc, atr15_mgc, mgc_risk)
        combined_series = [combined_daily_series(s, mgc_daily) for s in mnq_seeds]
        # average over 3 MC seeds per point for a more stable comparison, given Round 33 showed ~0.5% seed noise
        seed_results = [simulate_first_crossing(combined_series, N_EVAL_DAYS, N_MC_PATHS, mc_seed=s) for s in (31,32,33)]
        p_success = np.mean([r['p_success'] for r in seed_results])
        p_ruin = np.mean([r['p_ruin'] for r in seed_results])
        p_neither = np.mean([r['p_neither'] for r in seed_results])
        rows.append((mult, mnq_risk, mgc_risk, p_success, p_ruin, p_neither))
        print(f"mult={mult:.2f}  MNQ=${mnq_risk} MGC=${mgc_risk}  P(success)={p_success:.1%}  P(ruin)={p_ruin:.1%}  P(neither)={p_neither:.1%}", flush=True)

    best = max(rows, key=lambda r: r[3])
    print(f"\nBest: mult={best[0]:.2f} MNQ=${best[1]} MGC=${best[2]} P(success)={best[3]:.1%} P(ruin)={best[4]:.1%}")
    print("DONE.")
