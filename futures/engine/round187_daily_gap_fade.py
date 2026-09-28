"""
Round 187: after Round 186's combined Market Profile leads still didn't pass
the pass-speed gate at any sizing tried (best <=15-day pass rate ~15.9%,
worse than a zero-edge coin flip's 20%), explicitly asked to try something
SIMPLER -- POC/Value-Area construction needs volume-weighted binning and an
iterative expansion algorithm; this idea needs two price points and a
rolling standard deviation.

Rule: the classic "gap fade". Overnight gap = today's RTH open minus
yesterday's RTH close. If |gap| >= GAP_Z x the 20-day rolling SD of that
same gap series (shifted 1, no look-ahead -- same z-score convention Round
142 used for weekend-gap fades), trade AGAINST the gap's sign (long a
gap-down, short a gap-up) from the open, on the AMT-adjacent overreaction
idea that an unusually large overnight move partly reverts during the
session. Stop = 0.15x the 20-day average session range beyond the open
(the same stop-sizing convention Round 147/148/178 already use for this
exact data -- not re-picked). No target; flat by 16:00 ET (Broker-legal).
ES, NQ, GC, SI, Databento full history.

This is NOT the same test as Round 142's "CME gaps fill", which only fired
after a >=3-CALENDAR-DAY break (weekends/holidays), used Yahoo daily
18:00-ET-reopen bars, and lost. This fires on EVERY trading day's ordinary
overnight gap, using clean 1-minute Databento data and genuinely
flat-at-close intraday resolution -- a different, and more common,
occurrence of the same underlying idea, worth checking on its own rather
than assuming Round 142's result already covers it.

Step 0, honest before running: gap fades are folk-known and heavily
arbitraged; if this were a large, clean edge at the daily-open level,
professional gap-traders would already be capturing it. Tested anyway
because it is a genuinely simple, previously-untested rule (a new idea
class per the standing "keep testing new idea classes" instruction), not
because prior odds are good.

4 variants (one per symbol). Ledger k=322 -> 326; OOS bar 1 - 0.01/326 at
the last variant.

Candidate: idea_harness.test_idea's own rule (positive net and gross; IS
P(edge>0) >= 0.95; OOS P(edge>0) >= the bar at that variant's k).
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
from round171_databento_orb_replication import load_days_databento

FLAT_TIME = dt.time(16, 0)
RANGE_WINDOW = 20
GAP_Z = 0.5
STOP_MULT = 0.15


def build_signals(days, tick):
    ranges = pd.Series({d["tday"]: (d["session"]["high"].max() - d["session"]["low"].min())
                        for d in days if not d["session"].empty})
    avg_range = ranges.rolling(RANGE_WINDOW, min_periods=10).mean().shift(1)

    opens = pd.Series({d["tday"]: d["session"]["open"].iloc[0] for d in days if not d["session"].empty})
    closes = pd.Series({d["tday"]: d["session"]["close"].iloc[-1] for d in days if not d["session"].empty})
    gap = opens - closes.shift(1)
    gap_sd = gap.rolling(RANGE_WINDOW, min_periods=10).std().shift(1)

    out = []
    for d in days:
        s = d["session"]
        tday = d["tday"]
        if s.empty:
            continue
        S = avg_range.get(tday, np.nan)
        g = gap.get(tday, np.nan)
        sd = gap_sd.get(tday, np.nan)
        if not (S > 0) or not (sd > 0) or pd.isna(g):
            continue
        if abs(g) >= GAP_Z * sd:
            direction = -int(np.sign(g))  # fade the gap
            open_px = s["open"].iloc[0]
            sl = open_px - direction * STOP_MULT * S
            out.append((s.index[0], direction, open_px, sl, np.nan))
    return pd.DataFrame(out, columns=["ts", "direction", "entry", "sl", "tp"])


def build_trades(sym):
    days = load_days_databento(sym)
    bars = pd.concat([d[k] for d in days for k in ("on", "session")]).sort_index()
    sig = build_signals(days, H.TK[sym])
    tr = H.resolve_bracket(sig, bars, sym, flat_time=FLAT_TIME)
    tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
    return tr, days


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv

    if dry:
        for sym in ("ES", "NQ", "GC", "SI"):
            tr, days = build_trades(sym)
            print(f"{sym}: {len(tr)} trades of {len(days)} days")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    rows = []
    for sym in ("ES", "NQ", "GC", "SI"):
        k = H.ledger_count() + 1
        tr, days = build_trades(sym)
        all_days = [d["tday"] for d in days]
        name = f"Daily overnight gap fade, {sym}, Databento"
        r = H.test_idea(name, tr, all_days, sym, k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 187 (pre-registered, new idea class: simple daily gap fade)",
                               commit, date="2026-09-28")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round187_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
