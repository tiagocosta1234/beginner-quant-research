"""
Round 128: ICT high- vs low-resistance liquidity (HRL vs LRL) as a direction call.

Prompted by NQNoah's "The ONLY 2 Concepts You Need To Become Profitable (HRL vs.
LRL)" (youtube.com/watch?v=TNjZ7iFT4Yk, 2026-09-17). YouTube blocked the video
here and the description states no rules, so this tests the standard idea:
price runs easily toward low-resistance liquidity (a level it passed through
quickly) and grinds through high-resistance areas (where it spent time).
Pre-registered -- committed before any result was run.

  liquidity:   the previous RTH session's high (PDH) and low (PDL), same contract
               (roll days, where the contract changes, are skipped)
  resistance:  time at price in the previous session -- 1-minute bars covering
               each 1-point bucket -- averaged over the path from today's open to
               each level; the lower-density side is the LRL
  entry:       at the 09:30 bar's close (the open), if it is between PDL and PDH,
               toward the LRL side
  target:      that level (PDH or PDL)
  stop:        1:1 (the same distance the other way), or at the other level
  filter:      all days, or only days where the HRL path is >= 1.5x denser
  flat at 16:00; both distances >= 8 ticks; $300 risk
  variants:    stop in {1:1, other level} x filter in {all days, ratio >= 1.5}

idea_harness, 24-hour contract files. 4 variants take the ledger from k=55 to
k=59: a candidate needs positive net and before-cost expectancy, IS P(edge>0)
>= 0.95 and OOS P(edge>0) >= 1 - 0.01/59.
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
from round11_fvg_bias import TICK_SIZE

MIN_TICKS = 8


def time_at_price(session, lo_edge, step=1.0):
    """Bars covering each `step`-point bucket, bucket 0 starting at lo_edge."""
    lo = np.floor((session["low"].values - lo_edge) / step).astype(int)
    hi = np.floor((session["high"].values - lo_edge) / step).astype(int)
    n = hi.max() + 2
    diff = np.zeros(n + 1)
    np.add.at(diff, lo, 1)
    np.add.at(diff, hi + 1, -1)
    return np.cumsum(diff)[:n]


def path_density(tap, lo_edge, a, b, step=1.0):
    i, j = sorted((int((a - lo_edge) // step), int((b - lo_edge) // step)))
    i, j = max(i, 0), min(j, len(tap) - 1)
    return float(tap[i:j + 1].mean()) if j >= i else np.nan


def signals(days, stop, min_ratio):
    tick, out = TICK_SIZE["MNQ"], []
    for prev, d in zip(days[:-1], days[1:]):
        if prev["contract"] != d["contract"]:
            continue
        ps, s = prev["session"], d["session"]
        first = s[s.index.time == dt.time(9, 30)]
        if first.empty:
            continue
        ts, o = first.index[0], float(first["close"].iloc[0])
        pdh, pdl = ps["high"].max(), ps["low"].min()
        if not (pdl < o < pdh):
            continue
        tap = time_at_price(ps, pdl)
        dens_up, dens_dn = path_density(tap, pdl, o, pdh), path_density(tap, pdl, o, pdl)
        if np.isnan(dens_up) or np.isnan(dens_dn) or min(dens_up, dens_dn) <= 0:
            continue
        dd = 1 if dens_up < dens_dn else -1
        if max(dens_up, dens_dn) / min(dens_up, dens_dn) < min_ratio:
            continue
        tp = pdh if dd == 1 else pdl
        sl = o - dd * abs(tp - o) if stop == "1:1" else (pdl if dd == 1 else pdh)
        if abs(tp - o) >= MIN_TICKS * tick and abs(o - sl) >= MIN_TICKS * tick:
            out.append((ts, dd, o, sl, tp))
    return pd.DataFrame(out, columns=["ts", "direction", "entry", "sl", "tp"])


if __name__ == "__main__":
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k_final = H.ledger_count() + 4
    days = H.load_days("MNQ")
    bars, tdays = H.bars_from_days(days, "session"), [d["tday"] for d in days]
    print(f"MNQ {len(days)} days; k after this round = {k_final}\n")
    rows = []
    for stop in ["1:1", "other level"]:
        for ratio in [1.0, 1.5]:
            sig = signals(days, stop, ratio)
            tr = H.resolve_bracket(sig, bars, "MNQ")
            label = "all days" if ratio == 1.0 else f"HRL path >= {ratio}x denser"
            rows.append(H.test_idea(f"MNQ trade toward LRL at open, stop {stop}, {label}", tr, tdays, "MNQ", k_final))
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(H.ledger_rows(rows, "Round 128 (video, pre-registered)", commit)) + "\n")
    with open(os.path.join(H.HERE, "round128_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n==== {sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()} ====")
