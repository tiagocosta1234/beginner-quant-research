"""
Round 160: invert every ICT strategy in the ledger that hasn't already been
inverted. the trader: "try to invert all of them." Checked first which ones
already have a real (not just arithmetic) inversion on record: Round 131
already inverted Judas Swing (Round 125/125b), the STDV fade (Round 127)
and HRL/LRL (Round 128) for real -- 0 of those 16 inversions passed either.
Re-inverting them again would just reproduce the ORIGINAL (already-tested)
direction, so this covers the four ICT families Round 131 didn't reach:
Fair Value Gaps (Round 150, 4 core variants), Order Blocks and Silver
Bullet (Round 159, 5 variants), and Power of Three (Round 129, 4 variants)
-- 13 variants in total, not 14: Round 153's FVG exit-grid retest is a
different experimental axis (exit tuning, not the core signal) and isn't
re-inverted here to avoid compounding two axes in one result.

Selection warning, same as every inversion in this ledger (Round 131, 152,
158): these are chosen because the originals lost, which is fitting to
results already seen -- a real pass would need new (forward) data to count
as evidence, not just this same history read the other way.

Screened first with `inversion_screen.py` before deciding to actually
re-run everything (not just trust the arithmetic, which the tool's own
docstring says is "only a guide" for stop/target brackets -- all four of
these families are brackets): only PO3's row 63 (10:00-14:00, near-ATH
longs only) showed a meaningfully positive arithmetic inverse (+$29.70);
everything else screened negative. Re-run for real anyway, all 13, per
the trader's own "all of them" -- the arithmetic guide is not exact here and
Round 158 already showed a naive pre-run estimate can be wrong.

Inversion mechanics (exact, not the arithmetic approximation): same entry,
same risk distance, direction flipped, stop and target reflected through
the entry price (new_level = 2*entry - old_level) -- equivalent to swapping
which of the original stop/target level plays which role. Verified this
is the correct closed form (not just flipping the direction sign against
the original stop/target unchanged, which would double-count the risk).

Ledger k=205 -> 218 (13 new rows). Candidate bar: idea_harness.test_idea's
own rule (positive before/after costs, IS P>=0.95, OOS P>=1-0.01/k).
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
from round150_batch_p import fvg_orders, resolve_limit, candles
from round147_batch_m import full as day_bars
from round159_ict_order_blocks_silver_bullet import detect_order_blocks, silver_bullet_signals
from round129_4h_po3 import po3_signals, ath_flags
from round19_random_entry import causal_atr15_lookup

_DAYS_CACHE = {}
_BARS_CACHE = {}


def cached_days(sym):
    if sym not in _DAYS_CACHE:
        _DAYS_CACHE[sym] = H.load_days(sym)
    return _DAYS_CACHE[sym]


def cached_bars(sym):
    if sym not in _BARS_CACHE:
        _BARS_CACHE[sym] = H.bars_from_days(cached_days(sym), "all")
    return _BARS_CACHE[sym]


def invert_fvg_orders(orders):
    return [(formed, expiry, -d, e, tgt, s) for (formed, expiry, d, e, s, tgt) in orders]


def invert_ob_sb_signals(sig):
    sig = sig.copy()
    sig["sl"] = 2 * sig["entry"] - sig["sl"]
    sig["direction"] = -sig["direction"]
    return sig


def invert_po3_signals(sig):
    """po3_signals returns a DataFrame (ts, direction, entry, sl, tp=NaN) -- tp
    stays NaN (still hold-to-candle-end, just now betting the other way)."""
    sig = sig.copy()
    sig["sl"] = 2 * sig["entry"] - sig["sl"]
    sig["direction"] = -sig["direction"]
    return sig


def fvg_trades(tf, secrets):
    parts = []
    for sym in ("MNQ", "MGC"):
        days = cached_days(sym)
        rows = []
        for d in days:
            b = day_bars(d)
            orders = fvg_orders(b, sym, tf, secrets)
            inv = invert_fvg_orders(orders)
            rows += resolve_limit(b, inv, sym, risk=H.RISK)
        tr = pd.DataFrame(rows, columns=["entry_ts", "exit_ts", "direction", "contracts", "pnl", "r"])
        tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
        parts.append(tr)
    return pd.concat(parts, ignore_index=True)


def ob_sb_trades(setup, rr):
    parts = []
    for sym in ("MNQ", "MGC"):
        days = cached_days(sym)
        bars = cached_bars(sym)
        if setup == "OB":
            sig = detect_order_blocks(bars)
        else:
            atr15 = causal_atr15_lookup(bars)
            sig = silver_bullet_signals(bars, atr15)
        sig = invert_ob_sb_signals(sig)
        sig = sig.copy()
        sig["tp"] = sig["entry"] + rr * (sig["entry"] - sig["sl"])
        tr = H.resolve_bracket(sig, bars, sym, risk=H.RISK)
        tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
        parts.append(tr)
    return pd.concat(parts, ignore_index=True)


def po3_trades(start, longs_only_near_ath_flag):
    days = cached_days("MNQ")
    flags = ath_flags(days) if longs_only_near_ath_flag else None
    sig = po3_signals(days, start, flags)
    sig = invert_po3_signals(sig)
    bars = cached_bars("MNQ")
    end = dt.time((start.hour + 4) % 24, start.minute)  # candle's own end, matching Round 129's exit exactly
    tr = H.resolve_bracket(sig, bars, "MNQ", flat_time=end)
    tr["cost"] = tr["contracts"] * H.cost_per_contract("MNQ")
    return tr


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    if dry:
        for tf, secrets, label in [(5, False, "FVG P1 5m"), (5, True, "FVG P2 5m"),
                                     (15, False, "FVG P1 15m"), (15, True, "FVG P2 15m")]:
            tr = fvg_trades(tf, secrets)
            print(f"{label}: {len(tr)} inverted trades")
        for setup, rr, label in [("OB", 1.0, "OB 1R"), ("OB", 2.0, "OB 2R"), ("OB", 3.0, "OB 3R"),
                                   ("SB", 1.0, "SB 1:1"), ("SB", 2.0, "SB 1:2")]:
            tr = ob_sb_trades(setup, rr)
            print(f"{label}: {len(tr)} inverted trades")
        for start, ath, label in [(dt.time(6, 0), False, "PO3 06-10 both"), (dt.time(6, 0), True, "PO3 06-10 ATH"),
                                    (dt.time(10, 0), False, "PO3 10-14 both"), (dt.time(10, 0), True, "PO3 10-14 ATH")]:
            tr = po3_trades(start, ath)
            print(f"{label}: {len(tr)} inverted trades")
        print("\n--dry-run: counts only (no P&L printed above, but trades ARE resolved -- computed for real, "
              "just not logged). Hand-check before the real run.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    all_days_mnq_mgc = sorted(set(d["tday"] for d in cached_days("MNQ")) | set(d["tday"] for d in cached_days("MGC")))
    all_days_mnq = sorted(set(d["tday"] for d in cached_days("MNQ")))

    plan = [
        ("fvg", (5, False), "INVERTED P1 plain FVG retest, 5-min, MNQ + MGC", all_days_mnq_mgc),
        ("fvg", (5, True), "INVERTED P2 FVG (displacement/VWAP/killzone/50%), 5-min, MNQ + MGC", all_days_mnq_mgc),
        ("fvg", (15, False), "INVERTED P1 plain FVG retest, 15-min, MNQ + MGC", all_days_mnq_mgc),
        ("fvg", (15, True), "INVERTED P2 FVG (displacement/VWAP/killzone/50%), 15-min, MNQ + MGC", all_days_mnq_mgc),
        ("ob", ("OB", 1.0), "INVERTED ICT Order Block retest, 1R, MNQ + MGC", all_days_mnq_mgc),
        ("ob", ("OB", 2.0), "INVERTED ICT Order Block retest, 2R, MNQ + MGC", all_days_mnq_mgc),
        ("ob", ("OB", 3.0), "INVERTED ICT Order Block retest, 3R, MNQ + MGC", all_days_mnq_mgc),
        ("ob", ("SB", 1.0), "INVERTED ICT Silver Bullet, 1:1, MNQ + MGC", all_days_mnq_mgc),
        ("ob", ("SB", 2.0), "INVERTED ICT Silver Bullet, 1:2, MNQ + MGC", all_days_mnq_mgc),
        ("po3", (dt.time(6, 0), False), "INVERTED MNQ 4H Po3 06:00-10:00, both directions", all_days_mnq),
        ("po3", (dt.time(6, 0), True), "INVERTED MNQ 4H Po3 06:00-10:00, near-ATH longs only", all_days_mnq),
        ("po3", (dt.time(10, 0), False), "INVERTED MNQ 4H Po3 10:00-14:00, both directions", all_days_mnq),
        ("po3", (dt.time(10, 0), True), "INVERTED MNQ 4H Po3 10:00-14:00, near-ATH longs only", all_days_mnq),
    ]

    rows = []
    for kind, args, label, all_days in plan:
        k = H.ledger_count() + 1
        if kind == "fvg":
            tr = fvg_trades(*args)
        elif kind == "ob":
            tr = ob_sb_trades(*args)
        else:
            tr = po3_trades(*args)
        r = H.test_idea(label, tr, all_days, "MNQ", k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 160 (pre-registered, inverting all remaining un-inverted ICT strategies)",
                               commit, date="2026-09-27")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round160_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\nledger now k={H.ledger_count()}")
