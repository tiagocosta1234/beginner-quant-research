"""
Round 51: time-decay exit -- applies to BOTH tonight's confirmed real MNQ
edges (Round 39 tod_last_third, Round 49 VWAP Z-score). Instead of holding
until the ATR-trailing stop or max_hold_bars, liquidate at market if the
trade isn't showing at least min_profit_frac * initial_stop_distance of
unrealized profit by exactly decay_bars bars after entry -- the premise is
that a real edge shows up fast; a trade still flat or against you N bars in
has already told you the setup isn't playing out. Train-only grid search
(decay_bars x min_profit_frac) per fold, tested OOS unchanged, same walk-
forward discipline as everything else tonight.
"""
import os, sys
import datetime as dt
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, POINT_VALUE, TICK_SIZE, COMMISSION_RT, BUFFER, FOLDS, fold_stats
from round19_random_entry import causal_atr15_lookup, generate_random_entries, build_stop_signals, TRAIL_ATR_MULT, SEEDS
from round49_vwap_zscore import compute_session_vwap_z, build_zscore_signals

SYMBOL = "MNQ"
_T2 = dt.time(13, 50)
_CLOSE = dt.time(16, 0)
Z_THRESH = 2.5
DECAY_GRID = [3, 5, 10, 20, 40]
MIN_PROFIT_FRAC_GRID = [0.0, 0.25, 0.5]  # 0.0 = "just needs to not be negative"
RISK = 200
MIN_TRAIN = 20


def resolve_time_decay(sig_df, df1m, symbol, risk_dollar, trail_mult, decay_bars, min_profit_frac, max_hold_bars=390):
    pv = POINT_VALUE[symbol]; tick = TICK_SIZE[symbol]
    slip_dollars_rt = 2 * tick * pv
    ts = df1m.index.values; hi = df1m["high"].values; lo = df1m["low"].values; cl = df1m["close"].values
    n = len(df1m)
    results = []
    next_free_pos = 0
    sig_df = sig_df.sort_values("ts").reset_index(drop=True)
    for r in sig_df.itertuples(index=False):
        pos = np.searchsorted(ts, np.datetime64(r.ts), side="right")
        if pos >= n or pos < next_free_pos:
            continue
        init_dist = abs(r.entry - r.stop)
        if init_dist <= 0:
            continue
        trail_dist = trail_mult * init_dist
        contracts = max(1, int(risk_dollar // (init_dist * pv)))
        commission = COMMISSION_RT * contracts
        end_pos = min(pos + max_hold_bars, n - 1)
        decay_pos = min(pos + decay_bars, end_pos)
        cur_stop = r.entry - trail_dist if r.direction == 1 else r.entry + trail_dist
        best = r.entry; exit_px = None; outcome = "timeout"; exit_i = end_pos
        for i in range(pos, end_pos + 1):
            bar_hi, bar_lo = hi[i], lo[i]
            if r.direction == 1:
                if bar_lo <= cur_stop:
                    exit_px = cur_stop; outcome = "trail_stop"; exit_i = i; break
                best = max(best, bar_hi); cur_stop = max(cur_stop, best - trail_dist)
            else:
                if bar_hi >= cur_stop:
                    exit_px = cur_stop; outcome = "trail_stop"; exit_i = i; break
                best = min(best, bar_lo); cur_stop = min(cur_stop, best + trail_dist)
            if i == decay_pos and decay_pos < end_pos:
                cur_price = cl[i]
                unrealized = (cur_price - r.entry) if r.direction == 1 else (r.entry - cur_price)
                if unrealized < min_profit_frac * init_dist:
                    exit_px = cur_price; outcome = "time_decay"; exit_i = i; break
        if exit_px is None:
            exit_px = cl[end_pos]; outcome = "session_flatten"; exit_i = end_pos
        move = (exit_px - r.entry) if r.direction == 1 else (r.entry - exit_px)
        pnl = move * pv * contracts - commission - slip_dollars_rt * contracts
        results.append((r.ts, pnl, outcome))
        next_free_pos = exit_i + 1
    return pd.DataFrame(results, columns=["ts", "pnl", "outcome"])


def run(label, sig_all):
    print(f"\n{'='*78}\n{label}\n{'='*78}", flush=True)
    all_oos = []
    chosen_log = []
    for train_end, test_end in FOLDS:
        train_sig = sig_all[sig_all["ts"] < train_end]
        test_sig = sig_all[(sig_all["ts"] >= train_end) & (sig_all["ts"] < test_end)]
        if len(train_sig) < MIN_TRAIN or len(test_sig) == 0:
            continue
        best = None
        for decay in DECAY_GRID:
            for mpf in MIN_PROFIT_FRAC_GRID:
                tr = resolve_time_decay(train_sig, df1m, SYMBOL, RISK, TRAIL_ATR_MULT, decay, mpf)
                if len(tr) < MIN_TRAIN:
                    continue
                exp = tr["pnl"].mean()
                if best is None or exp > best[0]:
                    best = (exp, decay, mpf, len(tr))
        if best is None:
            continue
        exp, decay, mpf, ntrain = best
        chosen_log.append((train_end, decay, mpf, exp, ntrain))
        te = resolve_time_decay(test_sig, df1m, SYMBOL, RISK, TRAIL_ATR_MULT, decay, mpf)
        if len(te) > 0:
            all_oos.append(te)

    print("Selected (decay_bars, min_profit_frac), train-only:", flush=True)
    for te_end, decay, mpf, exp, n in chosen_log:
        print(f"  {te_end}: decay={decay} min_profit_frac={mpf} (train_exp=${exp:.2f}, n={n})", flush=True)

    if not all_oos:
        print("no OOS trades.", flush=True)
        return
    pooled = pd.concat(all_oos, ignore_index=True)
    t_stat, p_val = stats.ttest_1samp(pooled["pnl"].values, popmean=0.0)
    time_decay_frac = (pooled["outcome"] == "time_decay").mean()
    print(f"\nOOS: n={len(pooled)} exp=${pooled['pnl'].mean():.2f} t={t_stat:.2f} p={p_val:.2e} "
          f"(time_decay exits: {time_decay_frac:.1%} of trades)", flush=True)


if __name__ == "__main__":
    mnq_path = os.path.join("..", "data", "MNQ_CONTINUOUS.txt")
    df1m = load_1m(mnq_path)
    atr15 = causal_atr15_lookup(df1m)
    df1m_z = compute_session_vwap_z(df1m)
    print("data loaded", flush=True)

    # tod_last_third baseline (pool across all 8 seeds into one signal set for this test)
    tod_sigs = []
    for seed in SEEDS:
        raw = generate_random_entries(df1m, seed)
        sig = build_stop_signals(raw, atr15)
        t = sig["ts"].dt.time
        tod_sigs.append(sig[(t >= _T2) & (t < _CLOSE)])
    tod_all = pd.concat(tod_sigs, ignore_index=True).sort_values("ts").reset_index(drop=True)
    run("tod_last_third + time-decay exit", tod_all)

    z_sig = build_zscore_signals(df1m_z, atr15, Z_THRESH)
    run("VWAP Z-score + time-decay exit", z_sig)

    print("\n(compare: Round 39 tod_last_third baseline t=3.83(seed-level); "
          "Round 49 VWAP-Z baseline n=2351 exp=$40.88 t=3.76 @ $300 risk, this run uses $200)", flush=True)
    print("\nDONE.", flush=True)
