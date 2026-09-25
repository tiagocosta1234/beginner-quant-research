"""
Round 127: ICT standard-deviation projections as reversal levels ("top/bottom tick").

Prompted by DMCTRADES' "How to Top/Bottom Tick (GUIDE ON STDV AND OTE)"
(youtube.com/watch?v=d-aJ_CQUbyM, 2026-04-17). YouTube blocked the video here and
the description states no rules, so this tests the standard mechanical form.
(The OTE retracement entry was tested in Round 76 and lost.) Pre-registered --
committed before any result was run.

  reference range: MNQ Asian range, bars (20:00, 00:00] ET; width w
  levels:          Asian high + k*w (fade short), Asian low - k*w (fade long)
  window:          00:00 .. 12:00 ET (London and the New York morning)
  entry:           the first bar that trades through a level by >= 1 tick ->
                   enter against the move at that bar's close
  stop:            0.5*w beyond the level (skip if the close is already past it)
  target:          back 1*w from the level, or all the way to the Asian range edge
  flat at 16:00; one trade per day; stop >= 8 ticks; $300 risk
  variants:        k in {2.0, 2.5} x target in {1 SD back, range edge}

Uses idea_harness (24-hour contract files, one contract per day). 4 variants
take the ledger from k=51 to k=55: a candidate needs positive net and
before-cost expectancy, IS P(edge>0) >= 0.95 and OOS P(edge>0) >= 1 - 0.01/55.
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
from round11_fvg_bias import TICK_SIZE

T = dt.time
MIN_STOP_TICKS = 8


def stdv_signals(days, k, target):
    tick, out = TICK_SIZE["MNQ"], []
    for d in days:
        bars = pd.concat([d["on"], d["session"]])
        t = bars.index.time
        asia = bars[(t > T(20, 0)) | (t == T(0, 0))]
        asia = asia[asia.index.time != T(20, 0)]
        if len(asia) < 200:
            continue
        a_hi, a_lo = asia["high"].max(), asia["low"].min()
        w = a_hi - a_lo
        if w <= 0:
            continue
        up, dn = a_hi + k * w, a_lo - k * w
        win = bars[(t > T(0, 0)) & (t <= T(12, 0))]
        for ts, h, l, c in zip(win.index, win["high"].values, win["low"].values, win["close"].values):
            if h >= up + tick:
                dd, level = -1, up
            elif l <= dn - tick:
                dd, level = 1, dn
            else:
                continue
            sl = level - dd * 0.5 * w
            tp = (level + dd * w) if target == "1 SD back" else (a_hi if dd == -1 else a_lo)
            if dd * (c - sl) > 0 and dd * (tp - c) > 0 and abs(c - sl) >= MIN_STOP_TICKS * tick:
                out.append((ts, dd, c, sl, tp))
            break  # first touch of either level decides the day
    return pd.DataFrame(out, columns=["ts", "direction", "entry", "sl", "tp"])


if __name__ == "__main__":
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k_final = H.ledger_count() + 4
    days = H.load_days("MNQ")
    bars, tdays = H.bars_from_days(days, "all"), [d["tday"] for d in days]
    print(f"MNQ {len(days)} days; k after this round = {k_final}\n")
    rows = []
    for k in [2.0, 2.5]:
        for tg in ["1 SD back", "range edge"]:
            sig = stdv_signals(days, k, tg)
            tr = H.resolve_bracket(sig, bars, "MNQ")
            rows.append(H.test_idea(f"MNQ Asian-range STDV fade, {k} SD, target {tg}", tr, tdays, "MNQ", k_final))
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(H.ledger_rows(rows, "Round 127 (video, pre-registered)", commit)) + "\n")
    with open(os.path.join(H.HERE, "round127_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n==== {sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()} ====")
