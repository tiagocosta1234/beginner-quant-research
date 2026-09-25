"""
Round 125: ICT "Judas swing" at the New York open, mechanical version.

Prompted by FX Replay's "Passing Broker Tests Using The ICT Judas Swing"
(youtube.com/watch?v=6npusxeFRRQ, 2026-08-15) -- a manual replay session whose
description gives no rules, so this tests the standard mechanical form instead.
Fixed before running:

  overnight range: high/low of 18:00 (prior evening) .. 09:29 ET
  setup window:    09:30 .. WINDOW_END ET
  short: price trades above the overnight high (the sweep), then a 1-minute bar
         closes back below it (the reclaim) -> sell at that close;
         stop = highest high since 09:30 + 1 tick
  long:  mirror image at the overnight low
  first setup of the day only; flat at the session's last bar (16:00)
  target variants: 2R, or the opposite side of the overnight range
  window variants: 10:30, 11:00

Data: the 24-hour MNQ contract files (data/nasdaq_extended, UTC -> New York).
Each day uses the contract with the most RTH volume, for both the overnight
range and the session, so rolls can't distort levels. Exits on 1-minute bars
(stop wins a tie), $300 risk, stop >= 8 ticks, commission + 2 ticks slippage.
"""
import os, sys, glob, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from round11_fvg_bias import POINT_VALUE, TICK_SIZE, COMMISSION_RT
from round115_extended_hours_data_and_search import _load_one
import round120_goal_judge as J

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "nasdaq_extended")
RISK, MIN_STOP_TICKS, MAX_CONTRACTS = 300.0, 8, 50
PV, TICK = POINT_VALUE["MNQ"], TICK_SIZE["MNQ"]
COST_PER_CONTRACT = COMMISSION_RT + 2 * TICK * PV


def load_days():
    """Yields (trade_date, overnight bars, RTH bars) per day, from that day's highest-volume contract."""
    frames = []
    for f in sorted(glob.glob(os.path.join(DATA, "*.Last.txt"))):
        df = _load_one(f)
        df.index = df.index.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
        df["tday"] = (df.index + pd.Timedelta(hours=6)).normalize()  # 18:00 ET starts the next trading day
        df["contract"] = os.path.basename(f)
        frames.append(df)
    allb = pd.concat(frames)
    t = allb.index.time
    rth = (t >= dt.time(9, 30)) & (t <= dt.time(16, 0))
    vol = allb[rth].groupby(["tday", "contract"])["vol"].sum()
    best = vol.groupby(level=0).idxmax().map(lambda x: x[1])
    for tday, contract in best.items():
        d = allb[(allb["tday"] == tday) & (allb["contract"] == contract)]
        tt = d.index.time
        on = d[(tt >= dt.time(18, 0)) | (tt < dt.time(9, 30))]
        session = d[(tt >= dt.time(9, 30)) & (tt <= dt.time(16, 0))]
        if len(on) >= 300 and len(session) >= 300:
            yield tday, on, session


def trade_day(on, s, window_end, target, stop_scale=1.0):
    on_hi, on_lo = on["high"].max(), on["low"].min()
    hi, lo, cl = s["high"].values, s["low"].values, s["close"].values
    in_win = s.index.time <= window_end
    swept_hi = swept_lo = False
    for i in range(len(s) - 1):
        if not in_win[i]:
            return None
        swept_hi |= hi[i] > on_hi
        swept_lo |= lo[i] < on_lo
        d = 0
        if swept_hi and cl[i] < on_hi:
            d, stop = -1, hi[: i + 1].max() + TICK
        elif swept_lo and cl[i] > on_lo:
            d, stop = 1, lo[: i + 1].min() - TICK
        if d == 0:
            continue
        entry = cl[i]
        dist = abs(entry - stop) * stop_scale  # 1.0 = just beyond the sweep's extreme (the "protected" level)
        stop = entry - d * dist
        if dist < MIN_STOP_TICKS * TICK:
            continue
        tp = entry + d * 2 * dist if target == "2R" else (on_lo if d == -1 else on_hi)
        if d * (tp - entry) <= 0:
            continue
        c = min(max(1, int(RISK // (dist * PV))), MAX_CONTRACTS)
        for k in range(i + 1, len(s)):
            if (d == 1 and lo[k] <= stop) or (d == -1 and hi[k] >= stop):
                px = stop
            elif (d == 1 and hi[k] >= tp) or (d == -1 and lo[k] <= tp):
                px = tp
            elif k == len(s) - 1:
                px = cl[k]
            else:
                continue
            return dict(entry_ts=s.index[i], direction=d, contracts=c,
                        pnl=d * (px - entry) * PV * c - c * COST_PER_CONTRACT, r=d * (px - entry) / dist)
    return None


if __name__ == "__main__":
    days = list(load_days())
    print(f"{len(days)} days, {days[0][0].date()}..{days[-1][0].date()} (24-hour MNQ contract files)\n")
    for window_end in [dt.time(10, 30), dt.time(11, 0)]:
        for target in ["2R", "opposite side"]:
            tr = pd.DataFrame([x for _, on, s in days if (x := trade_day(on, s, window_end, target))])
            e = pd.to_datetime(tr["entry_ts"])
            si, so = J.edge_stats(tr[e < J.OOS_START]), J.edge_stats(tr[e >= J.OOS_START])
            gross = tr["pnl"] + tr["contracts"] * COST_PER_CONTRACT
            print(f"window to {window_end.strftime('%H:%M')}, target {target:<13}: n={len(tr)} "
                  f"win {(tr['pnl'] > 0).mean():.0%} avg {tr['r'].mean():+.2f}R net ${tr['pnl'].mean():+.1f} "
                  f"(before costs ${gross.mean():+.1f}) | IS n={si['n']} ${si['exp']:+.1f} P(>0) {si['p_pos']:.2f} | "
                  f"OOS n={so['n']} ${so['exp']:+.1f} P(>0) {so['p_pos']:.2f}", flush=True)
