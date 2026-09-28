"""
Round 189: /watch'd Revelio Trading's "How to identify the best Fair Value Gaps
(backed by data)" (YouTube qkzJknH5IJk) for real this time -- Round 150 (2026-09-26)
could only get the description (YouTube blocked the cloud session), so its
"secrets" (displacement, VWAP side, killzones, 50% entry) were this repo's own
guess, explicitly flagged as "not a reproduction of the video." CURRENT_STATE.md
asked to re-watch locally and test the video's own five if they differ -- they do,
completely: the video's actual five secrets are (1) gap SIZE >= a threshold,
(2) three-candle COLOR consistency, (3) a TREND filter, (4) EQUILIBRIUM
(discount/premium zone, the 50% level of the move), and (5) entry method (simple
close-of-touch-candle beat two fancier alternatives -- the video's own data already
settled this one, so only the winning entry is used here, not re-tested). Also
different: the video's basic strategy uses 1:2 R:R with a MARKET entry at the
touching candle's CLOSE, not a limit order at the gap's edge (Round 150's method).

Rule, following the video's own description literally:
  FVG: candle1.high < candle3.low (bullish) or candle1.low > candle3.high (bearish),
       >= 1 tick.
  First touch only: scan forward from formation for the first candle whose range
       reaches the gap's near edge (candle3's side). That candle's CLOSE decides the
       trade: inside the gap or back through it -> enter at that close; closed all
       the way through -> cancel. Either way, the gap is used up (only the first
       touch matters, matching the video exactly).
  Stop: beyond candle 1's own extreme (this repo's existing FVG stop convention,
       Round 150, one tick beyond -- not just beyond the tiny gap itself, which
       would be trivially easy to wick out).
  Target: R:R fixed, 1:2 or 1:3 (both tested, the video's own final question).
  Secrets, each togglable:
    SIZE: gap width (near edge to candle1's boundary) >= 0.5 x ATR(14) on the
       candle series, causal (known at candle 1, the video's own exact threshold).
    COLOR: all three candles the same color as the gap's direction (Casper's rule).
    TREND: this repo's own operational proxy, since the video names no exact
       code -- an uptrend is close > SMA(50) and SMA(50) itself rising (5 candles
       back); downtrend the mirror. Bullish gaps only trade with an uptrend,
       bearish only with a downtrend.
    EQUILIBRIUM: this repo's own reconstruction of "the last move's 50% level",
       since the video doesn't give exact code either -- the move's low is the
       10-candle swing low ending at candle 1, its high is candle 2's own high
       (the impulsive leg); bullish only if the near edge sits below that
       midpoint (discount), bearish only if above (premium).
  Timeframe: 60-minute candles, continuous across days (not reset daily) -- the
    video's own conclusion was that higher timeframes work better and it would
    personally choose 1-hour (positive on every asset, more trades than 4H).
  Broker-legal constraint the video's own numbers do NOT have: every trade here
    is forced flat by 16:00 ET on the ENTRY candle's own trading day, same as
    every other idea in this ledger -- the video holds across sessions, which this
    repo's rule ("never use anything that holds past the close for anything that
    must be legal on Broker") does not allow. This WILL make results look worse
    than the video's own numbers by construction, not by execution error -- a cost
    the video's numbers don't pay and this ledger always does.
  Data: MNQ + MGC, 24-hour 1-minute bars (round147_batch_m.load()), pooled.
  Cost filter: trades whose fixed cost would exceed 0.10R at $300 risk are skipped
    (as Round 150).

4 filters x 2 R:R = 32 combinations, MNQ+MGC pooled. Ledger k=327 -> 359.

Two things reported: (1) each combo through idea_harness.test_idea's own bar
(positive net and gross; IS P(edge>0) >= 0.95; OOS P(edge>0) >= the bar at that
variant's k); (2) descriptively, for each of the 4 secrets, the fraction of its 16
paired combinations (same other 3 filters + R:R, that filter on vs off) where
turning it ON improved mean $/trade -- the same methodology the video used on its
own 96-combo grid, so this repo's answer can be compared directly against the
video's own claimed percentages (size 94%, color 54%, trend made things WORSE,
equilibrium 60%).
"""
import os, sys, json, subprocess, itertools, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
from round147_batch_m import load, RISK

