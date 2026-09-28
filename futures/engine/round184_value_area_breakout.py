"""
Round 184: a genuinely distinct extension of the Market Profile framework
that produced this ledger's strongest surviving lead (Round 178/183's POC
reversion). POC is a single price (the most-traded level); the Value Area
(VAH/VAL) is the RANGE around it that contains ~70% of a session's volume
-- the "fair value" zone. Different hypothesis from POC reversion: instead
of "price is drawn back to the busiest price," this tests "when today opens
OUTSIDE yesterday's fair-value range, does it keep going (a trend/breakout
day) or snap back inside (a rejection/balance day)" -- a real, named
distinction in Market Profile trading (Steidlmayer/Dalton), never tested
in this ledger. Both directions pre-registered since the theory itself
argues both ways depending on regime (trend days vs balance days).

Rule: build yesterday's session volume profile exactly as Round 178 does
(tick-binned RTH volume), then expand outward from the POC, greedily adding
whichever adjacent price level has more volume, until >=70% of the
session's total volume is captured -- the standard value-area algorithm.
VAH/VAL are the resulting range's top and bottom. At today's open:
  if open > VAH: Continuation -> long (bet the breakout keeps going);
                 Rejection -> short (bet it snaps back into value).
  if open < VAL: mirror.
No trade if open falls inside yesterday's value area (nothing to test).
Stop = the OPPOSITE side of the value area from the breakout (a defined,
theory-consistent invalidation: continuation is wrong if price re-enters
and crosses all the way through value; rejection is wrong if price pushes
further away instead of returning). Target: for Continuation, 1x the
value-area width beyond the breakout; for Rejection, the POC itself
(matching Round 178's own target definition). Flat by 16:00 ET.

Step 0, honest before running: Market Profile is an established, decades-
old professional framework (still taught via CME's own materials) -- if
value-area breakout/rejection were this cleanly exploitable at the daily-
open level, professional Market Profile traders would already be trading
it. Tested because it's a different signal (range exit, not reversion to
a point) built on the same real data dimension (volume-weighted price
distribution) that already produced this ledger's most robust lead, not
because prior odds are good.

4 symbols x 2 directions = 8 variants. ES/NQ/GC/SI, Databento. Ledger
k=309 -> 317; OOS bar 1 - 0.01/317 at the last variant.

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
VA_PCT = 0.70


def session_value_area(session, tick):
    if session.empty:
        return np.nan, np.nan, np.nan
    px = np.round(session["close"] / tick).astype(int) * tick
    profile = pd.Series(session["vol"].values, index=px.values).groupby(level=0).sum().sort_index()
    if len(profile) < 2:
        v = float(profile.index[0])
        return v, v, v
    poc = profile.idxmax()
    levels = profile.index.to_list()
    poc_idx = levels.index(poc)
    target = VA_PCT * profile.sum()
    lo = hi = poc_idx
    vol_sum = profile.iloc[poc_idx]
    while vol_sum < target and (lo > 0 or hi < len(levels) - 1):
        vol_below = profile.iloc[lo - 1] if lo > 0 else -1
        vol_above = profile.iloc[hi + 1] if hi < len(levels) - 1 else -1
        if vol_below >= vol_above:
            lo -= 1
            vol_sum += profile.iloc[lo]
        else:
            hi += 1
            vol_sum += profile.iloc[hi]
    return float(poc), float(levels[lo]), float(levels[hi])  # poc, val, vah


def build_signals_df(days, tick, continuation):
    rows, prev = [], None
    for d in days:
        s = d["session"]
        if s.empty:
            continue
        if prev is not None:
            poc, val, vah = prev
            open_px = s["open"].iloc[0]
            va_width = vah - val
            if va_width > 0:
                if open_px > vah:
                    direction = 1 if continuation else -1
                    sl = val if continuation else open_px + (open_px - vah)
                    tp = open_px + va_width if continuation else poc
                    rows.append((s.index[0], direction, open_px, sl, tp))
                elif open_px < val:
                    direction = -1 if continuation else 1
                    sl = vah if continuation else open_px - (val - open_px)
                    tp = open_px - va_width if continuation else poc
                    rows.append((s.index[0], direction, open_px, sl, tp))
        prev = session_value_area(s, tick)
    return pd.DataFrame(rows, columns=["ts", "direction", "entry", "sl", "tp"])


def build_trades(sym, continuation):
    days = load_days_databento(sym)
    bars = pd.concat([d[k] for d in days for k in ("on", "session")]).sort_index()
    sig = build_signals_df(days, H.TK[sym], continuation)
    tr = H.resolve_bracket(sig, bars, sym, flat_time=FLAT_TIME)
    tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
    return tr, days


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv

    if dry:
        for sym in ("ES", "NQ", "GC", "SI"):
            for cont in (True, False):
                tr, days = build_trades(sym, cont)
                print(f"{sym} {'continuation' if cont else 'rejection'}: {len(tr)} trades")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    rows = []
    for sym in ("ES", "NQ", "GC", "SI"):
        for cont in (True, False):
            k = H.ledger_count() + 1
            tr, days = build_trades(sym, cont)
            all_days = [d["tday"] for d in days]
            label = "continuation" if cont else "rejection"
            name = f"Value Area breakout {label}, {sym}, Databento"
            r = H.test_idea(name, tr, all_days, sym, k)
            rows.append(r)
            lines = H.ledger_rows([r], "Round 184 (pre-registered, new idea class: value-area breakout/rejection)",
                                   commit, date="2026-09-28")
            with open(H.LEDGER, "a", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round184_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
