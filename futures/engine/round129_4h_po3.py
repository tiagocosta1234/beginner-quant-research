"""
Round 129: ICT 4-hour "Power of 3" (accumulation-manipulation-distribution
inside one 4H candle), with an optional "near all-time highs -> longs only" bias.

Prompted by Fearing's "Framing Po3 Above All Time Highs | 4hr Po3 +79.25 Point
Trade Review" (youtube.com/watch?v=9Gh5VCCRnl8, 2026-05-04): one hand-picked NQ
long on 2026-04-30. YouTube blocked the video here; this tests the rule behind
it, mechanically. Pre-registered -- committed before any result was run.

  4H candles on the 18:00 ET grid; tested: 06:00-10:00 and 10:00-14:00 ET
  O = the candle's open (close of the bar stamped at the candle start)
  manipulation + reclaim (first 2 hours of the candle only):
    long:  price trades >= 8 ticks below O, then a 1-minute bar closes back above
           O -> buy at that close; stop = the low since the candle start - 1 tick
    short: mirror image (not in the ATH-filtered variants)
  exit: stop, or hold to the candle's end (distribution completes at its close)
  bias filter: the previous RTH close is within 2% of NQ's all-time high close to
               date (Yahoo NQ=F daily since 2000) -> longs only; otherwise no trade
  first setup per candle per day; $300 risk
  variants: candle in {06-10, 10-14} x filter in {none (both directions), near-ATH longs only}

idea_harness, 24-hour MNQ contract files. 4 variants take the ledger from k=59
to k=63: a candidate needs positive net and before-cost expectancy, IS
P(edge>0) >= 0.95 and OOS P(edge>0) >= 1 - 0.01/63.
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
from round11_fvg_bias import TICK_SIZE
from round122b_tom_long_history import load_daily

T = dt.time
MIN_TICKS = 8
ATH_WITHIN = 0.02


def ath_flags(days):
    """tday -> True if the previous RTH close is within ATH_WITHIN of the all-time
    high close to date (Yahoo NQ=F daily closes, through the previous day)."""
    nq = load_daily("NQ=F")["close"]
    ath = nq.cummax()
    out = {}
    for d in days:
        pc = d["prev_close"]
        prior = ath[ath.index < d["tday"]]
        out[d["tday"]] = bool(len(prior) and not np.isnan(pc) and pc >= (1 - ATH_WITHIN) * prior.iloc[-1])
    return out


def po3_signals(days, start, longs_only_near_ath=None):
    tick, out = TICK_SIZE["MNQ"], []
    s_min = start.hour * 60 + start.minute
    for d in days:
        if longs_only_near_ath is not None and not longs_only_near_ath[d["tday"]]:
            continue
        bars = pd.concat([d["on"], d["session"]])
        mins = bars.index.hour * 60 + bars.index.minute
        opener = bars[mins == s_min]
        if opener.empty:
            continue
        o = float(opener["close"].iloc[0])
        win = bars[(mins > s_min) & (mins <= s_min + 120)]
        lo_run, hi_run = np.inf, -np.inf
        for ts, h, l, c in zip(win.index, win["high"].values, win["low"].values, win["close"].values):
            lo_run, hi_run = min(lo_run, l), max(hi_run, h)
            if lo_run <= o - MIN_TICKS * tick and c > o:
                dd, sl = 1, lo_run - tick
            elif longs_only_near_ath is None and hi_run >= o + MIN_TICKS * tick and c < o:
                dd, sl = -1, hi_run + tick
            else:
                continue
            out.append((ts, dd, c, sl, np.nan))
            break
    return pd.DataFrame(out, columns=["ts", "direction", "entry", "sl", "tp"])


if __name__ == "__main__":
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k_final = H.ledger_count() + 4
    days = H.load_days("MNQ")
    bars, tdays = H.bars_from_days(days, "all"), [d["tday"] for d in days]
    near_ath = ath_flags(days)
    print(f"MNQ {len(days)} days, {sum(near_ath.values())} with the previous close within {ATH_WITHIN:.0%} of the ATH; "
          f"k after this round = {k_final}\n")
    rows = []
    for start, end in [(T(6, 0), T(10, 0)), (T(10, 0), T(14, 0))]:
        for filt in [None, near_ath]:
            sig = po3_signals(days, start, filt)
            tr = H.resolve_bracket(sig, bars, "MNQ", flat_time=end)
            label = "both directions" if filt is None else "near-ATH longs only"
            rows.append(H.test_idea(f"MNQ 4H Po3 {start.strftime('%H:%M')}-{end.strftime('%H:%M')}, {label}",
                                    tr, tdays, "MNQ", k_final))
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(H.ledger_rows(rows, "Round 129 (video, pre-registered)", commit)) + "\n")
    with open(os.path.join(H.HERE, "round129_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n==== {sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()} ====")
