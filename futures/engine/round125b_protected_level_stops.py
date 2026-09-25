"""
Round 125b: does putting the stop beyond the "protected" high/low help?

Prompted by NQSimon's "Stop getting stopped out (Protected lows/highs)"
(youtube.com/watch?v=KfoChW1mHPI, 2026-08-03; YouTube blocked the video here,
so this is from its title and chapters): in ICT's AMD model, the stop belongs
beyond the manipulation move's extreme -- the protected level -- not at a
nearer swing, so the manipulation doesn't take you out.

Round 125's Judas swing entries already put the stop 1 tick beyond the sweep's
extreme. Same entries, same $300 risk, stop distance scaled 0.5x (tighter than
the protected level), 1.0x (at it) and 1.5x (beyond it); setup window to 11:00.
"""
import os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import round120_goal_judge as J
import round125_judas_swing as R

if __name__ == "__main__":
    days = list(R.load_days())
    for target in ["2R", "opposite side"]:
        for scale in [0.5, 1.0, 1.5]:
            tr = pd.DataFrame([x for _, on, s in days if (x := R.trade_day(on, s, dt.time(11, 0), target, scale))])
            e = pd.to_datetime(tr["entry_ts"])
            si, so = J.edge_stats(tr[e < J.OOS_START]), J.edge_stats(tr[e >= J.OOS_START])
            stopped = (tr["r"] <= -0.99).mean()
            gross = tr["pnl"] + tr["contracts"] * R.COST_PER_CONTRACT
            print(f"target {target:<13} stop {scale:.1f}x protected: n={len(tr)} stopped out {stopped:.0%} "
                  f"win {(tr['pnl'] > 0).mean():.0%} avg {tr['r'].mean():+.2f}R net ${tr['pnl'].mean():+.1f} "
                  f"(before costs ${gross.mean():+.1f}, {tr['contracts'].mean():.1f} contracts) | "
                  f"IS ${si['exp']:+.1f} P(>0) {si['p_pos']:.2f} | OOS ${so['exp']:+.1f} P(>0) {so['p_pos']:.2f}", flush=True)
