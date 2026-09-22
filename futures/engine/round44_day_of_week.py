"""
Round 44: day-of-week seasonality -- genuinely untried anywhere in this repo's
~100+ prior variants (checked docs/EDGE_VALIDATION_RESULTS.md's running total;
no round filters by calendar weekday). Tests whether restricting Round 39's
proven tod_last_third-filtered MNQ edge (and, separately, MGC's swing-bounce
edge) to specific weekdays concentrates it further. Day-of-week is trivially
known in advance -- zero look-ahead risk. Same train-only/OOS walk-forward
discipline as every other round tonight.
"""
import os, sys
import datetime as dt
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, resample_causal, BUFFER, FOLDS, fold_stats
from round19_random_entry import causal_atr15_lookup, generate_random_entries, build_stop_signals, resolve_trailing, TRAIL_ATR_MULT, SEEDS
from round30_support_resistance import build_swing_touch_signals
from round30b_sequential_fix import resolve_trailing_sequential

_T2 = dt.time(13, 50)
_CLOSE = dt.time(16, 0)
DOW_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri"]
SELECT_RISK_MNQ = 200
SELECT_RISK_MGC = 600
MIN_TRAIN = 20


def select_best_dow(train_trades_by_dow):
    """Rank single weekdays AND the best 2-weekday/3-weekday combos by train
    expectancy (min MIN_TRAIN trades). Returns (best_dow_set, score)."""
    from itertools import combinations
    candidates = {}
    for d in range(5):
        candidates[frozenset([d])] = train_trades_by_dow.get(d, pd.DataFrame())
    for size in (2, 3):
        for combo in combinations(range(5), size):
            frames = [train_trades_by_dow.get(d) for d in combo if train_trades_by_dow.get(d) is not None]
            frames = [f for f in frames if len(f) > 0]
            if frames:
                candidates[frozenset(combo)] = pd.concat(frames, ignore_index=True)
    best_set, best_exp, best_n = None, -1e18, 0
    for dow_set, df in candidates.items():
        if len(df) < MIN_TRAIN:
            continue
        exp = df["pnl"].mean()
        if exp > best_exp:
            best_exp, best_set, best_n = exp, dow_set, len(df)
    return best_set, best_exp, best_n


def run_mnq():
    print("=" * 78 + "\nMNQ (tod_last_third-filtered) x day-of-week\n" + "=" * 78, flush=True)
    df1m = load_1m(os.path.join("..", "data", "MNQ_CONTINUOUS.txt"))
    atr15 = causal_atr15_lookup(df1m)

    all_oos = []
    chosen_log = []
    for seed in SEEDS:
        raw = generate_random_entries(df1m, seed)
        sig = build_stop_signals(raw, atr15)
        t = sig["ts"].dt.time
        sig = sig[(t >= _T2) & (t < _CLOSE)]
        for train_end, test_end in FOLDS:
            train_sig = sig[sig["ts"] < train_end]
            test_sig = sig[(sig["ts"] >= train_end) & (sig["ts"] < test_end)]
            if len(train_sig) < MIN_TRAIN or len(test_sig) == 0:
                continue
            train_trades = resolve_trailing(train_sig, df1m, "MNQ", SELECT_RISK_MNQ, TRAIL_ATR_MULT)
            if len(train_trades) == 0:
                continue
            train_trades["dow"] = pd.to_datetime(train_trades["ts"]).dt.dayofweek
            by_dow = {d: g for d, g in train_trades.groupby("dow")}
            best_set, best_exp, best_n = select_best_dow(by_dow)
            if best_set is None:
                continue
            chosen_log.append((seed, train_end, best_set, best_exp, best_n))
            test_dow = pd.to_datetime(test_sig["ts"]).dt.dayofweek
            test_f = test_sig[test_dow.isin(best_set)]
            if len(test_f) == 0:
                continue
            oos_trades = resolve_trailing(test_f, df1m, "MNQ", SELECT_RISK_MNQ, TRAIL_ATR_MULT)
            if len(oos_trades) > 0:
                all_oos.append(oos_trades)

    print("Selected day-of-week sets (train-only):", flush=True)
    for seed, te, dset, exp, n in chosen_log:
        names = "+".join(DOW_NAMES[d] for d in sorted(dset))
        print(f"  seed={seed} train_end={te}: {names} (train_exp=${exp:.2f}, n={n})", flush=True)

    if not all_oos:
        print("MNQ: no OOS trades survive any selection.", flush=True)
        return
    pooled = pd.concat(all_oos, ignore_index=True)
    t_stat, p_val = stats.ttest_1samp(pooled["pnl"].values, popmean=0.0)
    print(f"\nMNQ OOS (day-of-week filtered, on top of tod_last_third): n={len(pooled)} "
          f"exp=${pooled['pnl'].mean():.2f} t={t_stat:.2f} p={p_val:.2e}", flush=True)
    print(f"vs. Round 39 tod_last_third-only baseline: n=2074 exp=$58.06 t=3.83(seed-level)", flush=True)


def run_mgc():
    print("\n" + "=" * 78 + "\nMGC (swing S/R bounce) x day-of-week\n" + "=" * 78, flush=True)
    df1m = load_1m(os.path.join("..", "data", "MGC_CONTINUOUS.txt"))
    h15 = resample_causal(df1m, "15min")
    atr15 = causal_atr15_lookup(df1m)
    sig = build_swing_touch_signals(df1m, h15, atr15, 3, 0.50)  # deployed params

    all_oos = []
    chosen_log = []
    for train_end, test_end in FOLDS:
        train_sig = sig[sig["ts"] < train_end]
        test_sig = sig[(sig["ts"] >= train_end) & (sig["ts"] < test_end)]
        if len(train_sig) < MIN_TRAIN or len(test_sig) == 0:
            continue
        train_trades, _ = resolve_trailing_sequential(train_sig, df1m, "MGC", SELECT_RISK_MGC, TRAIL_ATR_MULT)
        if len(train_trades) == 0:
            continue
        train_trades["dow"] = pd.to_datetime(train_trades["ts"]).dt.dayofweek
        by_dow = {d: g for d, g in train_trades.groupby("dow")}
        best_set, best_exp, best_n = select_best_dow(by_dow)
        if best_set is None:
            continue
        chosen_log.append((train_end, best_set, best_exp, best_n))
        test_dow = pd.to_datetime(test_sig["ts"]).dt.dayofweek
        test_f = test_sig[test_dow.isin(best_set)]
        if len(test_f) == 0:
            continue
        oos_trades, _ = resolve_trailing_sequential(test_f, df1m, "MGC", SELECT_RISK_MGC, TRAIL_ATR_MULT)
        if len(oos_trades) > 0:
            all_oos.append(oos_trades)

    print("Selected day-of-week sets (train-only):", flush=True)
    for te, dset, exp, n in chosen_log:
        names = "+".join(DOW_NAMES[d] for d in sorted(dset))
        print(f"  train_end={te}: {names} (train_exp=${exp:.2f}, n={n})", flush=True)

    if not all_oos:
        print("MGC: no OOS trades survive any selection.", flush=True)
        return
    pooled = pd.concat(all_oos, ignore_index=True)
    t_stat, p_val = stats.ttest_1samp(pooled["pnl"].values, popmean=0.0)
    print(f"\nMGC OOS (day-of-week filtered): n={len(pooled)} exp=${pooled['pnl'].mean():.2f} "
          f"t={t_stat:.2f} p={p_val:.2e}", flush=True)


if __name__ == "__main__":
    run_mnq()
    run_mgc()
    print("\nDONE.", flush=True)
