"""
Round 49: VWAP Z-score mean reversion -- pure statistical mechanics, distinct
from everything tried (this repo's prior "VWAP" work, per the existing_audit_docs
search earlier tonight, was part of the ResearchBot family found to have
no edge on retest; this is a specifically Z-score/mean-reversion framing, not a
breakout or bias filter, and untested standalone here). Daily session VWAP
(resets each session, cumulative typical-price*volume / cumulative volume, 100%
causal by construction -- only uses bars up to and including the current one),
Z-scored against its own rolling deviation. Entry only when price is >=2.5 SD
from VWAP AND the current bar's close reverses vs. the prior bar (a simple,
disclosed proxy for "1-minute market structure shift" -- a full MSS detector
was out of scope for tonight). Exit: same validated ATR-trailing mechanics as
every other round (a fixed return-to-1SD target was NOT implemented -- also
disclosed -- to stay comparable and fast to build/verify under time pressure).
"""
import os, sys
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, BUFFER, FOLDS, fold_stats
from round19_random_entry import causal_atr15_lookup, attach_atr, STOP_ATR_MULT, TRAIL_ATR_MULT
from round30b_sequential_fix import resolve_trailing_sequential

Z_GRID = [2.0, 2.5, 3.0, 3.5]
RISK_SWEEP = [100, 200, 300, 400, 600]
MIN_TRAIN = 15
ZSTD_WINDOW = 60  # bars, rolling std of (price - vwap) within session


def compute_session_vwap_z(df1m):
    dates = pd.Series(df1m.index.date, index=df1m.index)
    tp = (df1m["high"] + df1m["low"] + df1m["close"]) / 3.0
    pv = tp * df1m["vol"]
    cum_pv = pv.groupby(dates).cumsum()
    cum_v = df1m["vol"].groupby(dates).cumsum().replace(0, np.nan)
    vwap = cum_pv / cum_v
    dev = df1m["close"] - vwap
    z = dev.groupby(dates).transform(lambda s: s / s.rolling(ZSTD_WINDOW, min_periods=20).std())
    out = df1m.copy()
    out["vwap"] = vwap
    out["z"] = z
    return out


def build_zscore_signals(df1m_z, atr15, z_thresh):
    z = df1m_z["z"].values
    cl = df1m_z["close"].values
    ts = df1m_z.index.values
    rows = []
    for i in range(1, len(df1m_z)):
        if np.isnan(z[i]):
            continue
        if z[i] <= -z_thresh and cl[i] > cl[i - 1]:
            rows.append((ts[i], 1, cl[i]))
        elif z[i] >= z_thresh and cl[i] < cl[i - 1]:
            rows.append((ts[i], -1, cl[i]))
    sig = pd.DataFrame(rows, columns=["ts", "direction", "entry"])
    if len(sig) == 0:
        return sig
    sig = attach_atr(sig, atr15)
    sig = sig[sig["atr"] > 0].copy()
    stop_dist = STOP_ATR_MULT * sig["atr"]
    sig["stop"] = np.where(sig["direction"] == 1, sig["entry"] - stop_dist, sig["entry"] + stop_dist)
    return sig[["ts", "direction", "entry", "stop"]].reset_index(drop=True)


def run_symbol(symbol, path):
    print(f"\n{'='*78}\n{symbol} VWAP Z-score mean reversion\n{'='*78}", flush=True)
    df1m = load_1m(path)
    atr15 = causal_atr15_lookup(df1m)
    df1m_z = compute_session_vwap_z(df1m)
    print(f"{symbol}: {len(df1m)} bars, z computed ({df1m_z['z'].notna().sum()} valid)", flush=True)

    all_oos = []
    chosen_log = []
    for train_end, test_end in FOLDS:
        train_z = df1m_z[df1m_z.index < train_end]
        best = None
        for z_thresh in Z_GRID:
            sig = build_zscore_signals(train_z, atr15, z_thresh)
            if len(sig) < MIN_TRAIN:
                continue
            tr, _ = resolve_trailing_sequential(sig, df1m, symbol, 300, TRAIL_ATR_MULT)
            if len(tr) < MIN_TRAIN:
                continue
            exp = tr["pnl"].mean()
            if best is None or exp > best[0]:
                best = (exp, z_thresh, len(tr))
        if best is None:
            continue
        exp, z_thresh, ntrain = best
        chosen_log.append((train_end, z_thresh, exp, ntrain))
        test_z = df1m_z[(df1m_z.index >= train_end) & (df1m_z.index < test_end)]
        test_sig = build_zscore_signals(test_z, atr15, z_thresh)
        if len(test_sig) == 0:
            continue
        te, _ = resolve_trailing_sequential(test_sig, df1m, symbol, 300, TRAIL_ATR_MULT)
        if len(te) > 0:
            all_oos.append(te)

    print("Selected Z-threshold, train-only:", flush=True)
    for te, z_thresh, exp, n in chosen_log:
        print(f"  {te}: z>={z_thresh} (train_exp=${exp:.2f}, n={n})", flush=True)

    if not all_oos:
        print(f"{symbol}: no OOS trades.", flush=True)
        return
    pooled = pd.concat(all_oos, ignore_index=True)
    t_stat, p_val = stats.ttest_1samp(pooled["pnl"].values, popmean=0.0)
    print(f"\n{symbol} OOS @ $300 risk: n={len(pooled)} exp=${pooled['pnl'].mean():.2f} "
          f"t={t_stat:.2f} p={p_val:.2e}", flush=True)

    print(f"\n{symbol} risk sweep (same selected z-threshold per fold):", flush=True)
    for risk in RISK_SWEEP:
        oos_r = []
        for te, z_thresh, _, _ in chosen_log:
            test_end = [f[1] for f in FOLDS if f[0] == te][0]
            test_z = df1m_z[(df1m_z.index >= te) & (df1m_z.index < test_end)]
            test_sig = build_zscore_signals(test_z, atr15, z_thresh)
            if len(test_sig) == 0:
                continue
            tr, _ = resolve_trailing_sequential(test_sig, df1m, symbol, risk, TRAIL_ATR_MULT)
            if len(tr) > 0:
                oos_r.append(tr)
        if not oos_r:
            continue
        pooled_r = pd.concat(oos_r, ignore_index=True)
        worst_dd = max(fold_stats(t)["maxdd"] for t in oos_r)
        n_breach = sum(1 for t in oos_r if fold_stats(t)["breach"])
        t_r, p_r = stats.ttest_1samp(pooled_r["pnl"].values, popmean=0.0)
        print(f"  risk=${risk}: n={len(pooled_r)} exp=${pooled_r['pnl'].mean():.2f} t={t_r:.2f} "
              f"worst_dd=${worst_dd:.2f} breach={n_breach}/{len(oos_r)}", flush=True)


if __name__ == "__main__":
    run_symbol("MNQ", os.path.join("..", "data", "MNQ_CONTINUOUS.txt"))
    run_symbol("MGC", os.path.join("..", "data", "MGC_CONTINUOUS.txt"))
    print("\nDONE.", flush=True)
