"""
Round 170: a third from-scratch construction. Rounds 166 (portfolio
combination) and 167-169 (volume-as-a-confirmation-filter) both explored
what was available; this uses volume as the SIGNAL itself for the first
time in this ledger, not a filter on a price-pattern entry.

No tick or order-book data exists in this repo (`CURRENT_STATE.md` says so
directly), so true buy/sell aggressor volume can't be computed. This uses
the standard OHLCV proxy for it (Chaikin's Money Flow Multiplier, 1980s,
still the basis of on-balance/accumulation-distribution indicators): for
each 1-minute bar, MFM = ((close-low)-(high-close))/(high-low), in [-1,+1]
-- a close near the bar's high implies mostly buying pressure inside that
bar, near the low implies selling pressure. Money Flow Volume = MFM x vol.
Summed from the session open, this is a rough proxy for whether real
participation this morning was net accumulating or distributing, distinct
from the raw volume-only threshold Rounds 167-169 tested (this uses volume
CONDITIONED on where the bar closed, not volume alone) and distinct from
every price-only ICT/level/momentum test in this ledger (price momentum can
be positive on THIN, unconvincing volume; this is built to tell the two
apart).

Rule: at a checkpoint time (10:00 or 10:30 ET, one of two variants), sum
Money Flow Volume from 09:30 to the checkpoint. Sign of that sum -> the
day's direction, entered at the checkpoint's close, stop = the checkpoint's
own morning range (high-low from 09:30 to checkpoint, placed on the
opposite side of entry -- no extra tuned multiplier), no target, flat by
16:00 ET. Compared directly (ablation, matching Rounds 167-168's design)
against the SAME rule using plain price momentum (sign of the checkpoint's
close vs the 09:30 open) instead of money flow -- isolating whether volume-
weighting the direction adds anything over price alone.

Step 0, honest before running: this is a 45-year-old retail indicator
family (Chaikin, On-Balance Volume, Accumulation/Distribution) built for
daily charts, being repurposed here as an intraday timing signal on 1-minute
bars -- a real stretch of its original design, and OHLCV-derived volume
proxies are exactly the kind of thing the `/watch`ed video (2026-09-27,
Limbo/The Exchange Society) argued get arbitraged away at the tick level
long before a 1-minute-bar retail version could catch it. Tested because it
is a genuinely different signal TYPE (participation-weighted, not price-
only or volume-only), not because prior odds are good.

MNQ + MGC (full multi-year 1-minute-equivalent history), $300 risk, real
commission + 2-tick slippage, flat by 16:00 ET, first setup per day (one
trade only, at the fixed checkpoint).

4 variants (2 checkpoints x {money flow, price-momentum control}). Ledger
k=250 -> 254; OOS bar 1 - 0.01/254 at the last variant.

Candidate (each variant): idea_harness.test_idea's own rule (positive net
and gross; IS P(edge>0) >= 0.95; OOS P(edge>0) >= the bar at that variant's k).
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


def signals(days, symbol, checkpoint, use_money_flow):
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
        if use_money_flow:
            rng_bar = (morning["high"] - morning["low"]).replace(0, np.nan)
            mfm = ((morning["close"] - morning["low"]) - (morning["high"] - morning["close"])) / rng_bar
            score = (mfm.fillna(0) * morning["vol"]).sum()
        else:
            score = morning["close"].iloc[-1] - morning["open"].iloc[0]
        if score == 0:
            continue
        dd = 1 if score > 0 else -1
        entry = morning["close"].iloc[-1]
        sl = (lo - tick) if dd == 1 else (hi + tick)
        out.append((morning.index[-1], dd, entry, sl, np.nan))
    return pd.DataFrame(out, columns=["ts", "direction", "entry", "sl", "tp"])


def build_trades(checkpoint, use_money_flow):
    parts = []
    for sym in ("MNQ", "MGC"):
        days, bars = cached_days(sym), cached_bars(sym)
        sig = signals(days, sym, checkpoint, use_money_flow)
        tr = H.resolve_bracket(sig, bars, sym, flat_time=FLAT_TIME)
        tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
        parts.append(tr)
    return pd.concat(parts, ignore_index=True)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    grid = []
    for cp, cp_label in [(dt.time(10, 0), "10:00"), (dt.time(10, 30), "10:30")]:
        for mf, mf_label in [(True, "money-flow"), (False, "price-momentum control")]:
            grid.append((cp, mf, f"Checkpoint {cp_label} ET, {mf_label}, hold to close, MNQ+MGC"))

    if dry:
        for cp, mf, label in grid:
            tr = build_trades(cp, mf)
            print(f"{label}: {len(tr)} trades")
        print("\n--dry-run: counts only (trades ARE resolved for real, just not logged). Hand-check before the real run.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    all_days_mnq_mgc = sorted(set(d["tday"] for d in cached_days("MNQ")) | set(d["tday"] for d in cached_days("MGC")))

    rows = []
    for cp, mf, label in grid:
        k = H.ledger_count() + 1
        tr = build_trades(cp, mf)
        r = H.test_idea(label, tr, all_days_mnq_mgc, "MNQ", k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 170 (pre-registered, original strategy: cumulative money-flow proxy)",
                               commit, date="2026-09-27")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round170_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
