"""
Round 169: two follow-ups to Round 167's genuine (if sub-bar) finding, after
Round 168 showed the volume-confirmation effect does NOT generalize to
Round 148's other breakout levels (round numbers, prior-day H/L, overnight
H/L all got FLAT or WORSE with tighter volume filtering, one of them -- N3
-- confidently so, OOS P tightening toward 0 as the filter tightened). That
null result narrows, rather than kills, Round 167's finding: it says the
effect is plausibly tied to the opening range specifically (real
participation right after the day's key price-discovery event), not a
generic "volume confirms any breakout" law -- worth checking the ORB result
harder before either refining it further or retiring it.

Two checks, both pre-registered before running:

(1) Does the dose-response continue past 2.5x, or was that a local peak in
    a small sample? Round 167's 2R-target column: no filter $-1.3, 1.5x
    +$8.4, 2.5x +$14.9 (OOS P 0.22 / 0.43 / 0.93) -- monotonically improving
    across 3 points is suggestive but could still be a small-sample fluke.
    Extends the SAME grid (2R target, MNQ+MGC) to 3.5x and 5.0x.

(2) Is the effect present in BOTH instruments, or is one carrying it? Round
    167 always pooled MNQ+MGC. Splits the best cell found so far (2R
    target, >=2.5x volume) into MNQ-only and MGC-only.

Step 0, honest before running: extending a grid after seeing where it
peaked raises real selection-bias risk (exactly Round 166's own
step-0 caution about "choosing survivors" applied to a single lead this
time) -- disclosed, and held to the SAME OOS bar as anything else at this
ledger's current k, not given a lower one for being a "refinement".

Unchanged from Round 167: opening range = first 15 min RTH (09:30-09:45
ET), first breakout confirmed by volume >= the multiplier x the range's own
average bar volume, stop at the opposite side of the range, target = 2x
that stop, $300 risk, real commission + 2-tick slippage, flat by 16:00 ET.

4 variants (2 new thresholds + 2 single-symbol splits). Ledger k=246 -> 250;
OOS bar 1 - 0.01/250 at the last variant.

Candidate (each variant): idea_harness.test_idea's own rule (positive net
and gross; IS P(edge>0) >= 0.95; OOS P(edge>0) >= the bar at that variant's k).
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import idea_harness as H
from round167_volume_confirmed_orb import orb_signals, cached_days, cached_bars

RR = 2.0


def build_trades(vol_mult, symbols):
    parts = []
    for sym in symbols:
        days = cached_days(sym)
        bars = cached_bars(sym)
        sig = orb_signals(days, sym, vol_mult, RR)
        tr = H.resolve_bracket(sig, bars, sym, flat_time=dt.time(16, 0))
        tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
        parts.append(tr)
    return pd.concat(parts, ignore_index=True)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    grid = [(3.5, ("MNQ", "MGC"), "VCORB 2R, >=3.5x OR-avg vol, MNQ+MGC"),
            (5.0, ("MNQ", "MGC"), "VCORB 2R, >=5.0x OR-avg vol, MNQ+MGC"),
            (2.5, ("MNQ",), "VCORB 2R, >=2.5x OR-avg vol, MNQ only"),
            (2.5, ("MGC",), "VCORB 2R, >=2.5x OR-avg vol, MGC only")]

    if dry:
        for vm, syms, label in grid:
            tr = build_trades(vm, syms)
            print(f"{label}: {len(tr)} trades")
        print("\n--dry-run: counts only (trades ARE resolved for real, just not logged). Hand-check before the real run.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    all_days_mnq_mgc = sorted(set(d["tday"] for d in cached_days("MNQ")) | set(d["tday"] for d in cached_days("MGC")))

    rows = []
    for vm, syms, label in grid:
        k = H.ledger_count() + 1
        tr = build_trades(vm, syms)
        all_days = sorted(set(d["tday"] for s in syms for d in cached_days(s)))
        r = H.test_idea(label, tr, all_days, "MNQ", k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 169 (pre-registered, extending + decomposing Round 167's ORB volume finding)",
                               commit, date="2026-09-27")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round169_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
