"""
Round 73: fixed-points bracket exit -- 15pt stop, move to +2pt (a small locked-in
profit, not exact breakeven, to clear commission/slippage) once price reaches the
1:1 level (15pts favorable), 50pt static take-profit. A completely different exit
philosophy from every other resolver in this campaign: fixed points, not ATR-based,
and a hard profit CEILING (50pts) rather than letting winners run via a trail.

Applied to VWAP-Z's existing entry trigger (Z-score extreme + 1-bar reversal) --
only the exit mechanic changes here, not the entry logic.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
import numpy as np
import pandas as pd
from round11_fvg_bias import load_1m, FOLDS, POINT_VALUE, TICK_SIZE, COMMISSION_RT
from round19_random_entry import causal_atr15_lookup
from round49_vwap_zscore import compute_session_vwap_z, build_zscore_signals

STOP_POINTS = 15.0
TP_POINTS = 50.0
LOCK_PROFIT_POINTS = 2.0  # "tiny profit" once 1:1 is reached, not exact breakeven


def resolve_fixed_bracket(sig_df, df1m, symbol, risk_dollar, stop_pts, tp_pts, lock_pts, max_hold_bars=390):
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
        entry = r.entry
        contracts = max(1, int(risk_dollar // (stop_pts * pv)))
        commission = COMMISSION_RT * contracts
        end_pos = min(pos + max_hold_bars, n - 1)
        if r.direction == 1:
            cur_stop = entry - stop_pts
            take_profit = entry + tp_pts
            locked_level = entry + lock_pts
            one_to_one = entry + stop_pts
        else:
            cur_stop = entry + stop_pts
            take_profit = entry - tp_pts
            locked_level = entry - lock_pts
            one_to_one = entry - stop_pts
        locked_in = False
        exit_px = None; outcome = "timeout"; exit_i = end_pos
        for i in range(pos, end_pos + 1):
            bar_hi, bar_lo = hi[i], lo[i]
            if r.direction == 1:
                if bar_lo <= cur_stop:
                    exit_px = cur_stop; outcome = "locked_profit" if locked_in else "stop_loss"; exit_i = i; break
                if bar_hi >= take_profit:
                    exit_px = take_profit; outcome = "take_profit"; exit_i = i; break
                if not locked_in and bar_hi >= one_to_one:
                    locked_in = True
                    cur_stop = max(cur_stop, locked_level)
            else:
                if bar_hi >= cur_stop:
                    exit_px = cur_stop; outcome = "locked_profit" if locked_in else "stop_loss"; exit_i = i; break
                if bar_lo <= take_profit:
                    exit_px = take_profit; outcome = "take_profit"; exit_i = i; break
                if not locked_in and bar_lo <= one_to_one:
                    locked_in = True
                    cur_stop = min(cur_stop, locked_level)
        if exit_px is None:
            exit_px = cl[end_pos]; outcome = "session_flatten"; exit_i = end_pos
        move = (exit_px - entry) if r.direction == 1 else (entry - exit_px)
        pnl = move * pv * contracts - commission - slip_dollars_rt * contracts
        results.append((r.ts, symbol, r.direction, risk_dollar, contracts, pnl, outcome))
        next_free_pos = exit_i + 1
    return pd.DataFrame(results, columns=["ts", "symbol", "direction", "risk", "contracts", "pnl", "outcome"])


def resolve_fixed_bracket_daycap(sig_df, df1m, symbol, risk_dollar, stop_pts, tp_pts, lock_pts, day_cap, max_hold_bars=390):
    """Same mechanic as resolve_fixed_bracket, plus a same-day halt once cum_pnl
    could not absorb one more worst-case loss without breaching day_cap. Since
    stop_pts is fixed (not ATR-based), the worst-case per-trade loss is EXACT and
    deterministic here (contracts * stop_pts * point_value + costs) -- no safety-
    margin guess needed, unlike the ATR-based resolvers elsewhere in this campaign."""
    pv = POINT_VALUE[symbol]; tick = TICK_SIZE[symbol]
    slip_dollars_rt = 2 * tick * pv
    ts = df1m.index.values; hi = df1m["high"].values; lo = df1m["low"].values; cl = df1m["close"].values
    n = len(df1m)
    results = []
    next_free_pos = 0
    sig_df = sig_df.sort_values("ts").reset_index(drop=True)
    contracts = max(1, int(risk_dollar // (stop_pts * pv)))
    commission = COMMISSION_RT * contracts
    worst_case_loss = stop_pts * pv * contracts + commission + slip_dollars_rt * contracts
    cur_day = None; day_cum = 0.0; day_halted = False
    for r in sig_df.itertuples(index=False):
        r_day = pd.Timestamp(r.ts).date()
        if r_day != cur_day:
            cur_day = r_day; day_cum = 0.0; day_halted = False
        pos = np.searchsorted(ts, np.datetime64(r.ts), side="right")
        if pos >= n or pos < next_free_pos or day_halted:
            continue
        if day_cum <= -(day_cap - worst_case_loss):
            day_halted = True
            continue
        entry = r.entry
        end_pos = min(pos + max_hold_bars, n - 1)
        if r.direction == 1:
            cur_stop = entry - stop_pts; take_profit = entry + tp_pts; locked_level = entry + lock_pts; one_to_one = entry + stop_pts
        else:
            cur_stop = entry + stop_pts; take_profit = entry - tp_pts; locked_level = entry - lock_pts; one_to_one = entry - stop_pts
        locked_in = False
        exit_px = None; outcome = "timeout"; exit_i = end_pos
        for i in range(pos, end_pos + 1):
            bar_hi, bar_lo = hi[i], lo[i]
            if r.direction == 1:
                if bar_lo <= cur_stop:
                    exit_px = cur_stop; outcome = "locked_profit" if locked_in else "stop_loss"; exit_i = i; break
                if bar_hi >= take_profit:
                    exit_px = take_profit; outcome = "take_profit"; exit_i = i; break
                if not locked_in and bar_hi >= one_to_one:
                    locked_in = True; cur_stop = max(cur_stop, locked_level)
            else:
                if bar_hi >= cur_stop:
                    exit_px = cur_stop; outcome = "locked_profit" if locked_in else "stop_loss"; exit_i = i; break
                if bar_lo <= take_profit:
                    exit_px = take_profit; outcome = "take_profit"; exit_i = i; break
                if not locked_in and bar_lo <= one_to_one:
                    locked_in = True; cur_stop = min(cur_stop, locked_level)
        if exit_px is None:
            exit_px = cl[end_pos]; outcome = "session_flatten"; exit_i = end_pos
        move = (exit_px - entry) if r.direction == 1 else (entry - exit_px)
        pnl = move * pv * contracts - commission - slip_dollars_rt * contracts
        results.append((r.ts, symbol, r.direction, contracts, pnl, outcome))
        next_free_pos = exit_i + 1
        day_cum += pnl
        if day_cum <= -(day_cap - worst_case_loss):
            day_halted = True
    return pd.DataFrame(results, columns=["ts", "symbol", "direction", "contracts", "pnl", "outcome"]), worst_case_loss


if __name__ == "__main__":
    RISK = 600
    mnq_1m = load_1m(os.path.join("..", "data", "MNQ_CONTINUOUS.txt"))
    atr15 = causal_atr15_lookup(mnq_1m)
    mnq_z = compute_session_vwap_z(mnq_1m)
    sig_z = build_zscore_signals(mnq_z, atr15, 2.5)[["ts", "direction", "entry"]]

    trades = resolve_fixed_bracket(sig_z, mnq_1m, "MNQ", RISK, STOP_POINTS, TP_POINTS, LOCK_PROFIT_POINTS)
    print(f"n={len(trades)} win%={(trades['pnl']>0).mean()*100:.1f}")
    print(trades["outcome"].value_counts())
    w = trades[trades["pnl"] > 0]["pnl"]; l = trades[trades["pnl"] <= 0]["pnl"]
    print(f"avg_win=${w.mean():,.2f} avg_loss=${l.mean():,.2f} ratio={w.mean()/abs(l.mean()):.2f}")
    print(f"exp/trade=${trades['pnl'].mean():,.2f}  total=${trades['pnl'].sum():,.0f}")

    print("\n=== fold check ===")
    all_folds = [("2022-12-12", "2024-01-01")] + FOLDS
    for start, end in all_folds:
        s, e = pd.Timestamp(start), pd.Timestamp(end)
        f = trades[(trades["ts"] >= s) & (trades["ts"] < e)]
        exp = f["pnl"].mean() if len(f) else float("nan")
        wr = (f["pnl"] > 0).mean() * 100 if len(f) else 0
        print(f"  {start}..{end:12s} n={len(f):5d} win%={wr:5.1f} exp/trade=${exp:8.2f} total=${f['pnl'].sum():10,.0f}")
    print("\nDONE.")
