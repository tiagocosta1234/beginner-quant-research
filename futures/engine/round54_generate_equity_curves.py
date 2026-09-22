"""
Round 54: generate full-history trade logs (ts, pnl) for every real, confirmed
edge found across tonight's session and the earlier campaign, using each one's
now-established fixed parameters (the same numbers each round settled on) --
i.e. what the equity curve looks like if deployed as one fixed rule, not a
walk-forward re-optimization loop (that robustness case was already made
separately). Saves one CSV per edge for the equity-curve visualization.
"""
import os, sys
import datetime as dt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, resample_causal, detect_fvgs
from round19_random_entry import causal_atr15_lookup, generate_random_entries, build_stop_signals, resolve_trailing, TRAIL_ATR_MULT
from round30_support_resistance import build_swing_touch_signals
from round30b_sequential_fix import resolve_trailing_sequential
from round49_vwap_zscore import compute_session_vwap_z, build_zscore_signals
from round52_busted_fvg import build_busted_fvg_signals

OUT_DIR = "equity_curves"
os.makedirs(OUT_DIR, exist_ok=True)

_T2 = dt.time(13, 50)
_CLOSE = dt.time(16, 0)
Z_THRESH = 2.5
SEED = 0  # one representative seed for the two random-entry-based curves


def save(name, trades):
    trades = trades.sort_values("ts").reset_index(drop=True)
    trades["date"] = pd.to_datetime(trades["ts"]).dt.date
    daily = trades.groupby("date", as_index=False)["pnl"].sum()
    daily["cum_pnl"] = daily["pnl"].cumsum()
    daily.to_csv(os.path.join(OUT_DIR, f"{name}.csv"), index=False)
    print(f"{name}: {len(trades)} trades, {len(daily)} trading days, "
          f"final cum_pnl=${daily['cum_pnl'].iloc[-1]:,.2f}", flush=True)


if __name__ == "__main__":
    print("Loading MNQ...", flush=True)
    mnq_1m = load_1m(os.path.join("..", "data", "MNQ_CONTINUOUS.txt"))
    mnq_atr = causal_atr15_lookup(mnq_1m)
    mnq_z = compute_session_vwap_z(mnq_1m)
    mnq_htf15 = resample_causal(mnq_1m, "15min")
    mnq_fvgs = detect_fvgs(mnq_htf15)

    print("\n1. MNQ baseline (random entry + ATR trail, unfiltered) @ $200", flush=True)
    raw = generate_random_entries(mnq_1m, SEED)
    sig_base = build_stop_signals(raw, mnq_atr)
    save("1_mnq_baseline", resolve_trailing(sig_base, mnq_1m, "MNQ", 200, TRAIL_ATR_MULT))

    print("\n2. MNQ tod_last_third filter @ $200", flush=True)
    t = sig_base["ts"].dt.time
    sig_tod = sig_base[(t >= _T2) & (t < _CLOSE)]
    save("2_mnq_tod_last_third", resolve_trailing(sig_tod, mnq_1m, "MNQ", 200, TRAIL_ATR_MULT))

    print("\n3. MNQ VWAP Z-score mean reversion @ $200", flush=True)
    sig_z = build_zscore_signals(mnq_z, mnq_atr, Z_THRESH)
    trades_z, _ = resolve_trailing_sequential(sig_z, mnq_1m, "MNQ", 200, TRAIL_ATR_MULT)
    save("3_mnq_vwap_zscore", trades_z)

    print("\n4. MNQ busted-FVG @ $200", flush=True)
    sig_fvg = build_busted_fvg_signals(mnq_1m, mnq_htf15, mnq_fvgs, mnq_atr, 40)
    trades_fvg, _ = resolve_trailing_sequential(sig_fvg, mnq_1m, "MNQ", 200, TRAIL_ATR_MULT)
    save("4_mnq_busted_fvg", trades_fvg)

    print("\n5. MNQ combined (tod_last_third + VWAP-Z) @ $200", flush=True)
    combined = pd.concat([sig_tod, sig_z], ignore_index=True).sort_values("ts").reset_index(drop=True)
    trades_combined, _ = resolve_trailing_sequential(combined, mnq_1m, "MNQ", 200, TRAIL_ATR_MULT)
    save("5_mnq_combined", trades_combined)

    print("\nLoading MGC...", flush=True)
    mgc_1m = load_1m(os.path.join("..", "data", "MGC_CONTINUOUS.txt"))
    mgc_h15 = resample_causal(mgc_1m, "15min")
    mgc_atr = causal_atr15_lookup(mgc_1m)

    print("\n6. MGC swing S/R bounce (phantom-fill FIXED) @ $650", flush=True)
    sig_mgc = build_swing_touch_signals(mgc_1m, mgc_h15, mgc_atr, 3, 0.50)
    trades_mgc, _ = resolve_trailing_sequential(sig_mgc, mgc_1m, "MGC", 650, TRAIL_ATR_MULT)
    save("6_mgc_swing_bounce", trades_mgc)

    print("\nDONE.", flush=True)