FILTER_NAMES = ["size", "color", "trend", "equilibrium"]
MAX_COST_R = 0.10


def hourly_candles(bars):
    bars = bars.sort_index()
    r = bars.resample("60min", label="right", closed="right")
    k = pd.DataFrame({"open": r["open"].first(), "high": r["high"].max(), "low": r["low"].min(),
                      "close": r["close"].last(), "n": r["close"].count()})
    k = k[k["n"] >= 45].copy()
    k["tday"] = (k.index + pd.Timedelta(hours=6)).normalize()
    return k.reset_index(names="ts")


def compute_indicators(k):
    tr = pd.concat([k["high"] - k["low"], (k["high"] - k["close"].shift()).abs(),
                    (k["low"] - k["close"].shift()).abs()], axis=1).max(axis=1)
    k["atr"] = tr.rolling(14, min_periods=14).mean().shift(1)          # causal: known before this candle
    sma = k["close"].rolling(50, min_periods=50).mean()
    k["sma50"] = sma.shift(1)
    k["sma50_prior"] = sma.shift(6)
    k["swing_lo10"] = k["low"].rolling(10, min_periods=10).min().shift(1)
    k["swing_hi10"] = k["high"].rolling(10, min_periods=10).max().shift(1)
    return k


def build_gaps(k, tick, filters):
    out = []
    for j in range(2, len(k)):
        c1, c2, c3 = k.iloc[j - 2], k.iloc[j - 1], k.iloc[j]
        if c1["high"] + tick <= c3["low"]:
            d = 1
        elif c1["low"] - tick >= c3["high"]:
            d = -1
        else:
            continue
        near = c3["low"] if d == 1 else c3["high"]
        gap_far = c1["high"] if d == 1 else c1["low"]
        stop = c1["low"] - tick if d == 1 else c1["high"] + tick
        gap_size = abs(near - gap_far)

        if filters["size"]:
            atr = c1["atr"]
            if not (atr > 0) or gap_size < 0.5 * atr:
                continue
        if filters["color"]:
            c1g, c2g, c3g = c1["close"] > c1["open"], c2["close"] > c2["open"], c3["close"] > c3["open"]
            if (d == 1 and not (c1g and c2g and c3g)) or (d == -1 and (c1g or c2g or c3g)):
                continue
        if filters["trend"]:
            sma, smap = c1["sma50"], c1["sma50_prior"]
            if not (sma > 0 and smap > 0):
                continue
            if (d == 1 and not (c1["close"] > sma and sma > smap)) or \
               (d == -1 and not (c1["close"] < sma and sma < smap)):
                continue
        if filters["equilibrium"]:
            if d == 1:
                lo_ = c1["swing_lo10"]
                if not (lo_ == lo_) or not (near < (lo_ + c2["high"]) / 2):
                    continue
            else:
                hi_ = c1["swing_hi10"]
                if not (hi_ == hi_) or not (near > (hi_ + c2["low"]) / 2):
                    continue
        out.append(dict(formed=j, d=d, near=near, gap_far=gap_far, stop=stop))
    return out


def first_touch(k, gaps):
    lo, hi, cl = k["low"].values, k["high"].values, k["close"].values
    events = []
    for g in gaps:
        d, near = g["d"], g["near"]
        touch = None
        for i in range(g["formed"] + 1, len(k)):
            if (d == 1 and lo[i] <= near) or (d == -1 and hi[i] >= near):
                touch = i
                break
        if touch is None:
            continue
        c = cl[touch]
        trade_ok = (c >= g["gap_far"]) if d == 1 else (c <= g["gap_far"])
        events.append(dict(touch=touch, d=d, entry=c, stop=g["stop"], trade_ok=trade_ok))
    events.sort(key=lambda e: e["touch"])
    return events


