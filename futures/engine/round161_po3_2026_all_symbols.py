"""
Round 161: the trader asked, after the P=0.73 explanation for ledger row 217 (Round
160's "INVERTED MNQ 4H Po3 10:00-14:00, both directions"), to backtest that
exact strategy for calendar year 2026 across every symbol this repo has data
for. This is a descriptive re-slice of an already-registered rule (unchanged:
same entry/stop/exit as round129.po3_signals + round160.invert_po3_signals),
not a new idea -- so it does NOT get a new IDEA_LEDGER.md row. Two honest
caveats, stated up front rather than discovered after running:

1. For MNQ, "2026" is a strict subset of the OOS window Round 160 already
   scored (OOS_START = 2025-07-01) -- this is not new evidence, just a
   narrower look at data already counted in that OOS P=0.801.
2. Data reality, not a choice: only MNQ (`nasdaq_extended`) and MGC
   (`gold_extended`) have multi-year 24h-day-structured history. The other 7
   Broker-tradeable micros (MES, MYM, M2K, SIL, MCL, MBT, MET) only have the
   BrokerAPI 1-minute pull that starts 2026-07-29 (MET 2026-08-05) -- about
   8 weeks, not "a year". Their 2026 number IS their entire available
   history; it is reported anyway, labeled with its real date range, because
   the request was for every symbol available, not just the ones where a
   year exists.

MGC and the 7 short-history symbols have never had PO3 tested on them before
at all (round129/round159/round160 only ever used MNQ) -- so those results
ARE new, for whatever a few weeks (or MGC's one real year) of data are worth.

Mechanics, unchanged from round160: same entry/stop as round129.po3_signals
(first setup per day, 10:00-14:00 ET candle, manipulation in the first 2
hours, 8-tick minimum, stop 1 tick beyond the sweep), then inverted (entry
unchanged, direction flipped, stop reflected through entry: new_sl = 2*entry
- old_sl), held to the candle's own end (14:00) or stopped out, $300 risk,
real commission + 2-tick slippage. `po3_signals_multi` below is round129's
function with one change: the tick size is a parameter instead of hardcoded
to MNQ's, so it can run on other instruments (never needed before because
PO3 was MNQ-only). MBT/MET tick and point value aren't in idea_harness.PV/TK
(never tested before) -- added here from CME Group's own published Micro
contract specs (cmegroup.com), confirmed 2026-09-27: Micro Bitcoin = 0.1 BTC/
contract, 5-point tick = $0.50/contract (point value $0.10); Micro Ether =
0.1 ETH/contract, 0.5-point tick = $0.05/contract (point value $0.10).

Report only: n, win%, net $/trade (after cost), gross $/trade (before cost),
total $ for the period, and the same bootstrap P(edge>0) used everywhere else
in this ledger (round120_goal_judge.edge_stats) -- useful context, but NOT
compared against the k-adjusted candidate bar, since this isn't a new-idea
submission.
"""
import os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
import round129_4h_po3 as R129
from round160_invert_remaining_ict import invert_po3_signals

SHORT_HISTORY = ["MES", "MYM", "M2K", "SIL", "MCL", "MBT", "MET"]
LONG_HISTORY = ["MNQ", "MGC"]

# Never tested before (PO3 was MNQ-only through Round 160) -- added here, not
# in idea_harness.py, since nothing else in the repo needs these yet.
H.PV["MBT"], H.TK["MBT"] = 0.10, 5.0
H.PV["MET"], H.TK["MET"] = 0.10, 0.5


def load_days_brokerapi(symbol):
    """Same {tday, on, session} shape as idea_harness.load_days, built from the
    single-active-contract BrokerAPI 1-minute CSV (no continuous-contract
    stitching needed -- it's already the one pulled contract throughout)."""
    path = os.path.join(H.HERE, "..", "data", f"{symbol}_1MIN_BROKERAPI.csv")
    df = pd.read_csv(path)
    idx = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    bars = pd.DataFrame({"high": df["high"].values, "low": df["low"].values,
                          "close": df["close"].values}, index=idx).sort_index()
    bars["tday"] = (bars.index + pd.Timedelta(hours=6)).normalize()
    t = bars.index.time
    is_rth = (t >= H.T_RTH_OPEN) & (t <= H.T_RTH_CLOSE)
    days = []
    for tday, g in bars.groupby(bars["tday"]):
        m = is_rth[bars.index.get_indexer(g.index)]
        days.append(dict(tday=tday, on=g[~m], session=g[m]))
    return days


def po3_signals_multi(days, start, tick):
    """round129.po3_signals with the tick size parameterized instead of hardcoded
    to MNQ -- identical entry/stop logic otherwise, both-directions only."""
    out, s_min = [], start.hour * 60 + start.minute
    for d in days:
        bars = pd.concat([d["on"], d["session"]])
        if bars.empty:
            continue
        mins = bars.index.hour * 60 + bars.index.minute
        opener = bars[mins == s_min]
        if opener.empty:
            continue
        o = float(opener["close"].iloc[0])
        win = bars[(mins > s_min) & (mins <= s_min + 120)]
        lo_run, hi_run = np.inf, -np.inf
        for ts, h, l, c in zip(win.index, win["high"].values, win["low"].values, win["close"].values):
            lo_run, hi_run = min(lo_run, l), max(hi_run, h)
            if lo_run <= o - R129.MIN_TICKS * tick and c > o:
                dd, sl = 1, lo_run - tick
            elif hi_run >= o + R129.MIN_TICKS * tick and c < o:
                dd, sl = -1, hi_run + tick
            else:
                continue
            out.append((ts, dd, c, sl, np.nan))
            break
    return pd.DataFrame(out, columns=["ts", "direction", "entry", "sl", "tp"])


def run_symbol(sym):
    if sym in LONG_HISTORY:
        days = [d for d in H.load_days(sym) if d["tday"].year == 2026]
    else:
        days = load_days_brokerapi(sym)
    if not days:
        return dict(sym=sym, n=0)
    bars = pd.concat([d[k] for d in days for k in ("on", "session")]).sort_index()
    sig = po3_signals_multi(days, dt.time(10, 0), H.TK[sym])
    inv = invert_po3_signals(sig)
    tr = H.resolve_bracket(inv, bars, sym, flat_time=dt.time(14, 0))
    first, last = days[0]["tday"].date(), days[-1]["tday"].date()
    if tr.empty:
        return dict(sym=sym, n=0, first=first, last=last)
    gross = tr["pnl"] + tr["contracts"] * H.cost_per_contract(sym)
    st = J.edge_stats(tr, n_boot=8_000)
    return dict(sym=sym, n=len(tr), win=float((tr["pnl"] > 0).mean()), net=float(tr["pnl"].mean()),
                gross=float(gross.mean()), total=float(tr["pnl"].sum()), p_pos=st["p_pos"], first=first, last=last)


if __name__ == "__main__":
    print("Round 161: 2026 year-to-date, INVERTED PO3 10:00-14:00 ET both-directions, per symbol\n")
    rows = [run_symbol(s) for s in LONG_HISTORY + SHORT_HISTORY]
    for r in rows:
        if r["n"] == 0:
            print(f"  {r['sym']:<4} 0 trades ({r.get('first','?')} -> {r.get('last','?')})")
            continue
        print(f"  {r['sym']:<4} {r['first']} -> {r['last']}  n={r['n']:>4}  win {r['win']:.0%}  "
              f"net ${r['net']:+7.2f}  gross ${r['gross']:+7.2f}  total ${r['total']:+9.0f}  "
              f"P(edge>0) {r['p_pos']:.3f}")
