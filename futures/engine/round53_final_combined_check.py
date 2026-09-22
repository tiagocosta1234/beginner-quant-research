"""
Round 53: the most favorable configuration tonight's entire search produced --
all three confirmed real MNQ signals (Round 39 tod_last_third, Round 49 VWAP
Z-score, Round 52 busted-FVG) running simultaneously on one account, sequentially
gated so overlapping signals don't double-count a position, plain ATR-trailing
exits (time-decay in Round 51 was a wash, not included). Final answer to
whether tonight's full search -- every idea tried, combined -- changes the
profit-target Monte Carlo outcome.
"""
import os, sys
import datetime as dt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, resample_causal, detect_fvgs
from round19_random_entry import causal_atr15_lookup, generate_random_entries, build_stop_signals, TRAIL_ATR_MULT, SEEDS
from round30b_sequential_fix import resolve_trailing_sequential
from round34_fine_sizing_sweep import simulate_first_crossing
from round49_vwap_zscore import compute_session_vwap_z, build_zscore_signals
from round52_busted_fvg import build_busted_fvg_signals

SYMBOL = "MNQ"
_T2 = dt.time(13, 50)
_CLOSE = dt.time(16, 0)
Z_THRESH = 2.5
RISK_SWEEP = [100, 150, 200]


if __name__ == "__main__":
    mnq_path = os.path.join("..", "data", "MNQ_CONTINUOUS.txt")
    df1m = load_1m(mnq_path)
    atr15 = causal_atr15_lookup(df1m)
    df1m_z = compute_session_vwap_z(df1m)
    htf15 = resample_causal(df1m, "15min")
    fvgs = detect_fvgs(htf15)
    busted_sig = build_busted_fvg_signals(df1m, htf15, fvgs, atr15, 40)
    zsig = build_zscore_signals(df1m_z, atr15, Z_THRESH)
    print(f"data loaded; VWAP-Z signals={len(zsig)}, busted-FVG signals={len(busted_sig)}", flush=True)

    for risk in RISK_SWEEP:
        seeds_daily = []
        for seed in SEEDS:
            raw = generate_random_entries(df1m, seed)
            sig_tod = build_stop_signals(raw, atr15)
            t = sig_tod["ts"].dt.time
            sig_tod = sig_tod[(t >= _T2) & (t < _CLOSE)]

            combined = pd.concat([sig_tod, zsig, busted_sig], ignore_index=True).sort_values("ts").reset_index(drop=True)
            trades, _ = resolve_trailing_sequential(combined, df1m, SYMBOL, risk, TRAIL_ATR_MULT)
            if len(trades) == 0:
                continue
            trades["date"] = pd.to_datetime(trades["ts"]).dt.date
            daily = trades.groupby("date")["pnl"].sum()
            seeds_daily.append(daily)
        if not seeds_daily:
            print(f"risk=${risk}: no trades")
            continue
        pooled_mean = np.mean([s.mean() for s in seeds_daily])
        print(f"\nrisk=${risk}: mean_daily_pnl=${pooled_mean:.2f}", flush=True)
        for n_days in (20, 27):
            seed_results = [simulate_first_crossing(seeds_daily, n_days, 8000, mc_seed=s) for s in (31, 32, 33)]
            p_success = np.mean([r["p_success"] for r in seed_results])
            p_ruin = np.mean([r["p_ruin"] for r in seed_results])
            print(f"  days={n_days}  P(success)={p_success:.1%}  P(ruin)={p_ruin:.1%}", flush=True)

    print("\nDONE.")
