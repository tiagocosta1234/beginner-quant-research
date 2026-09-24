"""
Round 90: the trader asked directly -- if Round 89's bootstrap bar is real, does the
ORIGINAL TOD/VWAP-Z ("the trader") strategy, the one actually traded on the real $250K
account before tonight's OTE/FVG work even started, also clear it? Applying a new
rigor standard only to the new candidate while never checking it against the old
one would be inconsistent -- this closes that gap honestly, not defensively.

Reuses Round 69's exact resolver (resolve_true_risk_with_day_cap, the one with the
verified trail_dist-based true sizing and same-day halt) at the actual sizing
decision recorded in TRADING_JOURNAL.md 2026-09-22 ("Sizing decision made: $3,000
daily cap, TOD $2,100 / VWAP-Z $1,500" -- chosen for best success-minus-ruin edge
on Round 69b's frontier), against MNQ_CONTINUOUS.txt, the real 3.8-year dataset
this strategy was actually validated against (NOT the short BrokerAPI pull -- that
standing rule only applies to backtests started 2026-09-23 onward; this strategy
predates it and was never re-validated against the shorter real pull).

Same bootstrap methodology as Round 89, same unit (per-trade real PnL, resampled
with replacement 10,000x) -- a like-for-like check, not a different, more
forgiving one.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
import datetime as dt
import numpy as np
import pandas as pd
from round11_fvg_bias import load_1m
from round19_random_entry import causal_atr15_lookup, generate_random_entries, build_stop_signals, TRAIL_ATR_MULT
from round49_vwap_zscore import compute_session_vwap_z, build_zscore_signals
from round69_true_2000_daily_cap import resolve_true_risk_with_day_cap
from round89_ote_multi_symbol_significance import bootstrap_expectancy_ci, N_BOOTSTRAP

TOD_RISK = 2100.0
VWAPZ_RISK = 1500.0
DAY_CAP = 3000.0  # the actual sizing decision recorded 2026-09-22, not Round 69's own $2,000 experiment


if __name__ == "__main__":
    print("=== Round 90: does the trader's ORIGINAL TOD/VWAP-Z strategy clear the same bootstrap bar ===")
    print("(Round 89 applied to MES/MYM/M2K/MGC/SIL: n>=30 real trades AND P(true edge>0)>=90%)\n")

    data_path = os.path.join("..", "data", "MNQ_CONTINUOUS.txt")
    mnq_1m = load_1m(data_path)
    print(f"Real data: {data_path}")
    print(f"  {len(mnq_1m):,} bars, {mnq_1m.index.min()} -> {mnq_1m.index.max()} "
          f"({(mnq_1m.index.max() - mnq_1m.index.min()).days} real days)\n")

    atr15_mnq = causal_atr15_lookup(mnq_1m)
    mnq_z = compute_session_vwap_z(mnq_1m)
    _T2 = dt.time(13, 50); _CLOSE = dt.time(16, 0); SEED = 0
    raw = generate_random_entries(mnq_1m, SEED)
    sig_base = build_stop_signals(raw, atr15_mnq)
    t = sig_base["ts"].dt.time
    sig_tod = sig_base[(t >= _T2) & (t < _CLOSE)]
    sig_z = build_zscore_signals(mnq_z, atr15_mnq, 2.5)

    sig_tod_t = sig_tod.copy(); sig_tod_t["risk"] = TOD_RISK; sig_tod_t["source"] = "tod"
    sig_z_t = sig_z.copy(); sig_z_t["risk"] = VWAPZ_RISK; sig_z_t["source"] = "vwapz"
    combined_sig = pd.concat([sig_tod_t, sig_z_t], ignore_index=True).sort_values("ts").reset_index(drop=True)

    trades = resolve_true_risk_with_day_cap(combined_sig, mnq_1m, "MNQ", TRAIL_ATR_MULT, DAY_CAP)
    print(f"Sizing: TOD=${TOD_RISK:,.0f}  VWAP-Z=${VWAPZ_RISK:,.0f}  day_cap=${DAY_CAP:,.0f} "
          f"(the actual 2026-09-22 sizing decision)\n")

    for label, sub in [("ALL (TOD+VWAP-Z combined)", trades),
                        ("TOD only", trades[trades["source"] == "tod"]),
                        ("VWAP-Z only", trades[trades["source"] == "vwapz"])]:
        pnl = sub["pnl"].to_numpy()
        n = len(pnl)
        if n == 0:
            print(f"{label}: no trades.")
            continue
        total = pnl.sum()
        winrate = (pnl > 0).mean()
        expectancy = pnl.mean()
        ci = bootstrap_expectancy_ci(pnl)
        trustworthy = n >= 30 and ci["p_positive"] >= 0.90
        verdict = "PASSES the significance bar" if trustworthy else \
                  ("does NOT pass -- P(edge>0) only " + f"{ci['p_positive']:.1%}")
        print(f"{label}: n={n:,}  win%={winrate*100:.1f}  total=${total:,.2f}  expectancy=${expectancy:.2f}/trade")
        print(f"  Bootstrap 90% CI ({N_BOOTSTRAP:,}x resample of these {n:,} REAL trades): "
              f"[${ci['p05']:.2f}, ${ci['p95']:.2f}], P(true mean > $0)={ci['p_positive']:.1%}")
        print(f"  -> {verdict}\n")

    print("For direct comparison, Round 89's OTE/FVG/MNQ result (60-day BrokerAPI pull): "
          "n=38, P(edge>0)=99.8%, PASSES.")
    print("\nDONE.")
