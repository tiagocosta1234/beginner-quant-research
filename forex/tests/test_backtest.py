"""Hand-built bars for forex/backtest.py's fill logic and MT5 broker replay.
Run: python forex/tests/test_backtest.py"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mt5 import poc_leg as P  # noqa: E402
from forex.backtest import Costs, daily, replay, simulate_trade  # noqa: E402

C0 = Costs()                                   # no spread multiplier change, no slippage
SIG_L = P.Signal(direction=1, stop_dist=10.0, target=120.0, ref_open=100.0, S=66.7)
SIG_S = P.Signal(direction=-1, stop_dist=10.0, target=80.0, ref_open=100.0, S=66.7)


def bars(rows, spread_pts=100):
    """rows: (open, high, low, close) bid; spread 100 points = 1.00 price unit."""
    idx = pd.date_range("2026-07-01 09:30", periods=len(rows), freq="1min")
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)
    df["spread"] = spread_pts
    return df


def test_long_pays_the_ask_and_hits_target_on_bid():
    t = simulate_trade(bars([(100, 105, 99.5, 104), (104, 121, 103, 120)]), SIG_L, 1, 120.0, C0)
    assert t["fill"] == 101.0 and t["stop"] == 91.0 and t["outcome"] == "target" and t["exit"] == 120.0
    assert t["pnl_per_lot"] == 19.0 and abs(t["R"] - 1.9) < 1e-12


def test_short_exits_on_the_ask():
    # bid low 79.2 -> ask low 80.2 > 80: target NOT hit; bid low 78.9 -> ask 79.9 <= 80: hit
    t = simulate_trade(bars([(100, 100.5, 79.2, 85), (85, 86, 78.9, 79)]), SIG_S, -1, 80.0, C0)
    assert t["fill"] == 100.0 and t["stop"] == 110.0 and t["outcome"] == "target"
    assert t["exit_time"] == pd.Timestamp("2026-07-01 09:31")


def test_short_stop_triggers_on_ask_not_bid():
    # bid high 109.5 -> ask 110.5 >= stop 110 -> stopped, filled at the stop
    t = simulate_trade(bars([(100, 101, 99, 100), (100, 109.5, 99, 109)]), SIG_S, -1, 80.0, C0)
    assert t["outcome"] == "stop" and t["exit"] == 110.0 and t["pnl_per_lot"] == -10.0


def test_gap_through_stop_fills_at_the_open():
    t = simulate_trade(bars([(100, 101, 99, 99), (85, 86, 84, 85)]), SIG_L, 1, 120.0, C0)
    assert t["outcome"] == "stop" and t["exit"] == 85.0 and t["pnl_per_lot"] == -16.0
    assert t["worst_per_lot"] == -16.0


def test_stop_first_when_both_in_one_bar():
    t = simulate_trade(bars([(100, 125, 88, 110)]), SIG_L, 1, 120.0, C0)
    assert t["outcome"] == "stop"


def test_flat_at_last_bar_close_on_exit_side():
    t = simulate_trade(bars([(100, 103, 99, 102), (102, 104, 101, 103)]), SIG_S, -1, 80.0, C0)
    assert t["outcome"] == "flat" and t["exit"] == 104.0 and t["pnl_per_lot"] == -4.0   # close 103 + spread 1


def test_slippage_and_spread_multiplier():
    c = Costs(spread_mult=2.0, entry_slip=0.5, stop_slip=0.25)
    t = simulate_trade(bars([(100, 101, 80, 85)]), SIG_L, 1, 120.0, c)
    assert t["fill"] == 102.5 and t["stop"] == 92.5 and t["exit"] == 92.25


def test_entry_spread_floor_applies_to_long_entry_only():
    c = Costs(entry_spread_floor=1.95)
    t = simulate_trade(bars([(100, 101, 99, 100)], spread_pts=145), SIG_L, 1, 120.0, c)
    assert abs(t["fill"] - 101.95) < 1e-9 and abs(t["entry_spread"] - 1.95) < 1e-9
    s = simulate_trade(bars([(100, 101, 99, 100)], spread_pts=145), SIG_S, -1, 80.0, c)
    assert s["fill"] == 100.0                     # a short sells the bid; the spread is paid on exit


def ask_bars(rows):
    """rows: (bid o,h,l,c, ask o,h,l,c, spread_max points)"""
    idx = pd.date_range("2026-07-01 09:30", periods=len(rows), freq="1min")
    df = pd.DataFrame([r[:8] for r in rows], columns=["open", "high", "low", "close", "ask_open", "ask_high", "ask_low", "ask_close"], index=idx)
    df["spread"] = [int(round((r[4] - r[0]) * 100)) for r in rows]
    df["spread_max"] = [r[8] for r in rows]
    return df


def test_real_ask_used_for_long_entry_and_short_exits():
    # long pays the first tick's ask (101.95), not bid + minimum spread
    t = simulate_trade(ask_bars([(100, 101, 99, 100, 101.95, 102.5, 100.5, 101.5, 195)]), SIG_L, 1, 120.0, C0)
    assert abs(t["fill"] - 101.95) < 1e-9
    # short: bid high 108.2 but ask spiked to 110.2 in the minute -> stopped at 110
    s = simulate_trade(ask_bars([(100, 101, 99, 100, 101.45, 102, 100.4, 101.4, 145),
                                 (100, 108.2, 99, 105, 101.4, 110.2, 100.4, 106.4, 400)]), SIG_S, -1, 80.0, C0)
    assert s["outcome"] == "stop" and s["exit"] == 110.0


def test_harsh_spread_widens_ask_by_the_widest_spread():
    c = Costs(spread_mult=2.0)
    # ask_high 109.0 + one more widest spread (1.5) = 110.5 >= stop 110 -> stopped under harsh costs only
    rows = [(100, 101, 99, 100, 101.45, 102, 100.4, 101.4, 150), (100, 107.5, 99, 105, 101.4, 109.0, 100.4, 106.4, 150)]
    assert simulate_trade(ask_bars(rows), SIG_S, -1, 80.0, C0)["outcome"] == "flat"
    assert simulate_trade(ask_bars(rows), SIG_S, -1, 80.0, c)["outcome"] == "stop"


def test_no_trade_when_fill_is_through_target():
    assert simulate_trade(bars([(100, 101, 99, 100)]), SIG_S, -1, 100.5, C0) is None


def test_lots_rounding():
    assert P.lots_for(1000, 34.0) == 29.41 and P.lots_for(5, 1000.0) == 0.0


def _dly(pnls, worsts=None):
    idx = pd.bdate_range("2026-07-01", periods=len(pnls))
    d = pd.DataFrame(index=idx)
    d["pnl"] = pnls
    d["worst"] = worsts if worsts is not None else [min(p, 0) for p in pnls]
    d["entry_time"] = [i + pd.Timedelta(hours=9, minutes=30) for i in idx]
    return d


def test_replay_passes_both_phases():
    r = replay(_dly([3000, 3000, 3000, 1500] + [0] * 2 + [2000, 2000, 1000, 500]), 0, gap=2)
    assert r["result"] == "live" and r["days"] == 10


def test_replay_needs_four_trading_days():
    r = replay(_dly([11000, 0, 0, 0, 0, 0]), 0)      # target on day 1, but only 1 trading day... then 5 more with trades
    assert r["result"] != "fail"
    d = _dly([11000, 10, 10, 10] + [0] * 2 + [6000, 10, 10, 10])
    assert replay(d, 0)["result"] == "live"


def test_replay_daily_loss_on_intraday_worst():
    r = replay(_dly([100, -200, 50], worsts=[0, -5100, 0]), 0)
    assert r["result"] == "fail" and r["reason"] == "max_daily_loss" and r["days"] == 2


if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for f in fns:
        f()
    print(f"{len(fns)}/{len(fns)} passed")
