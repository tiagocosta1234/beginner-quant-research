"""
Round 159: the trader asked to try all ICT strategies. Checked what's already in
the ledger first (k=200) so this doesn't re-test what's done: Fair Value
Gaps (Round 150, 4 variants), Optimal Trade Entry / sweep-reclaim (Round
76), Judas Swing (Round 125), protected-level stops (Round 125b), Power of
Three (Round 129), Standard Deviation projections (Round 127, 132), HRL vs
LRL (Round 128), and fading the prior day's high/low on first touch (Round
147's M2 -- the same core mechanic as "Turtle Soup", so not re-tested here
as its own variant; it already found no edge). That leaves two genuinely
distinct, well-known ICT setups untested:

OB  Order Blocks: the last opposite-colour candle before a break of the
    prior 60-minute swing high/low (the same K_MIN this campaign already
    uses for OTE, round76) marks the order block; its [low, high] range is
    the zone. Enter on the FIRST retest of that zone, in the ORIGINAL
    breakout's direction (continuation) -- the standard "OB retest" model.
    Stop beyond the OB's far edge; target at 1R, 2R and 3R (three variants).
SB  Silver Bullet: round76's own OTE/FVG sweep-reclaim detector (unchanged,
    already validated code, no new bug surface), restricted to fire ONLY
    inside the two windows ICT actually teaches for this setup -- 10:00-
    11:00 and 14:00-15:00 ET. Genuinely different from Round 150's
    "killzones" (02:00-05:00 London, 09:30-11:30 NY AM) -- no time overlap
    with the afternoon window, and Round 150 never isolated a killzone-only
    effect (its P2 variant blended killzone with three other changes at
    once). Stop/target rebuilt fresh here (ATR-based) rather than reusing
    round76's own frozen-at-detection-time stop column, which Round 104
    already showed is unsafe to reuse for anything but its own original
    stop value.

Step 0, honest before running: FVG, OTE and Judas Swing already found no
edge on this same data with the same real-cost, flat-at-close discipline.
Order Blocks and Silver Bullet share the same underlying primitives
(swing/structure detection, FVG confluence) as those failed setups -- no
reason to expect a structurally different outcome, tested for completeness
of "all ICT strategies" as asked, not because the odds look better.

Data: 24-hour 1-minute MNQ + MGC (idea_harness.load_days/bars_from_days),
2022-12 .. 2026-09. Exits: idea_harness.resolve_bracket, $300 risk, real
costs, flat at the session close. Split 2025-07-01 (idea_harness convention).

5 variants (OB at 1R/2R/3R, SB at 1:1 and 1:2). Ledger k=200 -> 205; OOS bar
at k=205 = 1 - 0.01/205.

Candidate (idea_harness.test_idea's own rule): positive before AND after
costs; IS P(edge>0) >= 0.95; OOS P(edge>0) >= the k-adjusted bar.
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
from round19_random_entry import causal_atr15_lookup
from round11_fvg_bias import resample_causal, detect_fvgs
from round76_ote_pdarray_formalized import detect_ote_signals

K_SWING = 60
LOOKBACK_OB = 10
MAX_WAIT_BARS = 240
SB_WINDOWS = [(dt.time(10, 0), dt.time(11, 0)), (dt.time(14, 0), dt.time(15, 0))]


def detect_order_blocks(bars):
    op, hi, lo, cl = bars["open"].values, bars["high"].values, bars["low"].values, bars["close"].values
    ts = bars.index.values
    n = len(bars)
    signals = []
    i = K_SWING
    while i < n:
        prior_hi, prior_lo = hi[i - K_SWING:i].max(), lo[i - K_SWING:i].min()
        direction, ob_lo, ob_hi = 0, None, None
        if cl[i] > prior_hi:
            for j in range(i - 1, max(i - LOOKBACK_OB - 1, -1), -1):
                if cl[j] < op[j]:
                    direction, ob_lo, ob_hi = 1, lo[j], hi[j]
                    break
        elif cl[i] < prior_lo:
            for j in range(i - 1, max(i - LOOKBACK_OB - 1, -1), -1):
                if cl[j] > op[j]:
                    direction, ob_lo, ob_hi = -1, lo[j], hi[j]
                    break
        if direction == 0:
            i += 1
            continue
        found = False
        for k in range(i + 1, min(i + MAX_WAIT_BARS, n)):
            touched = lo[k] <= ob_hi and hi[k] >= ob_lo
            if touched:
                entry = cl[k]
                sl = ob_lo - 0.1 * (ob_hi - ob_lo) if direction == 1 else ob_hi + 0.1 * (ob_hi - ob_lo)
                signals.append((ts[k], direction, entry, sl))
                found = True
                break
        i = (k if found else i + MAX_WAIT_BARS) + 1
    return pd.DataFrame(signals, columns=["ts", "direction", "entry", "sl"])


def silver_bullet_signals(bars, atr15):
    htf15 = resample_causal(bars, "15min")
    fvg_zones = detect_fvgs(htf15)
    raw = detect_ote_signals(bars, fvg_zones)  # ts, direction, entry, stop (stop discarded, see docstring)
    if len(raw) == 0:
        return raw
    t = raw["ts"].dt.time
    in_window = np.zeros(len(raw), bool)
    for a, z in SB_WINDOWS:
        in_window |= (t >= a) & (t < z)
    raw = raw[in_window].reset_index(drop=True)
    atr_ts, atr_vals = atr15.index.values, atr15.values
    sl = []
    for r in raw.itertuples(index=False):
        pos = np.searchsorted(atr_ts, np.datetime64(r.ts), side="right") - 1
        a = atr_vals[pos] if pos >= 0 and not np.isnan(atr_vals[pos]) else np.nan
        sl.append(r.entry - a if r.direction == 1 else r.entry + a)
    raw = raw.assign(sl=sl).dropna(subset=["sl"])
    return raw[["ts", "direction", "entry", "sl"]]


def build_trades(setup, rr, dry_run=False):
    parts = []
    for sym in ("MNQ", "MGC"):
        days = H.load_days(sym)
        bars = H.bars_from_days(days, "all")
        if setup == "OB":
            sig = detect_order_blocks(bars)
        else:
            atr15 = causal_atr15_lookup(bars)
            sig = silver_bullet_signals(bars, atr15)
        if dry_run:
            parts.append((sym, len(sig)))
            continue
        sig = sig.copy()
        sig["tp"] = sig["entry"] + rr * (sig["entry"] - sig["sl"])
        tr = H.resolve_bracket(sig, bars, sym, risk=H.RISK)
        tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
        parts.append(tr)
    if dry_run:
        return parts
    return pd.concat(parts, ignore_index=True)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    if dry:
        for setup in ("OB", "SB"):
            counts = build_trades(setup, rr=1.0, dry_run=True)
            print(f"{setup}: " + ", ".join(f"{sym} {n} signals" for sym, n in counts))
        print("\n--dry-run: counts only, no P&L. Hand-check a few signals before running for real.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    rows = []
    all_days_by_sym = {sym: [d["tday"] for d in H.load_days(sym)] for sym in ("MNQ", "MGC")}
    all_days = sorted(set(all_days_by_sym["MNQ"]) | set(all_days_by_sym["MGC"]))
    for setup, rr, label in [
        ("OB", 1.0, "ICT Order Block retest continuation, 1R, MNQ + MGC"),
        ("OB", 2.0, "ICT Order Block retest continuation, 2R, MNQ + MGC"),
        ("OB", 3.0, "ICT Order Block retest continuation, 3R, MNQ + MGC"),
        ("SB", 1.0, "ICT Silver Bullet (10-11/14-15 ET sweep+FVG), 1:1, MNQ + MGC"),
        ("SB", 2.0, "ICT Silver Bullet (10-11/14-15 ET sweep+FVG), 1:2, MNQ + MGC"),
    ]:
        k = H.ledger_count() + 1
        tr = build_trades(setup, rr)
        r = H.test_idea(label, tr, all_days, "MNQ", k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 159 (pre-registered, ICT: all remaining strategies)", commit,
                               date="2026-09-27")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round159_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\nledger now k={H.ledger_count()}")
