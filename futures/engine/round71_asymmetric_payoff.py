"""
Round 71: hunting for a real (not hypothetical) strategy with a genuinely better
payoff ratio -- avg win meaningfully larger than avg loss -- to see how close a
real, backtested edge can get to the design target from the user's "what if"
question (avg loss $500 / avg win $2500, a 5:1 ratio). Best real ratios found so
far this campaign: VWAP-Z 2.24:1 (Round 65), TOD's real win/loss not far off.

Why the existing mechanic can't get there on its own: every resolver in this
campaign uses ONE distance (trail_dist = TRAIL_ATR_MULT x init_dist) for BOTH the
initial protective stop AND the trailing offset once in profit. Widening it to let
winners run further ALSO widens the initial risk by the same factor -- reward and
risk scale together, payoff ratio stays roughly fixed regardless of trail_mult.

This builds a genuine two-stage stop instead: a TIGHT initial stop (small,
independent distance), a move-to-breakeven once price shows real follow-through,
and only THEN a trail that can be wider than the original risk -- explicitly
decoupling "cut losers fast" from "let winners run far," which is what an
improved payoff ratio actually requires mechanically, not just a bigger number
somewhere.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
import numpy as np
import pandas as pd
from round11_fvg_bias import load_1m, POINT_VALUE, TICK_SIZE, COMMISSION_RT, FOLDS
from round19_random_entry import causal_atr15_lookup


def resolve_two_stage_stop(sig_df, df1m, symbol, risk_dollar, initial_stop_mult, breakeven_trigger_r,
                            trail_mult, max_hold_bars=390):
    """sig_df needs ts, direction, entry, atr (raw ATR value, not a precomputed stop).
    Stage 1: tight initial stop at initial_stop_mult x ATR.
    Stage 2: once favorable excursion >= breakeven_trigger_r x initial risk, stop
             moves to breakeven (entry price).
    Stage 3: once favorable excursion >= breakeven_trigger_r x initial risk AGAIN
             (same trigger, so stage 2/3 activate together) the stop also starts
             trailing at trail_mult x ATR behind the peak, which can be WIDER than
             the initial risk -- this is what decouples cut-losses from let-run.
    One position at a time (real overlap skip), same as every other resolver here."""
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
        init_dist = initial_stop_mult * r.atr
        if init_dist <= 0:
            continue
        trail_dist = trail_mult * r.atr
        contracts = max(1, int(risk_dollar // (init_dist * pv)))
        commission = COMMISSION_RT * contracts
        end_pos = min(pos + max_hold_bars, n - 1)
        entry = r.entry
        cur_stop = entry - init_dist if r.direction == 1 else entry + init_dist
        best = entry
        trailing_active = False
        exit_px = None; outcome = "timeout"; exit_i = end_pos
        for i in range(pos, end_pos + 1):
            bar_hi, bar_lo = hi[i], lo[i]
            if r.direction == 1:
                if bar_lo <= cur_stop:
                    exit_px = cur_stop; outcome = "trail_stop" if trailing_active else "initial_stop"
                    exit_i = i; break
                best = max(best, bar_hi)
                favorable = best - entry
                if favorable >= breakeven_trigger_r * init_dist:
                    trailing_active = True
                    cur_stop = max(cur_stop, entry, best - trail_dist)
            else:
                if bar_hi >= cur_stop:
                    exit_px = cur_stop; outcome = "trail_stop" if trailing_active else "initial_stop"
                    exit_i = i; break
                best = min(best, bar_lo)
                favorable = entry - best
                if favorable >= breakeven_trigger_r * init_dist:
                    trailing_active = True
                    cur_stop = min(cur_stop, entry, best + trail_dist)
        if exit_px is None:
            exit_px = cl[end_pos]; outcome = "session_flatten"; exit_i = end_pos
        move = (exit_px - entry) if r.direction == 1 else (entry - exit_px)
        pnl = move * pv * contracts - commission - slip_dollars_rt * contracts
        results.append((r.ts, symbol, r.direction, risk_dollar, contracts, pnl, outcome))
        next_free_pos = exit_i + 1
    return pd.DataFrame(results, columns=["ts", "symbol", "direction", "risk", "contracts", "pnl", "outcome"])


if __name__ == "__main__":
    sys.path.insert(0, ".")
    from round70_breakout_momentum import build_breakout_signals
    from round19_random_entry import attach_atr

    mnq_1m = load_1m(os.path.join("..", "data", "MNQ_CONTINUOUS.txt"))
    atr15 = causal_atr15_lookup(mnq_1m)

    # reuse the Round 70 breakout entries (best real edge found so far: frequent,
    # positive in every fold) but attach raw ATR instead of a precomputed stop --
    # this resolver derives its own stop stages from ATR directly
    raw_sig = build_breakout_signals(mnq_1m, atr15, 15)[["ts", "direction", "entry"]]
    sig = attach_atr(raw_sig, atr15)
    sig = sig[sig["atr"] > 0].reset_index(drop=True)

    print("=== baseline (Round 70's own mechanic, for reference) ===")
    from round30b_sequential_fix import resolve_trailing_sequential
    from round19_random_entry import STOP_ATR_MULT, TRAIL_ATR_MULT
    base_sig = build_breakout_signals(mnq_1m, atr15, 15)
    base_trades, _ = resolve_trailing_sequential(base_sig, mnq_1m, "MNQ", 600, TRAIL_ATR_MULT)
    bw = base_trades[base_trades["pnl"] > 0]["pnl"]; bl = base_trades[base_trades["pnl"] <= 0]["pnl"]
    print(f"n={len(base_trades)} win%={(base_trades['pnl']>0).mean()*100:.1f} "
          f"avg_win=${bw.mean():,.2f} avg_loss=${bl.mean():,.2f} ratio={bw.mean()/abs(bl.mean()):.2f} "
          f"exp/trade=${base_trades['pnl'].mean():,.2f}")

    print("\n=== two-stage stop sweep (breakeven-then-trail) ===")
    best = None
    for init_mult in (0.5, 0.75, 1.0):
        for be_trigger in (0.75, 1.0, 1.5, 2.0):
            for trail_mult in (1.5, 2.5, 4.0):
                trades = resolve_two_stage_stop(sig, mnq_1m, "MNQ", 600, init_mult, be_trigger, trail_mult)
                if len(trades) < 50:
                    continue
                w = trades[trades["pnl"] > 0]["pnl"]; l = trades[trades["pnl"] <= 0]["pnl"]
                if len(w) == 0 or len(l) == 0:
                    continue
                ratio = w.mean() / abs(l.mean())
                exp = trades["pnl"].mean()
                wr = (trades["pnl"] > 0).mean() * 100
                if best is None or exp > best[0]:
                    best = (exp, init_mult, be_trigger, trail_mult, ratio, wr, len(trades))
                if ratio >= 2.5 and exp > 0:
                    print(f"init={init_mult} be_trig={be_trigger} trail={trail_mult}: n={len(trades):5d} "
                          f"win%={wr:.1f} avg_win=${w.mean():,.2f} avg_loss=${l.mean():,.2f} "
                          f"ratio={ratio:.2f} exp/trade=${exp:,.2f}", flush=True)

    print(f"\nBEST by exp/trade: exp={best[0]:.2f} init_mult={best[1]} be_trigger={best[2]} "
          f"trail_mult={best[3]} ratio={best[4]:.2f} win%={best[5]:.1f} n={best[6]}")
    print("\nDONE.")
