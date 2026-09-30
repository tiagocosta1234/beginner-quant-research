"""
Round 220 (pre-registered, new idea class, 2026-09-30): "lets keep this
strategy safe for now and lets try to look for a new branch of a strategy"
-- the trader and disciplined_bracket are left untouched; this is a genuinely
new signal, not a risk-management tweak on an existing one.

Round 170 already tested Chaikin's Money Flow Multiplier proxy (MFM =
((close-low)-(high-close))/(high-low), summed as Money Flow Volume from
09:30 to a checkpoint) as a CONTINUATION signal: sign of the sum -> trade
that direction, hold to close. Both checkpoints (10:00, 10:30) failed (OOS
P(edge>0) = 0.135-0.389, ledger rows 250-253).

This tests a different hypothesis on the SAME real data construction:
DIVERGENCE, not continuation. Classic technical-analysis divergence theory
(applied here to daily charts for 45+ years, e.g. OBV/A-D divergence) says
a price move that participation data does NOT confirm is a reversal
warning, not a continuation signal -- the opposite rule from Round 170's.
Concretely, at each checkpoint, compare the sign of money flow against the
sign of plain price momentum (checkpoint close vs. 09:30 open):

  - DIVERGENCE days (signs disagree, both nonzero): trade WITH money flow,
    AGAINST price -- betting the unconfirmed price move reverts toward
    what real participation implied.
  - AGREEMENT days (signs agree): trade WITH price (== money flow) --
    the continuation case, but restricted to only the subset of days
    where both metrics agree, as a control to isolate whether the
    divergence subset in particular carries any real signal (rather than
    conviction/agreement in general, which is closer to Round 170's own
    always-trade-money-flow rule and already known to fail).

Same real entry/exit mechanics as Round 170 throughout, so results are
directly comparable and no new mechanic is smuggled in: entry at the
checkpoint's close, stop = that morning's own range (opposite side of
entry, no tuned multiplier), no target, flat by 16:00 ET, one trade/day.
MNQ + MGC, $300 risk, real commission + 2-tick slippage.

Step 0, honest before running: this only changes which days are eligible
and which side is taken, not the underlying data construction -- so it
inherits Round 170's own caveat (a 45-year-old daily-chart retail
indicator, repurposed here as an intraday 1-minute-bar timing signal, is a
real stretch of its original design). Tested because "divergence implies
reversal" is a genuinely different, named, real hypothesis from "the sign
of participation implies continuation" (Round 170), not because prior odds
are good -- 381 prior ledger rows, most idea classes already covered, per
the "new branch of a strategy" gap analysis done before writing this.

4 variants (2 checkpoints x {divergence-reversal, agreement-continuation
control}). Ledger k=382 -> 385; OOS bar 1 - 0.01/385 at the last variant.

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


def signals(days, symbol, checkpoint, mode):
    tick = H.TK[symbol]
    out = []
    for d in days:
        s = d["session"]
        t = s.index.time
        morning = s[(t >= RTH_OPEN) & (t <= checkpoint)]
        if len(morning) < 5:
            continue
        hi, lo = morning["high"].max(), morning["low"].min()
        rng = hi - lo
        if rng <= 0:
            continue
        rng_bar = (morning["high"] - morning["low"]).replace(0, np.nan)
        mfm = ((morning["close"] - morning["low"]) - (morning["high"] - morning["close"])) / rng_bar
        money_flow = (mfm.fillna(0) * morning["vol"]).sum()
        price_mom = morning["close"].iloc[-1] - morning["open"].iloc[0]
        if money_flow == 0 or price_mom == 0:
            continue
        agree = (money_flow > 0) == (price_mom > 0)
        if mode == "divergence" and agree:
            continue
        if mode == "agreement" and not agree:
            continue
        dd = 1 if (money_flow > 0 if mode == "divergence" else price_mom > 0) else -1
        entry = morning["close"].iloc[-1]
        sl = (lo - tick) if dd == 1 else (hi + tick)
        out.append((morning.index[-1], dd, entry, sl, np.nan))
    return pd.DataFrame(out, columns=["ts", "direction", "entry", "sl", "tp"])


def build_trades(checkpoint, mode):
    parts = []
    for sym in ("MNQ", "MGC"):
        days, bars = cached_days(sym), cached_bars(sym)
        sig = signals(days, sym, checkpoint, mode)
        tr = H.resolve_bracket(sig, bars, sym, flat_time=FLAT_TIME)
        tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
        parts.append(tr)
    return pd.concat(parts, ignore_index=True)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    grid = []
    for cp, cp_label in [(dt.time(10, 0), "10:00"), (dt.time(10, 30), "10:30")]:
        for mode, mode_label in [("divergence", "divergence-reversal"), ("agreement", "agreement-continuation control")]:
            grid.append((cp, mode, f"Checkpoint {cp_label} ET, money-flow/price {mode_label}, hold to close, MNQ+MGC"))

    if dry:
        for cp, mode, label in grid:
            tr = build_trades(cp, mode)
            print(f"{label}: {len(tr)} trades")
        print("\n--dry-run: counts only (trades ARE resolved for real, just not logged). Hand-check before the real run.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    all_days_mnq_mgc = sorted(set(d["tday"] for d in cached_days("MNQ")) | set(d["tday"] for d in cached_days("MGC")))

    rows = []
    for cp, mode, label in grid:
        k = H.ledger_count() + 1
        tr = build_trades(cp, mode)
        r = H.test_idea(label, tr, all_days_mnq_mgc, "MNQ", k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 220 (pre-registered, new idea class: money-flow/price divergence reversal)",
                               commit, date="2026-09-30")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round220_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
