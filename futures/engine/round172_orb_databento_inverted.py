"""
Round 172: the trader asked to invert the two cells from Round 171's Databento
replication that came up looking positive at a glance (NQ no-filter, IS
P=0.95 but OOS P=0.52 -- coin-flip; GC >=2.5x volume, OOS P=0.81) -- same
question this ledger has asked of every other lookalike positive result
(Rounds 131, 152, 158, 160). Inversion mechanics unchanged from every prior
one in this ledger: same entry, direction flipped, stop AND target
reflected through the entry price (new_level = 2*entry - old_level).

Step 0, honest before running: `inversion_screen.py`'s own documented
identity is inverse_net = net - 2*gross, which means an inversion only pays
when the ORIGINAL lost before costs by more than its costs -- neither of
these two lost before costs (NQ no-filter gross was positive; GC >=2.5x vol
gross was positive too, per Round 171's own printed numbers), so arithmetic
alone predicts both inversions make things WORSE, not better. Running for
real anyway (that arithmetic is only a guide for stop/target brackets, and
Round 158 already showed a naive pre-run estimate can be wrong) rather than
skipping on the strength of a mental calculation.

Same data, same 2R structure, same flat-by-16:00 exit as Round 171.

2 variants. Ledger k=274 -> 276; OOS bar 1 - 0.01/276.

Candidate (each variant): idea_harness.test_idea's own rule (positive net
and gross; IS P(edge>0) >= 0.95; OOS P(edge>0) >= the bar at that variant's k).
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idea_harness as H
from round171_databento_orb_replication import build_trades, load_days_databento


def invert(sig):
    sig = sig.copy()
    sig["sl"] = 2 * sig["entry"] - sig["sl"]
    sig["tp"] = 2 * sig["entry"] - sig["tp"]
    sig["direction"] = -sig["direction"]
    return sig


def build_inverted_trades(sym, vol_mult, rr):
    from round167_volume_confirmed_orb import orb_signals
    days = load_days_databento(sym)
    import pandas as pd
    bars = pd.concat([d[k] for d in days for k in ("on", "session")]).sort_index()
    sig = invert(orb_signals(days, sym, vol_mult, rr))
    tr = H.resolve_bracket(sig, bars, sym, flat_time=__import__("datetime").time(16, 0))
    tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
    return tr, days


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    grid = [("NQ", 0.0, "INVERTED NQ no-filter ORB, 2R, Databento"),
            ("GC", 2.5, "INVERTED GC >=2.5x vol ORB, 2R, Databento")]

    if dry:
        for sym, vm, label in grid:
            tr, _ = build_inverted_trades(sym, vm, 2.0)
            print(f"{label}: {len(tr)} trades")
        print("\n--dry-run: counts only (trades ARE resolved for real, just not logged). Hand-check before the real run.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    rows = []
    for sym, vm, label in grid:
        k = H.ledger_count() + 1
        tr, days = build_inverted_trades(sym, vm, 2.0)
        all_days = [d["tday"] for d in days]
        r = H.test_idea(label, tr, all_days, sym, k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 172 (pre-registered, inverting Round 171's two least-bad Databento cells)",
                               commit, date="2026-09-27")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round172_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
