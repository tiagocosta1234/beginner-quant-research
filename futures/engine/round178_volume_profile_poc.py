"""
Round 178: a genuinely new idea class -- Volume Profile / Point of Control
(POC) reversion, from Auction Market Theory (Steidlmayer, CBOT, 1980s).
Checked IDEA_LEDGER.md first (k=288): every level tested so far (round
numbers, prior-day high/low, overnight high/low, the opening range) is a
PRICE level. POC is different in kind -- it's the price where the MOST
VOLUME traded the prior session, found from the session's own volume-
weighted price distribution, not from price extremes alone. The AMT
thesis: price is drawn back toward yesterday's highest-volume (most
"accepted") price when today opens meaningfully away from it -- a magnet
effect, not a breakout-continuation or simple mean-reversion-to-a-high/low
idea.

Rule: previous session's POC = the tick-binned price level with the most
cumulative RTH volume. At today's open, if |open - POC| >= S (S = 0.15x
the 20-day average session range, the same stop-sizing convention Round
147/148 already use for this same data), trade TOWARD POC: long if POC is
above the open, short if below. Stop = S beyond the open (away from POC);
target = the POC level itself (not a fixed R-multiple -- the AMT thesis is
literally "price returns to this level", so the level itself is the exit,
whatever multiple of S that happens to be that day). Flat by 16:00 ET if
neither hit. ES, NQ, GC, SI (Databento, full history).

Step 0, honest before running: Market Profile/Volume Profile is a
established professional technique (still taught, still used by CME's own
educational materials) -- if POC-reversion were a clean, mechanically
exploitable rule at the daily-open level, professional volume-profile
traders would already be capturing it. Tested because it's a genuinely
different DATA DIMENSION (the volume-weighted price distribution) from
every level this ledger has tried, not because prior odds are good.

4 variants (one per symbol). Ledger k=288 -> 292; OOS bar 1 - 0.01/292 at
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


def session_poc(session, tick):
    if session.empty:
        return np.nan
    px = np.round(session["close"] / tick).astype(int) * tick
    profile = pd.Series(session["vol"].values, index=px.values).groupby(level=0).sum()
    return float(profile.idxmax())


def build_signals(days, tick):
    ranges = pd.Series({d["tday"]: (d["session"]["high"].max() - d["session"]["low"].min())
                        for d in days if not d["session"].empty})
    avg_range = ranges.rolling(RANGE_WINDOW, min_periods=10).mean().shift(1)

    out, prev_poc = [], None
    for d in days:
        s = d["session"]
        S = avg_range.get(d["tday"], np.nan)
        if s.empty or prev_poc is None or not (S > 0):
            prev_poc = session_poc(s, tick)
            continue
        open_px = s["open"].iloc[0]
        dist = prev_poc - open_px
        stop_mult = 0.15
        if abs(dist) >= stop_mult * S:
            direction = int(np.sign(dist))
            sl = open_px - direction * stop_mult * S
            out.append((s.index[0], direction, open_px, sl, prev_poc))
        prev_poc = session_poc(s, tick)
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
            print(f"{sym}: {len(tr)} trades")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    rows = []
    for sym in ("ES", "NQ", "GC", "SI"):
        k = H.ledger_count() + 1
        tr, days = build_trades(sym)
        all_days = [d["tday"] for d in days]
        name = f"Volume Profile POC reversion, {sym}, Databento"
        r = H.test_idea(name, tr, all_days, sym, k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 178 (pre-registered, new idea class: volume profile POC reversion)",
                               commit, date="2026-09-28")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round178_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
