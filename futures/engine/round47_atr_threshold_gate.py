"""
Round 47: intraday 15m ATR(14) threshold gate on top of the confirmed
tod_last_third MNQ edge -- "disable trading if ATR is below X" (avoid
low-volatility chop), using the SAME causal ATR already computed for stop
sizing, not a separate daily-realized-vol percentile (that was Round 39's
`daily_vol_regime` candidate, already tried and NOT what dominated selection
there -- this tests the more literal "current ATR level" framing directly).
Train-only threshold selection per fold (percentile-based grid, so it adapts
to each fold's own vol regime rather than a fixed dollar/point cutoff), tested
OOS unchanged.
"""
import os, sys
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, BUFFER, FOLDS
from round19_random_entry import causal_atr15_lookup, generate_random_entries, build_stop_signals, resolve_trailing, TRAIL_ATR_MULT, SEEDS

SYMBOL = "MNQ"
import datetime as dt
_T2 = dt.time(13, 50)
_CLOSE = dt.time(16, 0)
PCTL_GRID = [0, 25, 40, 50, 60, 75]  # "0" = no filter, the baseline candidate
SELECT_RISK = 200
MIN_TRAIN = 20


def run():
    mnq_path = os.path.join("..", "data", "MNQ_CONTINUOUS.txt")
    df1m = load_1m(mnq_path)
    atr15 = causal_atr15_lookup(df1m)
    print(f"MNQ: {len(df1m)} bars", flush=True)

    all_oos = []
    chosen_log = []
    for seed in SEEDS:
        raw = generate_random_entries(df1m, seed)
        sig = build_stop_signals(raw, atr15)
        sig = sig.copy()
        sig["atr"] = (sig["entry"] - sig["stop"]).abs()  # STOP_ATR_MULT=1.0, so this IS the 15m ATR(14) at entry
        t = sig["ts"].dt.time
        sig = sig[(t >= _T2) & (t < _CLOSE)].reset_index(drop=True)

        for train_end, test_end in FOLDS:
            train_sig = sig[sig["ts"] < train_end]
            test_sig = sig[(sig["ts"] >= train_end) & (sig["ts"] < test_end)]
            if len(train_sig) < MIN_TRAIN or len(test_sig) == 0:
                continue
            best_pctl, best_exp = 0, -1e18
            for pctl in PCTL_GRID:
                thresh = np.percentile(train_sig["atr"], pctl) if pctl > 0 else -1
                tf = train_sig[train_sig["atr"] >= thresh]
                if len(tf) < MIN_TRAIN:
                    continue
                tr = resolve_trailing(tf, df1m, SYMBOL, SELECT_RISK, TRAIL_ATR_MULT)
                if len(tr) == 0:
                    continue
                exp = tr["pnl"].mean()
                if exp > best_exp:
                    best_exp, best_pctl = exp, pctl
            chosen_log.append((seed, train_end, best_pctl, best_exp))
            thresh = np.percentile(train_sig["atr"], best_pctl) if best_pctl > 0 else -1
            test_f = test_sig[test_sig["atr"] >= thresh]
            if len(test_f) == 0:
                continue
            oos = resolve_trailing(test_f, df1m, SYMBOL, SELECT_RISK, TRAIL_ATR_MULT)
            if len(oos) > 0:
                all_oos.append(oos)

    print("Selected ATR percentile threshold (train-only):", flush=True)
    from collections import Counter
    counts = Counter(p for _, _, p, _ in chosen_log)
    for p, c in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  pctl={p}: chosen {c}/{len(chosen_log)} ({100*c/len(chosen_log):.1f}%)", flush=True)

    if not all_oos:
        print("No OOS trades.", flush=True)
        return
    pooled = pd.concat(all_oos, ignore_index=True)
    t_stat, p_val = stats.ttest_1samp(pooled["pnl"].values, popmean=0.0)
    print(f"\nOOS (ATR-threshold gated, on top of tod_last_third): n={len(pooled)} "
          f"exp=${pooled['pnl'].mean():.2f} t={t_stat:.2f} p={p_val:.2e}", flush=True)
    print("vs. Round 39 tod_last_third-only baseline: n=2074 exp=$58.06 t=3.83(seed-level)", flush=True)


if __name__ == "__main__":
    run()
    print("\nDONE.", flush=True)
