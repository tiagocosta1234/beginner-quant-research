"""
Round 41: does the "one random entry per day" convention itself cap the MNQ
edge below what's needed for the deadline, independent of per-trade expectancy?
Math check: at Round 39's filtered $58/trade expectancy, reaching the
$19,184.62 gap by pure expectancy needs ~330 trades -- but a once-a-day
strategy only gets ~20-27 trades total in the deadline window. That mismatch,
not the per-trade edge size, may be the real constraint Round 40 exposed.

Test: allow MULTIPLE non-overlapping random entries per day within Round 39's
proven tod_last_third window (13:50-16:00 ET), instead of exactly one. Reuses
validated infrastructure, not reimplemented: generate K candidate random
entries per day (same generate_random_entries mechanics), attach ATR stops
(build_stop_signals, unchanged), filter to the window, then resolve them
SEQUENTIALLY with round30b's resolve_trailing_sequential (already handles
"skip overlapping candidates, only take non-overlapping trades" correctly --
built and proven for a different signal source, reused here for this one).
Direction/timing within the window are still pure random draws -- this does
NOT reintroduce a price-informed entry (Round 20's lesson stands).

Reports OOS trade count and expectancy per K (number of candidate draws/day),
walk-forward per round11's FOLDS, same buffer/costs as every other round.
"""
import os, sys
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, BUFFER, FOLDS, fold_stats
from round19_random_entry import causal_atr15_lookup, build_stop_signals, TRAIL_ATR_MULT
from round30b_sequential_fix import resolve_trailing_sequential

SYMBOL = "MNQ"
import datetime as dt
_T2 = dt.time(13, 50)
_CLOSE = dt.time(16, 0)
SEEDS = list(range(8))
K_VALUES = [1, 3, 5, 8, 12, 20]
RISK_SWEEP = [100, 150, 200, 250, 300, 400]


def generate_multi_random_entries(df1m, seed, k):
    """K uniformly-random candidate entry timestamps per calendar day, restricted
    to the tod_last_third window -- same random-direction-per-entry convention as
    round19's generate_random_entries, just K draws instead of 1, and pre-filtered
    to the proven window so every candidate is inside it (not filtered after)."""
    rng = np.random.default_rng(seed)
    rows = []
    win_df = df1m[(df1m.index.time >= _T2) & (df1m.index.time < _CLOSE)]
    for day, day_idx in win_df.groupby(win_df.index.date).groups.items():
        day_idx = list(day_idx)
        if len(day_idx) < 5:
            continue
        n_draw = min(k, len(day_idx))
        chosen = rng.choice(len(day_idx), size=n_draw, replace=False)
        for c in chosen:
            ts = day_idx[c]
            direction = 1 if rng.random() < 0.5 else -1
            entry_px = df1m.loc[ts, "close"]
            rows.append((ts, direction, entry_px))
    raw = pd.DataFrame(rows, columns=["ts", "direction", "entry"]).sort_values("ts").reset_index(drop=True)
    return raw


def pooled_stats(trades_list):
    all_trades = [t for t in trades_list if t is not None and len(t) > 0]
    if not all_trades:
        return None
    pooled = pd.concat(all_trades, ignore_index=True)
    n = len(pooled)
    mean_pnl = pooled["pnl"].mean()
    if n > 1:
        t_stat, p_val = stats.ttest_1samp(pooled["pnl"].values, popmean=0.0)
    else:
        t_stat, p_val = float("nan"), float("nan")
    worst_dd = 0.0
    n_breach = 0
    for t in all_trades:
        st = fold_stats(t)
        if st["breach"]:
            n_breach += 1
        worst_dd = max(worst_dd, st["maxdd"])
    return dict(n=n, expectancy=mean_pnl, t_stat=t_stat, p_val=p_val,
                worst_dd=worst_dd, n_breach=n_breach, n_windows=len(all_trades),
                trades_per_day=n / max(1, pooled["ts"].dt.date.nunique()))


if __name__ == "__main__":
    mnq_path = os.path.join("..", "data", "MNQ_CONTINUOUS.txt")
    df1m = load_1m(mnq_path)
    atr15 = causal_atr15_lookup(df1m)
    print(f"{SYMBOL}: {len(df1m)} bars {df1m.index.min()} -> {df1m.index.max()}", flush=True)

    for k in K_VALUES:
        for risk in RISK_SWEEP:
            trades_all = []
            for seed in SEEDS:
                raw = generate_multi_random_entries(df1m, seed, k)
                if len(raw) == 0:
                    continue
                sig = build_stop_signals(raw, atr15)
                for train_end, test_end in FOLDS:
                    test_sig = sig[(sig["ts"] >= train_end) & (sig["ts"] < test_end)]
                    if len(test_sig) == 0:
                        continue
                    test_df1m = df1m[(df1m.index >= train_end) & (df1m.index < test_end)]
                    trades, _ = resolve_trailing_sequential(test_sig, test_df1m, SYMBOL, risk, TRAIL_ATR_MULT)
                    if len(trades) > 0:
                        trades_all.append(trades)
            st = pooled_stats(trades_all)
            if st is None:
                print(f"K={k:>3} risk=${risk}: no trades", flush=True)
                continue
            print(f"K={k:>3} risk=${risk:>4}  n={st['n']:>5} trades/day={st['trades_per_day']:.2f}  "
                  f"exp=${st['expectancy']:>7.2f}  t={st['t_stat']:>6.2f} p={st['p_val']:.2e}  "
                  f"worst_dd=${st['worst_dd']:>8.2f}  breach={st['n_breach']}/{st['n_windows']}", flush=True)

    print("\nDONE.", flush=True)
