"""
Round 221 (pre-registered, new idea class, 2026-09-30): opening-range
FAILURE fade -- continuing the "new branch" search after Round 220's
money-flow divergence found no edge.

Gap found before writing this: every opening-range-breakout variant in
this ledger (C2 NR7 ORB, VCORB x many volume-filter/target/instrument
combos, N1/N2/N3 level breakouts) trades CONTINUATION -- with the break,
never against it. Separately, Round 17 (pre-dates idea_harness/the
ledger) already tested a sweep-and-reverse fade, but on PRIOR-DAY
high/low as the reference level, and found it net negative on both
instruments ("breakout-and-continue was...one of the most unambiguous
negative results of the whole search...sweep-and-reverse...still net
negative on both instruments after real costs," journal 2026-09-26).

This tests the same sweep-and-reverse LOGIC Round 17 used, but on a
different, genuinely untested reference level: TODAY's own opening range
(first 15 or 30 minutes of RTH), not yesterday's high/low. This is the
natural "does the breakout hold" question for the exact ORB construction
this ledger has tested many times for continuation, asked for the first
time in the other direction: rule, causal throughout -- track the
morning's opening-range high/low, then watch for the first CLOSE beyond
one side (a breakout) followed by a later CLOSE back inside that same
side (a failure) -- fade in the reversal direction at that close. Stop =
the day's own most extreme point reached during the failed breakout (the
actual sweep extreme, same convention as Round 17), no target, flat by
16:00 ET, one trade per side per day (a chatty/choppy day can produce a
failed-upside AND a failed-downside signal, each independently gated so
neither re-fires once taken).

MNQ + MGC, $300 risk, real commission + 2-tick slippage -- same real
mechanics as every idea_harness round, so this compares directly against
every existing ORB/VCORB continuation number already on record.

Step 0, honest before running: opening-range levels are looked at by a lot
of real intraday traders, so a pure fade on them is not exotic -- it is
tested here because the SPECIFIC construction (this session's own OR,
sweep-and-reverse logic, idea_harness's real bootstrap/OOS bar) is
genuinely absent from this ledger, not because prior odds are good. Round
17's own result on the closely related prior-day-level version was
negative.

2 variants (OR window 15min, 30min). Ledger k=386 -> 387; OOS bar
1 - 0.01/387 at the last variant.

Candidate (each variant): idea_harness.test_idea's own rule (positive net
and gross; IS P(edge>0) >= 0.95; OOS P(edge>0) >= the bar at that variant's
k).
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H

FLAT_TIME = dt.time(16, 0)
RTH_OPEN = dt.time(9, 30)

_DAYS_CACHE, _BARS_CACHE = {}, {}


def cached_days(sym):
    if sym not in _DAYS_CACHE:
        _DAYS_CACHE[sym] = H.load_days(sym)
    return _DAYS_CACHE[sym]


def cached_bars(sym):
    if sym not in _BARS_CACHE:
        _BARS_CACHE[sym] = H.bars_from_days(cached_days(sym), "all")
    return _BARS_CACHE[sym]


def signals(days, symbol, or_minutes):
    tick = H.TK[symbol]
    end_or = (dt.datetime(2000, 1, 1, 9, 30) + dt.timedelta(minutes=or_minutes)).time()
    out = []
    for d in days:
        s = d["session"]
        t = s.index.time
        opening = s[(t >= RTH_OPEN) & (t < end_or)]
        if len(opening) < 3:
            continue
        or_hi, or_lo = opening["high"].max(), opening["low"].min()
        if or_hi <= or_lo:
            continue
        rest = s[t >= end_or]
        if len(rest) < 3:
            continue
        hi_r, lo_r, cl_r = rest["high"].values, rest["low"].values, rest["close"].values
        idx_r = rest.index
        swept_hi = swept_lo = done_hi = done_lo = False
        day_max_h, day_min_l = or_hi, or_lo
        for i in range(len(rest)):
            day_max_h = max(day_max_h, hi_r[i])
            day_min_l = min(day_min_l, lo_r[i])
            if hi_r[i] > or_hi:
                swept_hi = True
            if lo_r[i] < or_lo:
                swept_lo = True
            if swept_hi and not done_hi and cl_r[i] <= or_hi:
                out.append((idx_r[i], -1, cl_r[i], day_max_h + tick, np.nan))
                done_hi = True
            if swept_lo and not done_lo and cl_r[i] >= or_lo:
                out.append((idx_r[i], 1, cl_r[i], day_min_l - tick, np.nan))
                done_lo = True
    return pd.DataFrame(out, columns=["ts", "direction", "entry", "sl", "tp"])


def build_trades(or_minutes):
    parts = []
    for sym in ("MNQ", "MGC"):
        days, bars = cached_days(sym), cached_bars(sym)
        sig = signals(days, sym, or_minutes)
        tr = H.resolve_bracket(sig, bars, sym, flat_time=FLAT_TIME)
        tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
        parts.append(tr)
    return pd.concat(parts, ignore_index=True)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    grid = [(15, "Opening-range (15-min) failure fade, sweep-and-reverse, hold to close, MNQ+MGC"),
            (30, "Opening-range (30-min) failure fade, sweep-and-reverse, hold to close, MNQ+MGC")]

    if dry:
        for orm, label in grid:
            tr = build_trades(orm)
            print(f"{label}: {len(tr)} trades")
        print("\n--dry-run: counts only (trades ARE resolved for real, just not logged). Hand-check before the real run.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    all_days_mnq_mgc = sorted(set(d["tday"] for d in cached_days("MNQ")) | set(d["tday"] for d in cached_days("MGC")))

    rows = []
    for orm, label in grid:
        k = H.ledger_count() + 1
        tr = build_trades(orm)
        r = H.test_idea(label, tr, all_days_mnq_mgc, "MNQ", k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 221 (pre-registered, new idea class: opening-range failure fade)",
                               commit, date="2026-09-30")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round221_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
