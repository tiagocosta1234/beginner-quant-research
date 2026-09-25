"""
Round 122: published intraday effects, judged by round120_goal_judge with every
realism rule on -- pre-registered 2026-09-26, committed before any result was run.

Round 120b showed the edges this campaign relied on came from holding positions
across the session close. These are effects with decades of published
out-of-sample evidence that are legal on Broker (in and out within the RTH
session, flat at the close) and were never tested with the session-bounded
resolver:

  H1a  intraday momentum (Gao, Han, Li & Zhou 2018, JFE): the return from the
       previous RTH close to 10:00 ET predicts the last half hour. At the 15:30
       bar's close, trade in its sign; flat at the session's last bar.
  H1b  same, signal = previous close -> 15:30 (Baltussen, Da, Lammers & Martens
       2021, JFE: dealer gamma hedging pushes the close in the day's direction).
  H1c  H1b only on days where |signal| >= the median |signal| of the prior 60
       days (the effect is reported stronger on large-move days).
  H3   turn of the month (Ariel 1987; Lakonishok & Smidt 1988; McConnell & Xu
       2008): long from the 09:30 bar's close to the session's last bar on the
       last trading day of each month and the first three of the next.

Fixed exits for all: initial stop 2.0 x ATR15, trailing 1.5x that distance
(3 x ATR15), flat at the session's last bar -- mostly a time exit, as in the
papers. MNQ (the only long-history equity index file). No parameter is tuned.

Same harness and acceptance test as Round 121 (round121_candidate_search.evaluate):
sizing/tier/policy/withdrawal path chosen on days before 2025-07-01, then judged on
the untouched days after. Acceptance = all of: P(both goals by 2026-12-31) >= 80%
full and OOS; bootstrap P(edge>0) >= 99% IS and OOS; >= 300 OOS trades; top-20
trades <= 50% of OOS profit.

Secondary, also fixed now: a variant is worth wiring into live_bot for
Practice-mode shadowing only (no money) if IS P(edge>0) >= 0.95 AND OOS mean
trade > 0. That is a much weaker bar and says nothing about the year-end goal.

Usage: python round122_published_effects_search.py [n_screen_paths] [n_final_paths]
"""
import os, sys, json, time, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from round19_random_entry import causal_atr15_lookup
import round120_goal_judge as J
import round121_candidate_search as C

STOP_MULT = 2.0
T_SIGNAL_EARLY = dt.time(10, 0)
T_ENTRY = dt.time(15, 30)
T_OPEN = dt.time(9, 30)


def intraday_momentum_signals(df1m, atr15, variant):
    """variant: 'a' (prev close -> 10:00), 'b' (prev close -> 15:30), 'c' (b, large-move days)."""
    close = df1m["close"]
    day = df1m.index.normalize()
    t = df1m.index.time
    last = close.groupby(day).last()
    prev_close = last.shift(1)
    at = lambda tt: close[t == tt].groupby(day[t == tt]).last()
    entry_bar = pd.Series(df1m.index[t == T_ENTRY], index=day[t == T_ENTRY])
    p_entry = at(T_ENTRY)
    p_sig = at(T_SIGNAL_EARLY) if variant == "a" else p_entry
    r = (p_sig / prev_close - 1.0).reindex(entry_bar.index)
    keep = r.notna() & (r != 0)
    if variant == "c":
        thresh = r.abs().shift(1).rolling(60, min_periods=60).median()  # prior 60 days only
        keep &= r.abs() >= thresh
    raw = pd.DataFrame({"ts": entry_bar[keep].values, "direction": np.sign(r[keep]).astype(int).values,
                        "entry": p_entry.reindex(entry_bar.index)[keep].values})
    return C.with_atr_stop(raw, atr15, STOP_MULT)


def turn_of_month_signals(df1m, atr15):
    t = df1m.index.time
    day = df1m.index.normalize()
    days = pd.DatetimeIndex(sorted(day[t == T_OPEN].unique()))  # real sessions only (holidays leave stray bars)
    ym = days.year * 12 + days.month
    pos_from_start = pd.Series(1, index=days).groupby(ym).cumcount().values          # 0 = first day of month
    pos_from_end = pd.Series(1, index=days)[::-1].groupby(ym[::-1]).cumcount()[::-1].values  # 0 = last day
    # the file starts and ends mid-month: its first month has no real "first days",
    # its last month no real "last day"
    tom = days[((pos_from_start <= 2) & (ym != ym[0])) | ((pos_from_end == 0) & (ym != ym[-1]))]
    bars = df1m[(t == T_OPEN) & day.isin(tom)]
    raw = pd.DataFrame({"ts": bars.index, "direction": 1, "entry": bars["close"].values})
    return C.with_atr_stop(raw, atr15, STOP_MULT)


if __name__ == "__main__":
    n_screen = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    n_final = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
    mnq = J.load_mnq()
    atr = causal_atr15_lookup(mnq)
    runs = [
        ("H1a intraday momentum, prev close -> 10:00 signal", "H1a", intraday_momentum_signals(mnq, atr, "a")),
        ("H1b intraday momentum, prev close -> 15:30 signal", "H1b", intraday_momentum_signals(mnq, atr, "b")),
        ("H1c intraday momentum, 15:30 signal, large-move days", "H1c", intraday_momentum_signals(mnq, atr, "c")),
        ("H3 turn of the month, long RTH", "H3", turn_of_month_signals(mnq, atr)),
    ]
    results = []
    for name, fam, sig in runs:
        print(f"{fam}: {len(sig)} signals, {sig['direction'].eq(1).mean():.0%} long", flush=True)
        r = C.evaluate(name, fam, [("MNQ", mnq, sig, False)], n_screen, n_final)
        s_is, s_oos = r["stats_is"], r["stats_oos"]
        r["shadow_worthy"] = bool(s_is["p_pos"] >= 0.95 and s_oos["exp"] > 0)
        print(f"   secondary (Practice-mode shadowing only): {'YES' if r['shadow_worthy'] else 'no'}", flush=True)
        results.append(r)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "round122_results.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"\n==== {sum(r['passed'] for r in results)} of {len(results)} pass the goal test; "
          f"{sum(r['shadow_worthy'] for r in results)} meet the secondary shadowing bar ====")
