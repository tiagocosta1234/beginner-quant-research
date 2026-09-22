"""
Round 22: does relaxing the "1 trade/day" convention multiply Round 19's validated
exit-convexity edge into a usable daily pace?

Context: every round 1-21 capped trading at 1 trade/day/instrument as a *safety
convention* stated explicitly in Round 1's methodology, not a discovered limit.
Round 19 found a real edge (random entry + ATR-trailing exit, MNQ, +$66.27/trade at
$400 risk, 8/8 seeds positive, tail 11.9-21.5%). Round 20 proved the edge is exit-driven,
not entry-driven (real entries are worse than random for this exit). Since entry
timing carries no skill here, there's no obvious reason 2-4 independent random entries
on the same day should behave differently from 1 -- this round tests that empirically
rather than assuming it.

Multi-entry generation (causal, sequential, one position at a time -- matches this
repo's cluster-mutex convention): for each day, draw `trades_per_day` candidate
(time, direction) pairs uniformly at random from that day's bars. Walk them in time
order; a candidate is only accepted if its bar is at or after `available_from_pos`
(initialized to the day's first eligible bar). Each accepted entry is resolved
immediately (ATR-trailing exit, identical mechanics to round19_random_entry.resolve_trailing)
so the next candidate's gate reflects reality, not an assumption of independence:
available_from_pos = this trade's exit_pos + MIN_GAP_BARS. A day can therefore produce
fewer than `trades_per_day` entries if candidates cluster before the prior trade closes
-- this is intentional and reported (n_entries/day actually achieved).

MIN_GAP_BARS = 5 (five 1-minute bars after an exit before the next entry may open) --
a deliberately short but explicit gap, not zero, to avoid two entries evaluating on
literally the same bar.

Same FOLDS, same costs, same $400/$600 risk levels, same 8 seeds as Round 19/20 for
direct comparability.
"""
import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from round11_fvg_bias import (
    load_1m, POINT_VALUE, TICK_SIZE, COMMISSION_RT, BUFFER, FOLDS, tail_concentration,
)
from round19_random_entry import causal_atr15_lookup, attach_atr, SEEDS, STOP_ATR_MULT, TRAIL_ATR_MULT

MIN_GAP_BARS = 5
MAX_HOLD_BARS = 390
RISK_LEVELS = (400, 600)
TRADES_PER_DAY_GRID = (1, 2, 3, 4)


def _resolve_one(entry_pos, direction, entry_px, stop_px, hi, lo, cl, n, pv, trail_mult,
                  contracts, commission, slip_dollars_rt, max_hold_bars=MAX_HOLD_BARS):
    init_dist = abs(entry_px - stop_px)
    trail_dist = trail_mult * init_dist
    end_pos = min(entry_pos + max_hold_bars, n - 1)
    cur_stop = entry_px - trail_dist if direction == 1 else entry_px + trail_dist
    best = entry_px
    exit_px = None
    exit_pos = end_pos
    outcome = "timeout"
    for i in range(entry_pos, end_pos + 1):
        bar_hi, bar_lo = hi[i], lo[i]
        if direction == 1:
            if bar_lo <= cur_stop:
                exit_px = cur_stop
                exit_pos = i
                outcome = "trail_stop"
                break
            best = max(best, bar_hi)
            cur_stop = max(cur_stop, best - trail_dist)
        else:
            if bar_hi >= cur_stop:
                exit_px = cur_stop
                exit_pos = i
                outcome = "trail_stop"
                break
            best = min(best, bar_lo)
            cur_stop = min(cur_stop, best + trail_dist)
    if exit_px is None:
        exit_px = cl[end_pos]
        exit_pos = end_pos
        outcome = "session_flatten"
    move = (exit_px - entry_px) if direction == 1 else (entry_px - exit_px)
    pnl = move * pv * contracts - commission - slip_dollars_rt * contracts
    return exit_pos, exit_px, pnl, outcome


