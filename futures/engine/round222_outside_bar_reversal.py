"""
Round 222 (pre-registered, new idea class, 2026-09-30): outside-bar
(engulfing-candle) reversal -- continuing the new-branch search after
Round 220 (money-flow divergence) and Round 221 (opening-range failure
fade) both found no edge.

Gap found before writing this: none of the 387 prior ledger rows are a
pure CANDLESTICK-PATTERN signal. Every idea tested so far is level-based
(ORB, prior-day, round numbers, supply/demand zones), volume-based
(money-flow, volume filters), statistical (z-score, STDV, autocorrelation
via TSMOM/EMA), or calendar-based. Outside bars (a bar whose range fully
engulfs the immediately preceding bar) are one of the oldest, most
retail-known technical concepts (Bulkowski-style candlestick encyclopedia
entries, ~40+ years of retail use) and were never formalized here.

Rule, deliberately parameter-light to avoid smuggling in tuned degrees of
freedom: on causally-resampled HTF bars (5-min or 15-min, built per RTH
session so nothing crosses a day boundary), bar i is an "outside bar" if
high[i] > high[i-1] AND low[i] < low[i-1] (it fully engulfs the prior
bar's range, the literal engulfing-candle definition). Direction = sign of
that bar's own close vs. its own open (which way the outside bar itself
resolved). Entry at the outside bar's close, stop = that SAME bar's own
opposite extreme (its low for a long, its high for a short -- a tight,
structurally-motivated stop straight from the pattern's own range, no
extra tuned multiplier), no target, flat by 16:00 ET, resolved against the
real underlying 1-minute bars exactly like every other idea_harness round
(entries open on the next real 1-min bar after the signal bar's close).

MNQ + MGC, $300 risk, real commission + 2-tick slippage.

Step 0, honest before running: this is possibly the single most retail-
famous pattern in all of technical analysis, which is itself a reason for
skepticism (anything this well-known and mechanical is a natural target
for arbitrage) -- tested because it is a genuinely different signal TYPE
(pure candlestick geometry, not price level/volume/statistics), not
because prior odds are good.

2 variants (HTF 5-min, 15-min). Ledger k=388 -> 389; OOS bar 1 - 0.01/389
at the last variant.

Candidate (each variant): idea_harness.test_idea's own rule (positive net
and gross; IS P(edge>0) >= 0.95; OOS P(edge>0) >= the bar at that variant's
k).
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
from round11_fvg_bias import resample_causal

FLAT_TIME = dt.time(16, 0)

_DAYS_CACHE, _BARS_CACHE = {}, {}


def cached_days(sym):
    if sym not in _DAYS_CACHE:
        _DAYS_CACHE[sym] = H.load_days(sym)
    return _DAYS_CACHE[sym]


def cached_bars(sym):
    if sym not in _BARS_CACHE:
        _BARS_CACHE[sym] = H.bars_from_days(cached_days(sym), "all")
    return _BARS_CACHE[sym]


def signals(days, symbol, rule):
    tick = H.TK[symbol]
    out = []
    for d in days:
        htf = resample_causal(d["session"][["open", "high", "low", "close"]], rule)
        if len(htf) < 3:
            continue
        o, h, l, c = htf["open"].values, htf["high"].values, htf["low"].values, htf["close"].values
        idx = htf.index
        for i in range(1, len(htf)):
            if h[i] > h[i - 1] and l[i] < l[i - 1] and c[i] != o[i]:
                dd = 1 if c[i] > o[i] else -1
                entry = c[i]
                sl = (l[i] - tick) if dd == 1 else (h[i] + tick)
                out.append((idx[i], dd, entry, sl, np.nan))
    return pd.DataFrame(out, columns=["ts", "direction", "entry", "sl", "tp"])


def build_trades(rule):
    parts = []
    for sym in ("MNQ", "MGC"):
        days, bars = cached_days(sym), cached_bars(sym)
        sig = signals(days, sym, rule)
        tr = H.resolve_bracket(sig, bars, sym, flat_time=FLAT_TIME)
        tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
        parts.append(tr)
    return pd.concat(parts, ignore_index=True)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    grid = [("5min", "Outside-bar (engulfing) reversal, 5-min HTF, hold to close, MNQ+MGC"),
            ("15min", "Outside-bar (engulfing) reversal, 15-min HTF, hold to close, MNQ+MGC")]

    if dry:
        for rule, label in grid:
            tr = build_trades(rule)
            print(f"{label}: {len(tr)} trades")
        print("\n--dry-run: counts only (trades ARE resolved for real, just not logged). Hand-check before the real run.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    all_days_mnq_mgc = sorted(set(d["tday"] for d in cached_days("MNQ")) | set(d["tday"] for d in cached_days("MGC")))

    rows = []
    for rule, label in grid:
        k = H.ledger_count() + 1
        tr = build_trades(rule)
        r = H.test_idea(label, tr, all_days_mnq_mgc, "MNQ", k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 222 (pre-registered, new idea class: outside-bar/engulfing-candle reversal)",
                               commit, date="2026-09-30")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round222_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
