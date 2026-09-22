"""
Round 55: asymmetric partial-profit + runner exit, applied to tonight's best
combined MNQ signal set (tod_last_third + VWAP-Z). Genuinely different exit
structure from everything else tonight (all prior rounds used a single
whole-position ATR trail). 2/3 of the position closes at a fixed 1.5R target
(or the original stop, or session end, whichever first); the remaining 1/3
runs with a trailing stop (armed at breakeven once the 1.5R leg fills, then
trailed by the rolling N-bar extremum -- a simple proxy for "trail behind a
short MA/band") until stopped out or the session's flatten time.
"""
import os, sys
import datetime as dt
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, POINT_VALUE, TICK_SIZE, COMMISSION_RT, BUFFER, FOLDS, fold_stats
from round19_random_entry import causal_atr15_lookup, generate_random_entries, build_stop_signals, SEEDS
from round49_vwap_zscore import compute_session_vwap_z, build_zscore_signals

SYMBOL = "MNQ"
_T2 = dt.time(13, 50)
_CLOSE = dt.time(16, 0)
Z_THRESH = 2.5
RUNNER_TRAIL_BARS = 20
PARTIAL_R = 1.5
PARTIAL_FRAC = 2.0 / 3.0
RISK_SWEEP = [100, 150, 200, 300]
MIN_TRAIN = 20


def resolve_partial_runner(sig_df, df1m, symbol, risk_dollar, max_hold_bars=390):
    pv = POINT_VALUE[symbol]; tick = TICK_SIZE[symbol]
    slip_rt = 2 * tick * pv
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
        contracts_total = max(1, int(risk_dollar // (init_dist * pv)))
        if contracts_total < 3:
            # too small to split cleanly at this risk level -- take it as a single
            # whole-position trade (same sizing the plain baseline would use) rather
            # than force extra size just to make a 2:1 split possible.
            c_partial = contracts_total
            c_runner = 0
        else:
            c_partial = int(contracts_total * PARTIAL_FRAC)
            c_runner = contracts_total - c_partial
        commission = COMMISSION_RT * contracts_total
        end_pos = min(pos + max_hold_bars, n - 1)
        target = r.entry + PARTIAL_R * init_dist if r.direction == 1 else r.entry - PARTIAL_R * init_dist

        partial_pnl = None
        runner_pnl = None
        armed = False  # runner stop active (post-1.5R)
        runner_stop = r.stop
        exit_i_all = end_pos

        for i in range(pos, end_pos + 1):
            bar_hi, bar_lo, bar_cl = hi[i], lo[i], cl[i]
            if partial_pnl is None:
                # both legs still share the original stop pre-1.5R
                if (r.direction == 1 and bar_lo <= r.stop) or (r.direction == -1 and bar_hi >= r.stop):
                    move = (r.stop - r.entry) if r.direction == 1 else (r.entry - r.stop)
                    partial_pnl = move * pv * c_partial
                    runner_pnl = move * pv * c_runner
                    exit_i_all = i
                    break
                if (r.direction == 1 and bar_hi >= target) or (r.direction == -1 and bar_lo <= target):
                    move = (target - r.entry) if r.direction == 1 else (r.entry - target)
                    partial_pnl = move * pv * c_partial
                    armed = True
                    runner_stop = r.entry  # armed at breakeven
                    continue
            else:
                if (r.direction == 1 and bar_lo <= runner_stop) or (r.direction == -1 and bar_hi >= runner_stop):
                    move = (runner_stop - r.entry) if r.direction == 1 else (r.entry - runner_stop)
                    runner_pnl = move * pv * c_runner
                    exit_i_all = i
                    break
                lookback = slice(max(pos, i - RUNNER_TRAIL_BARS + 1), i + 1)
                if r.direction == 1:
                    runner_stop = max(runner_stop, lo[lookback].min())
                else:
                    runner_stop = min(runner_stop, hi[lookback].max())

        if partial_pnl is None:
            # never hit stop or target -- flatten both at session end
            move = (cl[end_pos] - r.entry) if r.direction == 1 else (r.entry - cl[end_pos])
            partial_pnl = move * pv * c_partial
            runner_pnl = move * pv * c_runner
            exit_i_all = end_pos
        elif runner_pnl is None:
            # partial hit target, runner never stopped -- flatten runner at session end
            move = (cl[end_pos] - r.entry) if r.direction == 1 else (r.entry - cl[end_pos])
            runner_pnl = move * pv * c_runner
            exit_i_all = end_pos

        pnl = partial_pnl + runner_pnl - commission - slip_rt * contracts_total
        results.append((r.ts, pnl))
        next_free_pos = exit_i_all + 1
    return pd.DataFrame(results, columns=["ts", "pnl"])


if __name__ == "__main__":
    mnq_path = os.path.join("..", "data", "MNQ_CONTINUOUS.txt")
    df1m = load_1m(mnq_path)
    atr15 = causal_atr15_lookup(df1m)
    df1m_z = compute_session_vwap_z(df1m)
    print("data loaded", flush=True)

    zsig = build_zscore_signals(df1m_z, atr15, Z_THRESH)
    raw = generate_random_entries(df1m, 0)
    sig_tod = build_stop_signals(raw, atr15)
    t = sig_tod["ts"].dt.time
    sig_tod = sig_tod[(t >= _T2) & (t < _CLOSE)]
    combined = pd.concat([sig_tod, zsig], ignore_index=True).sort_values("ts").reset_index(drop=True)

    for risk in RISK_SWEEP:
        all_oos = []
        for train_end, test_end in FOLDS:
            test_sig = combined[(combined["ts"] >= train_end) & (combined["ts"] < test_end)]
            if len(test_sig) < MIN_TRAIN:
                continue
            te = resolve_partial_runner(test_sig, df1m, SYMBOL, risk)
            if len(te) > 0:
                all_oos.append(te)
        if not all_oos:
            print(f"risk=${risk}: no trades")
            continue
        pooled = pd.concat(all_oos, ignore_index=True)
        t_stat, p_val = stats.ttest_1samp(pooled["pnl"].values, popmean=0.0)
        worst_dd = max(fold_stats(t)["maxdd"] for t in all_oos)
        n_breach = sum(1 for t in all_oos if fold_stats(t)["breach"])
        print(f"risk=${risk}: OOS n={len(pooled)} exp=${pooled['pnl'].mean():.2f} t={t_stat:.2f} "
              f"p={p_val:.2e} worst_dd=${worst_dd:.2f} breach={n_breach}/{len(all_oos)}", flush=True)

    print("\nDONE.", flush=True)
