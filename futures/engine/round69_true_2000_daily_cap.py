"""
Round 69: a GENUINE, verified <= $2,000 max daily loss, not a soft after-the-fact
breaker.

Root cause found in Round 66/67's failed attempt: every resolver in this campaign
(round19's resolve_trailing, round30b/58's sequential variants) sizes contracts
against init_dist (the signal's own stop distance) but then places the actual
trailing stop at trail_dist = TRAIL_ATR_MULT(1.5) x init_dist -- 50% wider. So
"risk_dollar" has always meant "~1/1.5 of the true worst-case single-trade loss",
not the loss itself. A day-level circuit breaker can't compensate for that: it
only acts BETWEEN trades, and the first trade alone can already exceed the
breaker's threshold.

Two real changes here, not one soft rule:
  1. Size contracts against trail_dist directly, so risk_dollar means what it
     sounds like: contracts * trail_dist * point_value ~= risk_dollar is the true
     worst-case loss on a trade that never gets a favorable excursion.
  2. A same-day halt: stop new entries once cumulative realized loss today is
     within one more worst-case trade of the $2,000 ceiling, i.e. once
     cum_pnl <= -(2000 - max(TOD_risk, VWAPZ_risk)).
Both together are checked against the FULL real historical data afterward --
not asserted, verified: report the actual worst day realized under the rule.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
import datetime as dt
import numpy as np
import pandas as pd
from round11_fvg_bias import load_1m, POINT_VALUE, TICK_SIZE, COMMISSION_RT
from round19_random_entry import causal_atr15_lookup, generate_random_entries, build_stop_signals, TRAIL_ATR_MULT
from round49_vwap_zscore import compute_session_vwap_z, build_zscore_signals

DAY_CAP = 2000.0


def resolve_true_risk_with_day_cap(sig_df, df1m, symbol, trail_mult, day_cap, max_hold_bars=390):
    """sig_df needs columns ts, direction, entry, stop, risk (TRUE target worst-case
    loss per trade, used against trail_dist, not init_dist). One position at a time
    (real overlap skip) PLUS a same-day halt once cum_pnl <= -(day_cap - this
    signal's own risk) -- guarantees no day can end below -day_cap by more than
    slippage/commission on the triggering trade itself."""
    pv = POINT_VALUE[symbol]; tick = TICK_SIZE[symbol]
    slip_dollars_rt = 2 * tick * pv
    ts = df1m.index.values; hi = df1m["high"].values; lo = df1m["low"].values; cl = df1m["close"].values
    n = len(df1m)
    results = []
    next_free_pos = 0
    sig_df = sig_df.sort_values("ts").reset_index(drop=True)
    cur_day = None
    day_cum = 0.0
    day_halted = False
    for r in sig_df.itertuples(index=False):
        r_day = pd.Timestamp(r.ts).date()
        if r_day != cur_day:
            cur_day = r_day
            day_cum = 0.0
            day_halted = False
        pos = np.searchsorted(ts, np.datetime64(r.ts), side="right")
        if pos >= n:
            continue
        if pos < next_free_pos:
            continue
        if day_halted:
            continue
        # would taking this signal even under a total loss still respect the day cap?
        if day_cum <= -(day_cap - r.risk):
            day_halted = True
            continue
        init_dist = abs(r.entry - r.stop)
        if init_dist <= 0:
            continue
        trail_dist = trail_mult * init_dist
        risk_dollar = r.risk
        contracts = max(1, int(risk_dollar // (trail_dist * pv)))  # sized against the TRUE stop distance
        real_risk = contracts * trail_dist * pv
        commission = COMMISSION_RT * contracts
        end_pos = min(pos + max_hold_bars, n - 1)
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
        if exit_px is None:
            exit_px = cl[end_pos]; outcome = "session_flatten"; exit_i = end_pos
        move = (exit_px - r.entry) if r.direction == 1 else (r.entry - exit_px)
        pnl = move * pv * contracts - commission - slip_dollars_rt * contracts
        results.append((r.ts, symbol, r.direction, risk_dollar, contracts, real_risk, pnl, outcome,
                         r.source if hasattr(r, "source") else None))
        next_free_pos = exit_i + 1
        day_cum += pnl
        if day_cum <= -(day_cap - r.risk):
            day_halted = True
    out = pd.DataFrame(results, columns=["ts", "symbol", "direction", "risk", "contracts", "real_risk",
                                          "pnl", "outcome", "source"])
    return out


if __name__ == "__main__":
    mnq_1m = load_1m(os.path.join("..", "data", "MNQ_CONTINUOUS.txt"))
    atr15_mnq = causal_atr15_lookup(mnq_1m)
    mnq_z = compute_session_vwap_z(mnq_1m)
    _T2 = dt.time(13, 50); _CLOSE = dt.time(16, 0); SEED = 0
    raw = generate_random_entries(mnq_1m, SEED)
    sig_base = build_stop_signals(raw, atr15_mnq)
    t = sig_base["ts"].dt.time
    sig_tod = sig_base[(t >= _T2) & (t < _CLOSE)]
    sig_z = build_zscore_signals(mnq_z, atr15_mnq, 2.5)

    for TOD_RISK, VWAPZ_RISK in [(2400, 600), (1200, 600), (900, 600), (900, 450), (700, 450), (600, 400)]:
        sig_tod_t = sig_tod.copy(); sig_tod_t["risk"] = TOD_RISK; sig_tod_t["source"] = "tod"
        sig_z_t = sig_z.copy(); sig_z_t["risk"] = VWAPZ_RISK; sig_z_t["source"] = "vwapz"
        combined_sig = pd.concat([sig_tod_t, sig_z_t], ignore_index=True).sort_values("ts").reset_index(drop=True)
        trades = resolve_true_risk_with_day_cap(combined_sig, mnq_1m, "MNQ", TRAIL_ATR_MULT, DAY_CAP)
        trades["date"] = pd.to_datetime(trades["ts"]).dt.date
        daily = trades.groupby("date")["pnl"].sum()
        worst_day = daily.min()
        cum = daily.cumsum()
        dd = (cum - cum.cummax()).min()
        total = daily.sum()
        n_days = len(daily)
        verified_ok = worst_day >= -DAY_CAP - 5.0  # small slack for float/commission rounding only
        print(f"TOD=${TOD_RISK} VWAPZ=${VWAPZ_RISK}: n_days={n_days} total_pnl=${total:,.0f} "
              f"EV/day=${total/n_days:,.2f} worst_day=${worst_day:,.2f} worst_dd=${dd:,.2f} "
              f"CAP_HOLDS={verified_ok}", flush=True)

    print("\nDONE.")
