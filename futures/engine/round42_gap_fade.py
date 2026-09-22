"""
Round 42: gap FADE (inverse of Round 39's gap continuation) -- Round 39 found
gap-continuation is a CONFIRMED, statistically significant LOSER on MGC
(t=-3.05, n=365, consistent $50-$2000/trade). A confirmed loser in one
direction is direct, principled motivation to test the opposite direction, not
a cherry-pick -- same signal, same walk-forward discipline, same exit, only
the direction sign flipped. Reuses round39_gap_open_drive.py's session
detection, gap computation, and walk-forward machinery unchanged; only
build_gap_signals is redefined here with direction flipped.
"""
import os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, BUFFER
from round19_random_entry import causal_atr15_lookup, attach_atr, resolve_trailing, STOP_ATR_MULT, TRAIL_ATR_MULT
from round30b_sequential_fix import resolve_trailing_sequential
from round39_gap_open_drive import (
    build_rth_sessions, build_gap_detected_sessions, compute_gaps,
    walk_forward_gap, fold_summary, pooled_stats, buffer_safe_sweep,
    RISK_LEVELS,
)


def build_gap_signals_fade(sess, atr_series):
    """Identical to round39_gap_open_drive.build_gap_signals except direction is
    FLIPPED: fade the gap (short a gap-up, long a gap-down) instead of trading
    with it. Everything else -- fill price (opening bar's own close), stop
    distance, causal ATR lookup -- unchanged."""
    tmp = sess.rename(columns={"open_ts": "ts"})
    tmp = attach_atr(tmp, atr_series)
    tmp = tmp[tmp["atr"] > 0].copy()
    tmp["gap_atr"] = tmp["gap"].abs() / tmp["atr"]
    tmp["direction"] = -np.sign(tmp["gap"]).astype(int)  # <-- the only change from Round 39
    tmp = tmp[tmp["direction"] != 0].copy()
    stop_dist = STOP_ATR_MULT * tmp["atr"]
    tmp["entry"] = tmp["open_bar_close"]
    tmp["stop"] = np.where(tmp["direction"] == 1, tmp["entry"] - stop_dist, tmp["entry"] + stop_dist)
    return tmp[["ts", "direction", "entry", "stop", "gap", "gap_atr"]].reset_index(drop=True)


def run_symbol_fade(symbol, path, session_builder):
    print(f"\n{'='*78}\n{symbol} FADE: loading {path}", flush=True)
    df1m = load_1m(path)
    atr15 = causal_atr15_lookup(df1m)
    sess = session_builder(df1m)
    sess = compute_gaps(sess)
    sig_all = build_gap_signals_fade(sess, atr15)
    print(f"{symbol}: {len(sig_all)} fade signals, median |gap| in ATR units = {sig_all['gap_atr'].median():.2f}", flush=True)

    diag, skipped = resolve_trailing_sequential(sig_all, df1m, symbol, 400, TRAIL_ATR_MULT)
    print(f"{symbol}: diagnostic unfiltered @ $400 -- n={len(diag)} exp=${diag['pnl'].mean():.2f} "
          f"(skipped_overlap={skipped})" if len(diag) else f"{symbol}: diagnostic empty", flush=True)

    per_risk = {}
    for risk in RISK_LEVELS:
        fold_rows = walk_forward_gap(sig_all, df1m, symbol, risk)
        fs = fold_summary(fold_rows)
        pooled = pooled_stats(fold_rows)
        per_risk[risk] = dict(fold_summary=fs, pooled=pooled)
        print(f"  {symbol} risk=${risk}: POOLED OOS n={pooled['n']} exp=${pooled['exp']:.2f} "
              f"t={pooled['tstat']:.2f} win%={pooled['winrate']:.1%} "
              f"worst_fold_maxdd=${fs['maxdd'].max() if len(fs) else 0:.2f} "
              f"breach={int(fs['breach'].sum()) if len(fs) else 0}/{len(fs)}", flush=True)
    return sig_all, per_risk


if __name__ == "__main__":
    engine_dir = os.path.dirname(__file__)
    data_dir = os.path.join(engine_dir, "..", "data")

    mnq_sig, mnq_results = run_symbol_fade("MNQ", os.path.join(data_dir, "MNQ_CONTINUOUS.txt"), build_rth_sessions)
    mgc_sig, mgc_results = run_symbol_fade("MGC", os.path.join(data_dir, "MGC_CONTINUOUS.txt"), build_gap_detected_sessions)

    print(f"\n{'#'*78}\nBUFFER-SAFE SWEEP (only meaningful if an edge showed above)\n{'#'*78}", flush=True)
    mnq_df1m = load_1m(os.path.join(data_dir, "MNQ_CONTINUOUS.txt"))
    mgc_df1m = load_1m(os.path.join(data_dir, "MGC_CONTINUOUS.txt"))
    fine_grid = list(range(50, 1201, 50))

    print("\nMNQ fade sweep:", flush=True)
    mnq_sweep = buffer_safe_sweep("MNQ", mnq_sig, mnq_df1m, fine_grid)
    print("\nMGC fade sweep:", flush=True)
    mgc_sweep = buffer_safe_sweep("MGC", mgc_sig, mgc_df1m, fine_grid)

    for symbol, sweep in [("MNQ", mnq_sweep), ("MGC", mgc_sweep)]:
        safe = sweep[~sweep["breach"]]
        if len(safe) > 0:
            best = safe.loc[safe["risk"].idxmax()]
            print(f"\n{symbol}: largest buffer-safe risk/trade = ${best['risk']:.0f} "
                  f"(worst_fold_maxdd=${best['worst_fold_maxdd']:.2f}, pooled_exp=${best['pooled_exp']:.2f}, "
                  f"t={best['pooled_tstat']:.2f})", flush=True)
        else:
            print(f"\n{symbol}: no buffer-safe size found (every tested risk breaches)", flush=True)

    print("\nDONE.", flush=True)
