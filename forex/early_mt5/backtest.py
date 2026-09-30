"""
Bar-level backtest of the POC leg on MT5 CFD bars, and an exact MT5 2-Step replay.

FILLS (MT5 bars are BID prices; tick-built bars also carry the real ASK OHLC, used when present):
  ask = bid + spread x point x spread_mult (the bar's own spread); at ENTRY the spread is at least
  entry_spread_floor (the bar field is the minute's minimum; the first 09:30 tick is wider)
  long : enters at the 09:30 bar's ask open + entry_slip; exits on the BID
         stop  : bid low <= stop  -> fills at min(stop, bar open if it gapped past) - stop_slip
         target: bid high >= target -> fills at target (limit)
  short: enters at the bid open - entry_slip; exits on the ASK
         stop  : ask high >= stop  -> fills at max(stop, ask open if it gapped past) + stop_slip
         target: ask low <= target -> fills at target
  stop and target in the same bar -> the stop (conservative); nothing hit by 16:10 ET -> closes at
  the last bar's close on the exit side. Stop re-anchored to the fill (poc_leg.bracket_from_fill),
  target = the prior POC. US100.cash: $1 per point per lot, no commission; flat intraday -> no swap.
  worst = the lowest mark-to-market of the position on the exit side while open (MT5 broker judges equity).

MT5 REPLAY: mt5broker.rules.ChallengeState driven day by day (the same object a live executor uses):
equity checked at the day's worst mark, balance updated at the close, trading day recorded at the
entry; Phase 2 starts `gap` trading days after Phase 1 passes.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd

from mt5broker import poc_leg as P
from mt5broker.rules import PHASE1, PHASE2, ChallengeState

PRAGUE_TZ = "Europe/Prague"


@dataclass(frozen=True)
class Costs:
    spread_mult: float = 1.0
    entry_slip: float = 0.0      # points, adverse
    stop_slip: float = 0.0       # points, adverse
    point: float = 0.01
    entry_spread_floor: float = 0.0   # points; the M1 bar spread is the minute's MINIMUM -- ticks show
                                      # 1.95 pts at the first 09:30 tick vs 1.45 in the bar (forex/early_mt5/spread_probe.py)


def simulate_trade(bars: pd.DataFrame, sig: P.Signal, direction: int, target: float, costs: Costs) -> dict | None:
    """One trade on one session's trade-window bars (index = NY time; columns open/high/low/close bid,
    spread in points). Entry at bars.iloc[0]'s open. Returns per-lot results or None if no bracket."""
    o, h, l, c = (bars[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    if "ask_open" in bars.columns:        # real ask from tick-built bars; harsh = widen by the minute's widest spread
        extra = bars["spread_max"].to_numpy(float) * costs.point * (costs.spread_mult - 1.0)
        ao, ah, al, ac = (bars[k].to_numpy(float) + extra for k in ("ask_open", "ask_high", "ask_low", "ask_close"))
    else:                                # bid + the bar's (minimum) spread
        spr = bars["spread"].to_numpy(float) * costs.point * costs.spread_mult
        ao, ah, al, ac = o + spr, h + spr, l + spr, c + spr
    d = direction
    entry_ask = max(ao[0], o[0] + costs.entry_spread_floor * costs.spread_mult)
    entry_spr = entry_ask - o[0]
    fill = entry_ask + costs.entry_slip if d == 1 else o[0] - costs.entry_slip
    if (target - fill) * d <= 0:
        return None
    stop = fill - d * sig.stop_dist
    worst = 0.0
    exit_px, outcome, ei = None, "flat", len(bars) - 1
    for i in range(len(bars)):
        if d == 1:
            hit_stop, hit_tgt = l[i] <= stop, h[i] >= target
            mark_worst = l[i] - fill
        else:
            hit_stop, hit_tgt = ah[i] >= stop, al[i] <= target
            mark_worst = fill - ah[i]
        if hit_stop:
            if d == 1:
                px = (min(stop, o[i]) if i > 0 else stop) - costs.stop_slip
            else:
                px = (max(stop, ao[i]) if i > 0 else stop) + costs.stop_slip
            exit_px, outcome, ei = px, "stop", i
            worst = min(worst, d * (px - fill))
            break
        worst = min(worst, mark_worst)
        if hit_tgt:
            exit_px, outcome, ei = target, "target", i
            break
    if exit_px is None:
        exit_px = c[-1] if d == 1 else ac[-1]
    pnl = d * (exit_px - fill)
    return dict(direction=d, fill=fill, stop=stop, target=target, exit=exit_px, outcome=outcome,
                entry_time=bars.index[0], exit_time=bars.index[ei], pnl_per_lot=pnl, worst_per_lot=min(worst, pnl, 0.0),
                R=pnl / sig.stop_dist, entry_spread=entry_spr, stop_dist=sig.stop_dist)


def sessions(cfd_ny: pd.DataFrame):
    """Yield (date, rth_bars 09:30-16:00, window_bars 09:30-16:10) per NY date."""
    t = cfd_ny.index
    for d, g in cfd_ny.groupby(t.normalize()):
        tt = g.index.time
        rth = g[(tt >= P.RTH_OPEN) & (tt < P.RTH_CLOSE)]
        win = g[(tt >= P.RTH_OPEN) & (tt < P.FLAT_AT)]
        yield d, rth, win


def run_strategy(cfd_ny: pd.DataFrame, costs: Costs, direction_override=None, skip_days=()) -> tuple[pd.DataFrame, list]:
    """All POC-leg trades. direction_override: optional {date: +1/-1} (random-direction control; the
    target is mirrored to the same distance on the other side of the open). skip_days: dates that are
    not US trading sessions (the CFD can quote on exchange holidays) -- neither traded nor profiled."""
    prior, rows, days = [], [], []
    skip = {pd.Timestamp(x).normalize() for x in skip_days}
    for d, rth, win in sessions(cfd_ny):
        if len(rth) == 0 or d in skip:
            continue
        days.append(d)
        first = win.index[0]
        late = (first - (d + pd.Timedelta(hours=9, minutes=30))).total_seconds() / 60
        if prior and late <= P.ENTRY_GRACE_MIN:
            sig = P.signal(prior, float(win["open"].iloc[0]))
            if sig is not None:
                direction, target = sig.direction, sig.target
                if direction_override is not None:
                    direction = direction_override[d]
                    target = sig.ref_open + direction * abs(sig.target - sig.ref_open)
                tr = simulate_trade(win, sig, direction, target, costs)
                if tr is not None:
                    tr["date"] = d
                    tr["late_min"] = late
                    rows.append(tr)
        prof = P.profile(rth)
        if prof is not None:
            prior.append(prof)
    return pd.DataFrame(rows), days


def daily(trades: pd.DataFrame, days: list, risk_usd: float) -> pd.DataFrame:
    """Per trading day at a given $ risk: lots, pnl, worst mark (all $), entry time (NY)."""
    df = pd.DataFrame(index=pd.DatetimeIndex(days))
    df["pnl"] = 0.0; df["worst"] = 0.0; df["entry_time"] = pd.NaT
    if len(trades):
        lots = trades["stop_dist"].map(lambda s: P.lots_for(risk_usd, s))
        t = trades.assign(lots=lots, pnl=trades["pnl_per_lot"] * lots, worst=trades["worst_per_lot"] * lots)
        t = t[t["lots"] > 0].set_index("date")
        df.loc[t.index, "pnl"] = t["pnl"]; df.loc[t.index, "worst"] = t["worst"]; df.loc[t.index, "entry_time"] = t["entry_time"]
    return df


def _utc(ny_ts) -> dt.datetime:
    return pd.Timestamp(ny_ts).tz_localize("America/New_York").tz_convert("UTC").to_pydatetime()


def replay(dly: pd.DataFrame, start: int, gap: int = 2, max_days: int | None = None) -> dict:
    """Exact MT5 2-Step replay from trading day `start`: Phase 1 then (after `gap` trading days)
    Phase 2, each from $100,000, until live or breached or the data ends (or `max_days` trading
    days have passed -- result "open"; used where only "live within N days" is needed)."""
    idx = dly.index
    if max_days is not None:
        dly = dly.iloc[: start + max_days]
        idx = dly.index
    pnl, worst, et = dly["pnl"].to_numpy(), dly["worst"].to_numpy(), dly["entry_time"].to_numpy()
    i, phase_start = start, start
    for phase, rules in ((1, PHASE1), (2, PHASE2)):
        st, bal = ChallengeState(rules), rules.initial
        while i < len(idx):
            day = idx[i]
            if not pd.isna(et[i]):
                t_entry = _utc(et[i])
                st.on_update(t_entry, bal, bal)                        # day roll at the first event of the day
                st.on_position_opened(t_entry)
                if st.on_update(t_entry + dt.timedelta(minutes=1), bal, bal + worst[i]):
                    return dict(result="fail", reason=st.breach, phase=phase, days=i - start + 1)
                bal += pnl[i]
                st.on_update(_utc(day + pd.Timedelta(hours=16, minutes=10)), bal, bal)
                if st.objectives(bal, 0)["passed"]:
                    i += 1
                    if phase == 1:
                        i += gap
                        break
                    return dict(result="live", days=i - start, phase1_days=None)
            i += 1
        else:
            return dict(result="open", phase=phase, days=i - start)
    return dict(result="open", phase=2, days=i - start)
