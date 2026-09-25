"""
Round 120b: does the edge survive Broker's flat-by-close rule?

Round 69's resolve_true_risk_with_day_cap and Round 113's resolve_concurrent_trailing
(used by Rounds 69-119) close a position on its trailing stop or after
max_hold_bars=390 *bars* -- with no session boundary, so an afternoon entry is
still open at the next morning's open. Broker requires every position flat by
3:10 PM CT, and live_bot/main.py flattens then. The 2026-09-20 edge audit
noticed this in Round 19 and estimated it at ~5-7%.

The legacy MNQ file is 09:30-16:00 ET only, so a position held overnight meets
the next session's first bar. When that bar opens beyond the stop, the old
resolvers still fill at the stop price, while a favourable gap is banked in full.

Same signals, same sizing, one position, through round120_goal_judge.resolve_mtm
with three exit rules:
  flat   -- flat at each session's last bar (the real rule, what live_bot does)
  held   -- held across sessions up to 390 bars (the old resolvers' behavior)
  held_open_fill -- held, but a stop gapped through on a session's first bar
                    fills at that bar's open (the first price this data has)
Also runs round69's resolver as-is on the the trader signals, to show `held`
reproduces it.
"""
import os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import round120_goal_judge as J
from round19_random_entry import causal_atr15_lookup, generate_random_entries, build_stop_signals
from round49_vwap_zscore import compute_session_vwap_z, build_zscore_signals
from round69_true_2000_daily_cap import resolve_true_risk_with_day_cap
from round117_gap_and_trend_search import build_ema_cross_signals


def open_fill_adjust(trades, df1m, entry_px):
    """Re-price stop exits on a session's first bar that gapped through the stop
    at that bar's open. entry_px: Series of entry price by entry_ts."""
    pv = J.POINT_VALUE["MNQ"]
    first = pd.Series(~df1m.index.normalize().duplicated(), index=df1m.index)
    ed = pd.to_datetime(trades["entry_ts"]).dt.normalize()
    xd = pd.to_datetime(trades["exit_ts"]).dt.normalize()
    cost = trades["contracts"] * (J.COMMISSION_RT + 2 * J.TICK_SIZE["MNQ"] * pv)
    move = (trades["pnl"] + cost) / (pv * trades["contracts"])
    ent = entry_px.reindex(pd.to_datetime(trades["entry_ts"])).to_numpy()
    fill = np.where(trades["direction"] == 1, ent + move, ent - move)
    o = df1m["open"].reindex(pd.to_datetime(trades["exit_ts"])).to_numpy()
    on_first = first.reindex(pd.to_datetime(trades["exit_ts"])).to_numpy() & (ed != xd).to_numpy()
    worse = np.where(trades["direction"] == 1, o < fill, o > fill)
    adj = np.where(on_first & worse,
                   np.where(trades["direction"] == 1, o - fill, fill - o) * pv * trades["contracts"], 0.0)
    out = trades.copy()
    out["pnl_open_fill"] = trades["pnl"] + adj
    out["overnight"] = (ed != xd).to_numpy()
    return out, int((on_first & worse).sum())


def row(label, pnl, entry_ts):
    e = pd.to_datetime(entry_ts)
    st = J.edge_stats(pd.DataFrame({"pnl": pnl}))
    i, o = pnl[e < J.OOS_START], pnl[e >= J.OOS_START]
    print(f"  {label:<24} n={len(pnl):>5}  total ${pnl.sum():>9,.0f}  exp ${pnl.mean():>6.1f}  "
          f"P(>0) {st['p_pos']:.3f}  | IS exp ${i.mean():>6.1f} (n={len(i)})  OOS exp ${o.mean():>6.1f} (n={len(o)})",
          flush=True)


def check(name, sig, mnq, risk, max_contracts):
    entry_px = sig.drop_duplicates("ts").set_index("ts")["entry"]
    assert np.allclose(entry_px.to_numpy(), mnq["close"].reindex(entry_px.index).to_numpy()), \
        "signals are expected to enter at the signal bar's close"
    print(f"\n{name}  (risk ${risk:.0f}/trade, trail 1.5x, one position)")
    _, fl = J.resolve_mtm(sig, mnq, "MNQ", risk, 1.5, 1e9, max_contracts, flatten_eod=True)
    _, hd = J.resolve_mtm(sig, mnq, "MNQ", risk, 1.5, 1e9, max_contracts, flatten_eod=False)
    hd, n_gap = open_fill_adjust(hd, mnq, entry_px)
    row("flat (real rule)", fl["pnl"], fl["entry_ts"])
    row("held", hd["pnl"], hd["entry_ts"])
    row("held_open_fill", hd["pnl_open_fill"], hd["entry_ts"])
    on = hd["overnight"]
    print(f"  held overnight: {on.sum()} trades ({on.mean():.0%}), P&L ${hd.loc[on, 'pnl'].sum():,.0f} "
          f"(${hd.loc[on, 'pnl_open_fill'].sum():,.0f} with open fills; {n_gap} stops gapped through); "
          f"same-day trades ${hd.loc[~on, 'pnl'].sum():,.0f}", flush=True)


if __name__ == "__main__":
    mnq = J.load_mnq()
    atr = causal_atr15_lookup(mnq)

    ema = build_ema_cross_signals(mnq, atr, 9, 21, 1.5)
    check("EMA 9/21 crossover, stop 1.5 x ATR15 (Rounds 117-119)", ema, mnq, 450.0, 50)

    base = build_stop_signals(generate_random_entries(mnq, 0), atr)
    t = base["ts"].dt.time
    tod = base[(t >= dt.time(13, 50)) & (t < dt.time(16, 0))].reset_index(drop=True)
    vz = build_zscore_signals(compute_session_vwap_z(mnq), atr, 2.5).reset_index(drop=True)
    for name, sig in [("the trader TOD: random entry 13:50-16:00 ET (Rounds 39-69)", tod),
                      ("the trader VWAP-Z 2.5 (Rounds 49-69)", vz)]:
        s = sig.copy(); s["risk"] = 300.0
        r69 = resolve_true_risk_with_day_cap(s, mnq, "MNQ", 1.5, day_cap=1e9)
        print(f"\n  round69 resolver as-is on {name.split(':')[0].split(' (')[0]}: n={len(r69)}  "
              f"total ${r69['pnl'].sum():,.0f}  exp ${r69['pnl'].mean():.1f}", flush=True)
        check(name, sig, mnq, 300.0, 10_000)

    both = pd.concat([tod, vz], ignore_index=True).sort_values("ts").reset_index(drop=True)
    check("the trader TOD + VWAP-Z together, one position (what live_bot runs)", both, mnq, 300.0, 10_000)