def generate_and_resolve_multi(df1m, atr_series, seed, trades_per_day, risk_dollar,
                                symbol, trail_mult=TRAIL_ATR_MULT):
    rng = np.random.default_rng(seed)
    pv = POINT_VALUE[symbol]
    tick = TICK_SIZE[symbol]
    slip_dollars_rt = 2 * tick * pv
    ts = df1m.index.values
    hi = df1m["high"].values
    lo = df1m["low"].values
    cl = df1m["close"].values
    n = len(df1m)
    atr_ts = atr_series.index.values
    atr_vals = atr_series.values

    dates = pd.Series(df1m.index.date, index=df1m.index)
    rows = []
    daily_counts = []

    for day, day_idx in df1m.groupby(dates).groups.items():
        if len(day_idx) < 30:
            continue
        day_positions = np.searchsorted(ts, day_idx.values)
        day_start_pos = int(day_positions.min())
        day_end_pos = int(day_positions.max())
        n_candidates = min(trades_per_day, len(day_idx))
        cand_positions = rng.choice(np.arange(day_start_pos, day_end_pos + 1), size=n_candidates,
                                     replace=False)
        cand_positions.sort()
        directions = rng.integers(0, 2, size=n_candidates) * 2 - 1  # -1 or +1

        available_from = day_start_pos
        n_accepted = 0
        for cpos, direction in zip(cand_positions, directions):
            if cpos < available_from:
                continue
            cand_ts = ts[cpos]
            apos = np.searchsorted(atr_ts, cand_ts, side="right") - 1
            if apos < 0:
                continue
            atr_val = atr_vals[apos]
            if not (atr_val > 0):
                continue
            entry_px = cl[cpos]
            stop_dist = STOP_ATR_MULT * atr_val
            stop_px = entry_px - stop_dist if direction == 1 else entry_px + stop_dist
            init_dist = abs(entry_px - stop_px)
            contracts = max(1, int(risk_dollar // (init_dist * pv)))
            commission = COMMISSION_RT * contracts
            exit_pos, exit_px, pnl, outcome = _resolve_one(
                cpos, direction, entry_px, stop_px, hi, lo, cl, n, pv, trail_mult,
                contracts, commission, slip_dollars_rt,
            )
            rows.append((cand_ts, symbol, direction, risk_dollar, contracts, pnl, outcome,
                         str(day)))
            n_accepted += 1
            available_from = min(exit_pos, day_end_pos) + MIN_GAP_BARS
        daily_counts.append(n_accepted)

    trades = pd.DataFrame(rows, columns=["ts", "symbol", "direction", "risk", "contracts",
                                          "pnl", "outcome", "day"])
    return trades, daily_counts


def fold_slice(trades, train_end, test_end):
    return trades[(trades["ts"] >= pd.Timestamp(train_end)) & (trades["ts"] < pd.Timestamp(test_end))]


def daily_pnl_series(trades):
    return trades.groupby("day")["pnl"].sum()


def maxdd_of(pnl_values):
    equity = pd.Series(pnl_values).cumsum()
    peak = equity.cummax()
    return float((peak - equity).max()) if len(equity) else 0.0


def run_symbol(symbol, path):
    print(f"\n{'='*70}\nRound 22: {symbol} from {path}", flush=True)
    df1m = load_1m(path)
    atr15 = causal_atr15_lookup(df1m)
    print(f"{symbol}: {len(df1m)} 1m bars, {df1m.index.min()} -> {df1m.index.max()}", flush=True)

    summary_rows = []
    for tpd in TRADES_PER_DAY_GRID:
        for risk in RISK_LEVELS:
            per_trade_exps, per_day_exps, worst_dd_over_seeds, tail_pooled = [], [], 0.0, []
            all_seed_trades = []
            all_seed_actual_tpd = []
            for seed in SEEDS:
                trades, daily_counts = generate_and_resolve_multi(df1m, atr15, seed, tpd, risk, symbol)
                if len(trades) == 0:
                    continue
                all_seed_trades.append(trades)
                all_seed_actual_tpd.append(np.mean(daily_counts) if daily_counts else 0.0)
                per_trade_exps.append(trades["pnl"].mean())
                daily = daily_pnl_series(trades)
                per_day_exps.append(daily.mean())

                fold_dds = []
                for train_end, test_end in FOLDS:
                    fs = fold_slice(trades, train_end, test_end)
                    if len(fs) == 0:
                        continue
                    fdaily = daily_pnl_series(fs)
                    fold_dds.append(maxdd_of(fdaily.values))
                if fold_dds:
                    worst_dd_over_seeds = max(worst_dd_over_seeds, max(fold_dds))

            if not all_seed_trades:
                continue
            pooled = pd.concat(all_seed_trades, ignore_index=True)
            mean_exp_trade = float(np.mean(per_trade_exps))
            mean_exp_day = float(np.mean(per_day_exps))
            mean_actual_tpd = float(np.mean(all_seed_actual_tpd))
            tc10 = tail_concentration(pooled, 10)
            tc20 = tail_concentration(pooled, 20)
            print(f"tpd_target={tpd} risk=${risk}: actual_tpd={mean_actual_tpd:.2f} "
                  f"n_trades_pooled={len(pooled)} exp/trade=${mean_exp_trade:.2f} "
                  f"exp/day=${mean_exp_day:.2f} worst_day_maxdd(over 8 seeds, 6 folds)=${worst_dd_over_seeds:.2f} "
                  f"tail10={tc10} tail20={tc20}", flush=True)
            summary_rows.append(dict(tpd_target=tpd, risk=risk, actual_tpd=mean_actual_tpd,
                                      n=len(pooled), exp_trade=mean_exp_trade, exp_day=mean_exp_day,
                                      worst_day_maxdd=worst_dd_over_seeds, tail10=tc10, tail20=tc20))
    return pd.DataFrame(summary_rows)


SIZING_GRID = (400, 300, 200, 150, 125, 100, 75, 50, 25)
SAFETY_MARGIN_TARGET = 0.70 * BUFFER  # same 70%-of-real-buffer convention as Round 20


def buffer_safe_search(df1m, atr15, symbol, tpd):
    """Round 20's exact sizing-search convention, applied per trades/day setting:
    sweep risk down until worst-case (max over 8 seeds x 6 folds) DAILY drawdown
    clears 70% of the real $4,937.50 buffer -- real margin, not cut to the wire."""
    rows = []
    for risk in SIZING_GRID:
        per_trade_exps, per_day_exps, worst_dd = [], [], 0.0
        all_trades = []
        for seed in SEEDS:
            trades, daily_counts = generate_and_resolve_multi(df1m, atr15, seed, tpd, risk, symbol)
            if len(trades) == 0:
                continue
            all_trades.append(trades)
            per_trade_exps.append(trades["pnl"].mean())
            per_day_exps.append(daily_pnl_series(trades).mean())
            for train_end, test_end in FOLDS:
                fs = fold_slice(trades, train_end, test_end)
                if len(fs) == 0:
                    continue
                worst_dd = max(worst_dd, maxdd_of(daily_pnl_series(fs).values))
        if not all_trades:
            continue
        pooled = pd.concat(all_trades, ignore_index=True)
        exp_trade = float(np.mean(per_trade_exps))
        exp_day = float(np.mean(per_day_exps))
        within_target = worst_dd <= SAFETY_MARGIN_TARGET
        rows.append(dict(tpd_target=tpd, risk=risk, n=len(pooled), exp_trade=exp_trade,
                          exp_day=exp_day, worst_day_maxdd=worst_dd, within_70pct_target=within_target))
        print(f"  [sizing] tpd={tpd} risk=${risk}: exp/day=${exp_day:.2f} "
              f"worst_day_maxdd=${worst_dd:.2f} within_70pct_target={within_target}", flush=True)
        if within_target:
            break  # smallest risk in the grid that already clears it is what we want to report next-finer if needed
    return pd.DataFrame(rows)


if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "..", "data", "MNQ_CONTINUOUS.txt")
    res_mnq = run_symbol("MNQ", path)
    print("\n\n=== MNQ SUMMARY TABLE ($400/$600, headline comparison to Round 19/20) ===")
    print(res_mnq.to_string(index=False))
    res_mnq.to_csv(os.path.join(os.path.dirname(__file__), "round22_mnq_summary.csv"), index=False)

    print("\n\n=== BUFFER-SAFE SIZING SEARCH (per trades/day target) ===", flush=True)
    df1m = load_1m(path)
    atr15 = causal_atr15_lookup(df1m)
    all_sizing = []
    for tpd in TRADES_PER_DAY_GRID:
        print(f"\n--- tpd_target={tpd} ---", flush=True)
        sizing_df = buffer_safe_search(df1m, atr15, "MNQ", tpd)
        all_sizing.append(sizing_df)
    sizing_all = pd.concat(all_sizing, ignore_index=True)
    print("\n\n=== FULL SIZING TABLE ===")
    print(sizing_all.to_string(index=False))
    sizing_all.to_csv(os.path.join(os.path.dirname(__file__), "round22_sizing_search.csv"), index=False)
    print("\nDONE.", flush=True)
