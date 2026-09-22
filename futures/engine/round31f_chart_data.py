"""Generate sample equity paths for the updated combined-portfolio equity curve
artifact, at Round 31's recommended sizing (MNQ $225 / MGC $600), over the real
N_EVAL_DAYS=20 window. Honest sample: no cherry-picking -- take the first N
paths from a fixed-seed run and report whatever mix of outcomes results, same
convention as the original $2,000/trade chart's 8 real seeds.
"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, resample_causal
from round19_random_entry import causal_atr15_lookup
from round31_combined_portfolio import (
    build_mnq_daily, build_mgc_daily, combined_daily_series, block_bootstrap,
    CURRENT_BALANCE, TRAILING_FLOOR, DAILY_LOSS_LIMIT, PROFIT_TARGET_GAP, BLOCK_SIZE
)
from round28_withdrawal_deadline import N_EVAL_DAYS

N_PATHS = 28
MC_SEED = 31

if __name__ == "__main__":
    mnq_path = os.path.join("..","data","MNQ_CONTINUOUS.txt")
    mgc_path = os.path.join("..","data","MGC_CONTINUOUS.txt")
    df1m_mnq = load_1m(mnq_path); atr15_mnq = causal_atr15_lookup(df1m_mnq)
    df1m_mgc = load_1m(mgc_path); h15_mgc = resample_causal(df1m_mgc, "15min"); atr15_mgc = causal_atr15_lookup(df1m_mgc)
    print("data loaded", flush=True)

    mnq_seeds = build_mnq_daily(df1m_mnq, atr15_mnq, 225, n_seeds=15)
    mgc_daily = build_mgc_daily(df1m_mgc, h15_mgc, atr15_mgc, 600)
    combined_series = [combined_daily_series(s, mgc_daily) for s in mnq_seeds]

    rng = np.random.default_rng(MC_SEED)
    profit_target_balance = CURRENT_BALANCE + PROFIT_TARGET_GAP
    paths_out = []
    n_success = n_ruin = n_neither = 0
    for p in range(N_PATHS):
        daily = block_bootstrap(combined_series, N_EVAL_DAYS, BLOCK_SIZE, rng)
        cum = np.cumsum(daily)
        equity = CURRENT_BALANCE + cum
        trailing_breach = equity <= TRAILING_FLOOR
        daily_breach = daily <= -DAILY_LOSS_LIMIT
        breach_idx = None
        if trailing_breach.any() or daily_breach.any():
            idx_t = int(np.argmax(trailing_breach)) if trailing_breach.any() else N_EVAL_DAYS
            idx_d = int(np.argmax(daily_breach)) if daily_breach.any() else N_EVAL_DAYS
            breach_idx = min(idx_t, idx_d)
            equity_trunc = equity[:breach_idx+1]
            status = "ruin"
            n_ruin += 1
        else:
            equity_trunc = equity
            if cum[-1] >= PROFIT_TARGET_GAP:
                status = "success"
                n_success += 1
            else:
                status = "neither"
                n_neither += 1
        pts = [{"day": 0, "bal": round(CURRENT_BALANCE, 2)}]
        for i, bal in enumerate(equity_trunc):
            pts.append({"day": i+1, "bal": round(float(bal), 2)})
        paths_out.append({"path": p, "status": status, "points": pts, "final": round(float(pts[-1]["bal"]), 2)})

    print(f"N_PATHS={N_PATHS}: success={n_success} ({n_success/N_PATHS:.1%}) ruin={n_ruin} ({n_ruin/N_PATHS:.1%}) neither={n_neither} ({n_neither/N_PATHS:.1%})")
    print(f"trailing_floor={TRAILING_FLOOR:.2f} profit_target_balance={profit_target_balance:.2f} start={CURRENT_BALANCE:.2f}")

    out = {
        "n_paths": N_PATHS, "n_eval_days": N_EVAL_DAYS,
        "start_balance": round(CURRENT_BALANCE, 2),
        "trailing_floor": round(TRAILING_FLOOR, 2),
        "profit_target_balance": round(profit_target_balance, 2),
        "daily_loss_limit": DAILY_LOSS_LIMIT,
        "mc_p_success": 0.834, "mc_p_ruin": 0.038, "mc_p_neither": 0.128,  # full 8000-path Round 31b figures
        "sample_p_success": n_success/N_PATHS, "sample_p_ruin": n_ruin/N_PATHS, "sample_p_neither": n_neither/N_PATHS,
        "paths": paths_out,
    }
    with open("round31f_chart_data.json", "w") as f:
        json.dump(out, f)
    print("wrote round31f_chart_data.json")
