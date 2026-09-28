"""
Round 196: asked directly, after the earnings-calendar data source turned out
to be a dead end (Finnhub's free tier only serves a rolling near-term window,
confirmed by direct API test -- no usable historical depth), to try "supply
and demand" -- the classic retail zone-trading concept -- for a quick pass.

This is a genuinely new construction, not a relabel of anything already in
the 371-row ledger. It is superficially similar to three things already
tested and already failed, but formally distinct from each:
  - ICT Order Blocks (Rounds 159/160/210): defined by a SINGLE candle (the
    last opposing candle before an impulsive move), not a multi-bar base.
  - Fair Value Gaps (Rounds 150/160): a pure 3-candle PRICE GAP, no base or
    impulse-strength requirement at all.
  - Support/resistance swing-level bounce (Round 130): a generic swing high/
    low fade, undirected by any prior impulsive move away from the level.
Supply/demand zones specifically require (a) a tight multi-bar consolidation
("base"), (b) a subsequently STRONG, fast break away from it (not just any
swing point), and (c) trade WITH the original break's direction on the
zone's first retest (continuation, not a fade) -- a different combination of
conditions from all three.

Rule (standard textbook description; thresholds set from signal COUNTS only,
before any P&L was looked at -- see the dry-run note below): on NQ/ES/GC/SI
1-minute Databento RTH bars (concatenated, causal 20-bar rolling average
range as the reference ATR, shifted 1 -- no look-ahead), a BASE is 3
consecutive bars each with range <= 0.6x that ATR. An IMPULSE is confirmed if,
within the next 5 bars (same trading day), price moves >= 1.5x ATR beyond the
base's near edge in one direction WITHOUT any bar in between closing back
inside the base range -- a clean break. The zone is [base_low, base_high];
type = demand (long bias) if the impulse was up, supply (short bias) if
down. The FIRST bar afterward (same day only) whose range touches back into
the zone triggers a trade in the impulse's original direction, entry at that
bar's close, stop 2 ticks beyond the zone's far edge, target 2R, flat by
16:00 (Broker-legal, `idea_harness.resolve_bracket`'s standard exits). Only
the first retest per zone counts; a zone that is never retested by the
session's close simply produces no trade (zones don't carry across days).

Dry-run note: the first, stricter guess (0.5x base / 2.0x impulse, the more
"classic" textbook tightness) produced only 8 NQ signals over 1,806 days --
too few to mean anything (this ledger's own standard, e.g. Round 161's
n=4-33 caveat). Loosened once, uniformly across all 4 symbols, to the
0.6x/1.5x values above based ONLY on the resulting signal counts (265-3,894
across symbols, no P&L examined at either setting) before running for real
-- the same dry-run "hand-check before running" step every other round in
this ledger already does, not a re-pick after seeing results.

Step 0, honest before running: this ledger's track record on discretionary
retail/ICT-style zone concepts is 0 for everything tried so far -- Order
Blocks, FVG (plain and with all 5 "secrets"), Silver Bullet, support/
resistance bounce, and all of their inversions. Supply/demand zones are the
same style of concept (a discretionary visual pattern formalized into a
fixed rule) and there is no basis here for a higher prior than those had.
Tested because it's a genuinely new construction and was asked for directly,
not because the odds have improved.

4 variants (one per symbol). Ledger k=371 -> 375; OOS bar 1 - 0.01/375 at the
last variant.

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
ATR_WINDOW = 20
BASE_BARS = 3
BASE_MULT = 0.6
IMPULSE_WINDOW = 5
IMPULSE_MULT = 1.5
TICK_BUFFER = 2
RR = 2.0


def build_signals(days, tick):
    sess = pd.concat([d["session"] for d in days if not d["session"].empty]).sort_index()
    hi, lo, cl = sess["high"].values, sess["low"].values, sess["close"].values
    day = sess["tday"].values
    ts = sess.index.values
    rng = hi - lo
    atr = pd.Series(rng).rolling(ATR_WINDOW, min_periods=ATR_WINDOW).mean().shift(1).values
    n = len(sess)
    out = []
    i = BASE_BARS - 1
    while i < n - 1:
        a = atr[i]
        if not (a > 0) or day[i - (BASE_BARS - 1)] != day[i]:
            i += 1
            continue
        base_lo_all = lo[i - BASE_BARS + 1: i + 1]
        base_hi_all = hi[i - BASE_BARS + 1: i + 1]
        base_ok = bool(np.all(rng[i - BASE_BARS + 1: i + 1] <= BASE_MULT * a))
        if base_ok:
            base_lo, base_hi = float(base_lo_all.min()), float(base_hi_all.max())
            zone_type, j_confirm = None, None
            j_end = min(i + 1 + IMPULSE_WINDOW, n)
            for j in range(i + 1, j_end):
                if day[j] != day[i]:
                    break
                if hi[j] - base_hi >= IMPULSE_MULT * a and lo[i + 1: j + 1].min() >= base_lo:
                    zone_type, j_confirm = 1, j
                    break
                if base_lo - lo[j] >= IMPULSE_MULT * a and hi[i + 1: j + 1].max() <= base_hi:
                    zone_type, j_confirm = -1, j
                    break
            if zone_type is not None:
                for k in range(j_confirm + 1, n):
                    if day[k] != day[i]:
                        break
                    if lo[k] <= base_hi and hi[k] >= base_lo:
                        sl = base_lo - TICK_BUFFER * tick if zone_type == 1 else base_hi + TICK_BUFFER * tick
                        entry = cl[k]
                        dist = abs(entry - sl)
                        if dist > 0:
                            tp = entry + zone_type * RR * dist
                            out.append((ts[k], zone_type, entry, sl, tp))
                        break
        i += 1
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
        name = f"Supply/demand zone retest continuation (2R), {sym}, Databento"
        r = H.test_idea(name, tr, all_days, sym, k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 196 (pre-registered, new idea class: supply/demand zone retest)",
                               commit, date="2026-09-28")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round196_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
