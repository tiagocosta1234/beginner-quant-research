"""
Round 46: higher-timeframe (4H/Daily) FVG confluence as a GATE on top of the
one already-confirmed real edge (Round 39's tod_last_third-filtered MNQ),
not as the primary entry signal. This is meaningfully different from Rounds
11-13/20's prior FVG work: those used FVG position AS the entry trigger
(price-informed, directional) and Round 20 found that made things worse than
random entry. This instead asks: does requiring the random entry to ALSO
coincide with price sitting inside a recent, still-active 4H or Daily FVG zone
(a "premium/discount" liquidity-draw confluence check) concentrate the
already-random-direction edge, the same question Round 39 asked of
time-of-day and volatility-regime filters.

Zone is "active" from its causal confirmation until EITHER price later closes
fully through it (filled) or `MAX_ZONE_AGE_BARS` (in the zone's own timeframe)
elapses, whichever first -- a zone nobody has returned to in a long time is
dropped rather than treated as still live.
"""
import os, sys
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, resample_causal, detect_fvgs, BUFFER, FOLDS
from round19_random_entry import causal_atr15_lookup, generate_random_entries, build_stop_signals, resolve_trailing, TRAIL_ATR_MULT, SEEDS

SYMBOL = "MNQ"
import datetime as dt
_T2 = dt.time(13, 50)
_CLOSE = dt.time(16, 0)
MAX_ZONE_AGE_BARS = 30  # in the zone's OWN timeframe (30 4H bars = ~20 sessions; 30 daily bars = ~6 weeks)
RISK_SWEEP = [100, 150, 200, 250, 300, 400]


def active_zones_mask(entry_ts, entry_price, htf, fvgs, max_age_bars):
    """For each entry, check if price sits inside any FVG zone confirmed strictly
    before entry_ts, not yet filled by a later HTF close, and not older than
    max_age_bars (in HTF bars). Vectorized-ish via per-entry search (signal counts
    are modest, a few thousand -- a plain loop is fine and easiest to verify correct)."""
    htf_idx = htf.index.values
    htf_close = htf["close"].values
    out = np.zeros(len(entry_ts), dtype=bool)
    fvg_confirm = fvgs["confirm_ts"].values
    fvg_lo = fvgs["zone_lo"].values
    fvg_hi = fvgs["zone_hi"].values
    fvg_dir = fvgs["direction"].values
    for k in range(len(entry_ts)):
        ts = entry_ts[k]
        px = entry_price[k]
        cutoff_pos = np.searchsorted(htf_idx, np.datetime64(ts), side="right")
        oldest_ts = htf_idx[max(0, cutoff_pos - max_age_bars)] if cutoff_pos > 0 else htf_idx[0]
        eligible = (fvg_confirm < np.datetime64(ts)) & (fvg_confirm >= oldest_ts)
        if not eligible.any():
            continue
        lo_e = fvg_lo[eligible]; hi_e = fvg_hi[eligible]; conf_e = fvg_confirm[eligible]; dir_e = fvg_dir[eligible]
        in_zone = (px >= lo_e) & (px <= hi_e)
        if not in_zone.any():
            continue
        # check not yet "filled": no HTF close between confirm and entry has closed
        # fully through the zone in the direction that would invalidate it
        any_active = False
        for j in np.where(in_zone)[0]:
            conf_pos = np.searchsorted(htf_idx, conf_e[j], side="right")
            entry_pos = np.searchsorted(htf_idx, np.datetime64(ts), side="right")
            between = htf_close[conf_pos:entry_pos]
            if dir_e[j] == 1:  # bullish zone filled if a close goes back below zone_lo
                filled = (between < lo_e[j]).any()
            else:
                filled = (between > hi_e[j]).any()
            if not filled:
                any_active = True
                break
        out[k] = any_active
    return out


if __name__ == "__main__":
    mnq_path = os.path.join("..", "data", "MNQ_CONTINUOUS.txt")
    df1m = load_1m(mnq_path)
    atr15 = causal_atr15_lookup(df1m)
    print(f"MNQ: {len(df1m)} bars", flush=True)

    h4 = resample_causal(df1m, "4h")
    hD = resample_causal(df1m, "1D")
    fvg_4h = detect_fvgs(h4)
    fvg_D = detect_fvgs(hD)
    print(f"4H FVGs: {len(fvg_4h)}, Daily FVGs: {len(fvg_D)}", flush=True)

    all_oos_gated = []
    all_oos_base = []
    for seed in SEEDS:
        raw = generate_random_entries(df1m, seed)
        sig = build_stop_signals(raw, atr15)
        t = sig["ts"].dt.time
        sig = sig[(t >= _T2) & (t < _CLOSE)].reset_index(drop=True)  # tod_last_third baseline

        gate_4h = active_zones_mask(sig["ts"].values, sig["entry"].values, h4, fvg_4h, MAX_ZONE_AGE_BARS)
        gate_D = active_zones_mask(sig["ts"].values, sig["entry"].values, hD, fvg_D, MAX_ZONE_AGE_BARS)
        sig_gated = sig[gate_4h | gate_D].reset_index(drop=True)

        for train_end, test_end in FOLDS:
            test_base = sig[(sig["ts"] >= train_end) & (sig["ts"] < test_end)]
            test_gated = sig_gated[(sig_gated["ts"] >= train_end) & (sig_gated["ts"] < test_end)]
            if len(test_base) > 0:
                tb = resolve_trailing(test_base, df1m, SYMBOL, 200, TRAIL_ATR_MULT)
                if len(tb) > 0:
                    all_oos_base.append(tb)
            if len(test_gated) > 0:
                tg = resolve_trailing(test_gated, df1m, SYMBOL, 200, TRAIL_ATR_MULT)
                if len(tg) > 0:
                    all_oos_gated.append(tg)
        print(f"seed={seed}: baseline sig={len(sig)}, gated sig={len(sig_gated)} "
              f"({100*len(sig_gated)/max(1,len(sig)):.1f}% pass gate)", flush=True)

    print(f"\n{'='*78}\nRESULTS @ $200 risk (reference, sweep below)\n{'='*78}", flush=True)
    base = pd.concat(all_oos_base, ignore_index=True) if all_oos_base else pd.DataFrame()
    gated = pd.concat(all_oos_gated, ignore_index=True) if all_oos_gated else pd.DataFrame()
    for label, df in [("BASELINE (tod_last_third only)", base), ("GATED (+ HTF FVG confluence)", gated)]:
        if len(df) == 0:
            print(f"{label}: no trades")
            continue
        t_stat, p_val = stats.ttest_1samp(df["pnl"].values, popmean=0.0)
        print(f"{label}: n={len(df)} exp=${df['pnl'].mean():.2f} t={t_stat:.2f} p={p_val:.2e}", flush=True)

    print("\nDONE.", flush=True)
