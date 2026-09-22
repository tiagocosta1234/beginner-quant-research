"""
Round 70: a genuinely different entry idea, not a repackaged inversion of VWAP-Z.
User asked for a strategy that (a) trades relatively frequently -- more than TOD's
1/day -- and (b) has an explicit "let winners run, cut losers short" profile. That's
a trend-following/breakout shape, not mean-reversion -- the OPPOSITE philosophy from
VWAP-Z, but built as its own principled entry (causal N-bar Donchian breakout), not
by flipping VWAP-Z's signal (which Round 69's fold check already showed decays to
near-zero in the most recent periods -- see TRADING_JOURNAL.md).

Exit mechanics reused unchanged from the rest of this campaign: STOP_ATR_MULT=1.0
initial stop, TRAIL_ATR_MULT=1.5 trailing stop -- the same "cut losers at a defined
distance, let winners run via the trail" mechanic already proven across TOD/VWAP-Z.
Only the ENTRY trigger is new here.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
import numpy as np
import pandas as pd
from round11_fvg_bias import load_1m, FOLDS
from round19_random_entry import causal_atr15_lookup, attach_atr, STOP_ATR_MULT, TRAIL_ATR_MULT
from round30b_sequential_fix import resolve_trailing_sequential


def build_breakout_signals(df1m, atr15, lookback):
    """Causal N-bar Donchian breakout: LONG when close breaks above the highest
    high of the PRIOR `lookback` bars (current bar excluded), SHORT on breaking
    below the prior lowest low. RTH-only by construction (df1m already is)."""
    hi = df1m["high"].values
    lo = df1m["low"].values
    cl = df1m["close"].values
    ts = df1m.index.values
    n = len(df1m)
    # prior-N rolling max/min, shifted by 1 so the current bar's own high/low
    # never counts toward its own breakout level (no lookahead)
    roll_hi = pd.Series(hi).rolling(lookback).max().shift(1).values
    roll_lo = pd.Series(lo).rolling(lookback).min().shift(1).values

    rows = []
    for i in range(lookback + 1, n):
        if np.isnan(roll_hi[i]) or np.isnan(roll_lo[i]):
            continue
        if cl[i] > roll_hi[i]:
            rows.append((ts[i], 1, cl[i]))
        elif cl[i] < roll_lo[i]:
            rows.append((ts[i], -1, cl[i]))
    sig = pd.DataFrame(rows, columns=["ts", "direction", "entry"])
    if len(sig) == 0:
        return sig
    sig = attach_atr(sig, atr15)
    sig = sig[sig["atr"] > 0].copy()
    stop_dist = STOP_ATR_MULT * sig["atr"]
    sig["stop"] = np.where(sig["direction"] == 1, sig["entry"] - stop_dist, sig["entry"] + stop_dist)
    return sig[["ts", "direction", "entry", "stop"]].reset_index(drop=True)


if __name__ == "__main__":
    RISK = 600
    mnq_1m = load_1m(os.path.join("..", "data", "MNQ_CONTINUOUS.txt"))
    atr15 = causal_atr15_lookup(mnq_1m)
    print(f"MNQ: {len(mnq_1m)} bars {mnq_1m.index.min()} -> {mnq_1m.index.max()}", flush=True)

    print("\n=== lookback sweep (raw signal frequency + full-history expectancy) ===")
    results = {}
    for lookback in (15, 20, 30, 45, 60, 90, 120):
        sig = build_breakout_signals(mnq_1m, atr15, lookback)
        trades, skipped = resolve_trailing_sequential(sig, mnq_1m, "MNQ", RISK, TRAIL_ATR_MULT)
        n_days = trades["ts"].dt.date.nunique() if len(trades) else 0
        wr = (trades["pnl"] > 0).mean() * 100 if len(trades) else 0
        exp = trades["pnl"].mean() if len(trades) else 0
        total = trades["pnl"].sum() if len(trades) else 0
        results[lookback] = trades
        print(f"lookback={lookback:4d}min: raw_signals={len(sig):5d} accepted_trades={len(trades):5d} "
              f"(skipped {skipped} overlap) trades/day={len(trades)/max(n_days,1):.2f} "
              f"win_rate={wr:.1f}% exp/trade=${exp:,.2f} total=${total:,.0f}", flush=True)

    print("\nDONE lookback sweep.")