def resolve_trades(k, events, sym, rr, risk=RISK, max_contracts=50):
    lo, hi, cl, ts, tday = k["low"].values, k["high"].values, k["close"].values, k["ts"].values, k["tday"].values
    pv, cpc = H.PV[sym], H.cost_per_contract(sym)
    trades, free_from = [], 0
    for e in events:
        if e["touch"] < free_from or not e["trade_ok"]:
            continue
        deadline = pd.Timestamp(pd.Timestamp(tday[e["touch"]]).date()) + pd.Timedelta(hours=16)
        if pd.Timestamp(ts[e["touch"]]) >= deadline:
            continue
        d, entry, stop = e["d"], e["entry"], e["stop"]
        dist = abs(entry - stop)
        if dist <= 0 or cpc / (dist * pv) > MAX_COST_R:
            continue
        target = entry + d * rr * dist
        i, px = e["touch"], None
        while px is None:
            i += 1
            if i >= len(k):
                i, px = len(k) - 1, cl[-1]
                break
            if (d == 1 and lo[i] <= stop) or (d == -1 and hi[i] >= stop):
                px = stop
            elif (d == 1 and hi[i] >= target) or (d == -1 and lo[i] <= target):
                px = target
            elif pd.Timestamp(ts[i]) >= deadline or i == len(k) - 1:
                px = cl[i]
        c_ = min(max(1, int(risk // (dist * pv))), max_contracts)
        trades.append((ts[e["touch"]], ts[i], d, c_, d * (px - entry) * pv * c_ - c_ * cpc, d * (px - entry) / dist))
        free_from = i + 1
    return pd.DataFrame(trades, columns=["entry_ts", "exit_ts", "direction", "contracts", "pnl", "r"])


def load_candles():
    data = load()
    out = {}
    for sym, (days, bars_all) in data.items():
        k = compute_indicators(hourly_candles(bars_all))
        out[sym] = (k, days)
    return out


def run_combo(candles, filters, rr):
    parts = []
    for sym, (k, days) in candles.items():
        gaps = build_gaps(k, H.TK[sym], filters)
        events = first_touch(k, gaps)
        tr = resolve_trades(k, events, sym, rr)
        tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
        tr["sym"] = sym
        parts.append(tr)
    return pd.concat(parts, ignore_index=True)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    candles = load_candles()
    all_days = sorted({d["tday"] for _, days in candles.values() for d in days})
    combos = list(itertools.product([False, True], repeat=4))

    if dry:
        for rr in (2, 3):
            for combo in combos:
                filters = dict(zip(FILTER_NAMES, combo))
                tr = run_combo(candles, filters, rr)
                tag = "".join(n[0].upper() if filters[n] else n[0] for n in FILTER_NAMES)
                print(f"rr={rr} {tag}: {len(tr)} trades")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    rows = []
    for rr in (2, 3):
        for combo in combos:
            filters = dict(zip(FILTER_NAMES, combo))
            tr = run_combo(candles, filters, rr)
            tag = ", ".join(n for n in FILTER_NAMES if filters[n]) or "none"
            k = H.ledger_count() + 1
            name = f"FVG real secrets [{tag}], 1:{rr}, 60-min, MNQ+MGC"
            r = H.test_idea(name, tr, all_days, "MNQ", k)
            r["filters"] = filters
            r["rr"] = rr
            rows.append(r)
            lines = H.ledger_rows([r], "Round 189 (pre-registered, the video's own 5 FVG secrets)", commit)
            with open(H.LEDGER, "a", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

    # descriptive: fraction of paired combos where turning each secret ON improved mean $/trade
    print("\n---- per-secret improvement rate (paired, same other settings) ----")
    by_key = {(tuple(sorted(r["filters"].items())), r["rr"]): r for r in rows}
    for name in FILTER_NAMES:
        improved, total = 0, 0
        for r in rows:
            if not r["filters"][name]:
                off = dict(r["filters"])
                on = dict(off, **{name: True})
                key_on = (tuple(sorted(on.items())), r["rr"])
                if key_on in by_key and not np.isnan(r["exp"]) and not np.isnan(by_key[key_on]["exp"]):
                    total += 1
                    improved += by_key[key_on]["exp"] > r["exp"]
        print(f"  {name:<12} improved {improved}/{total} paired combos ({100*improved/total:.0f}%)" if total else f"  {name}: n/a")

    with open(os.path.join(H.HERE, "round189_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
