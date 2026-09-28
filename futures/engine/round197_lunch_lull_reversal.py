"""
Round 197: continuing the idea-hunt after Round 196 closed supply/demand
zones (0/4). Checked IDEA_LEDGER.md first (k=375) -- no round has tested the
NY "lunch doldrums" specifically. This is a different granularity from
everything already tried: not a calendar-date rule (gap fade/continuation,
quad-witching), not a volume-profile construction (POC/VA), not a
single-candle/gap pattern (Order Blocks/FVG/supply-demand), and not the
09:30 open itself (ORB, Round 171) -- a specific INTRADAY SESSION SEGMENT
(the low-liquidity midday window) with its own well-known floor-trading
folklore: moves made 12:00-13:30 ET, when institutional participation
thins out, are considered less "informed" than moves made in the morning or
afternoon, and are expected to partially revert once normal volume returns.

Worth noting before running: this ledger's mean-reversion/fade concepts have
had genuinely mixed results, not a uniform 0 -- Connors RSI(2), IBS, and the
dip-buy ensemble (Round 166) all show small real edges, while gap fade
(Round 187), VIX-backwardation fade (Round 165) and S/R bounce (Round 130)
failed outright. This is a somewhat better-motivated test than Round 196's
pattern concepts, not because a lunch-specific effect is expected to be
large, but because "fade an isolated move made on thin liquidity" is closer
in kind to this ledger's few actual survivors than to its many outright
losers.

Rule: on NQ/ES/GC/SI 1-minute Databento RTH bars, the MORNING range is the
session high/low from open (09:30) through 11:59 ET. During the LUNCH window
(12:00-13:29 ET), the first bar that closes beyond the morning range (a new
session high or low made specifically during this thin window) triggers a
fade: short a new lunch-window high, long a new lunch-window low, entry at
that bar's close, stop 2 ticks beyond the lunch extreme, target 1.5R, flat
by 16:00 (`idea_harness.resolve_bracket`'s standard exits). Only the first
such break per day counts (matching the "first signal per day" convention
Round 125's Judas swing self-test already uses in this same harness).

4 variants (one per symbol). Ledger k=375 -> 379; OOS bar 1 - 0.01/379 at
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
MORNING_END = dt.time(11, 59)
LUNCH_START = dt.time(12, 0)
LUNCH_END = dt.time(13, 29)
TICK_BUFFER = 2
RR = 1.5


def build_signals(days, tick):
    out = []
    for d in days:
        s = d["session"]
        if s.empty:
            continue
        t = s.index.time
        morning = s[(t <= MORNING_END)]
        lunch = s[(t >= LUNCH_START) & (t <= LUNCH_END)]
        if morning.empty or lunch.empty:
            continue
        m_hi, m_lo = morning["high"].max(), morning["low"].min()
        hi, lo, cl = lunch["high"].values, lunch["low"].values, lunch["close"].values
        for i in range(len(lunch)):
            broke_up = hi[i] > m_hi
            broke_dn = lo[i] < m_lo
            if broke_up or broke_dn:
                direction = -1 if broke_up else 1
                extreme = hi[i] if broke_up else lo[i]
                entry = cl[i]
                sl = extreme - direction * TICK_BUFFER * tick  # buffer further beyond the extreme than entry
                dist = abs(entry - sl)
                if dist > 0:
                    tp = entry + direction * RR * dist
                    out.append((lunch.index[i], direction, entry, sl, tp))
                break
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
        name = f"Lunch-lull (12:00-13:29 ET) extreme fade, {sym}, Databento"
        r = H.test_idea(name, tr, all_days, sym, k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 197 (pre-registered, new idea class: NY lunch-lull session-segment fade)",
                               commit, date="2026-09-28")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round197_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
