"""
Round 173: the trader asked what could raise Sharpe (smooth the equity curve),
and agreed to test the most direct lever -- the payoff SHAPE, not just
finding more signals. Every real-ish signal in this ledger (Connors, IBS,
the ORB) uses a low-win-rate/big-target structure, which is inherently
high-variance for its expectancy. This tests whether tightening the ORB's
target (round167/171's rr parameter, currently 2.0) toward a higher-win-
rate, lower-variance shape raises Sharpe, even at the cost of a smaller
average dollar edge -- on the two Round 171 cells that had a real, if
unconfirmed, positive point estimate: NQ no-filter and GC >=2.5x volume.

Step 0, honest before running, directly citing this ledger's own prior
lesson: Round 153 already found that exits tuned IN-SAMPLE decay OUT-OF-
SAMPLE (a previous-day breakout's best exit went from +$63.5 IS to +$5.0
OOS). To avoid repeating that mistake under a different name, this round
uses a genuine train/test split, not a look-at-everything-and-pick-the-best
grid search: for each symbol, the Sharpe-maximizing RR is chosen using ONLY
data before idea_harness's own OOS_START (2025-07-01), then that single,
already-chosen RR is applied, unchanged, to the OOS period and judged there
-- the same discipline this ledger has always required, just with the
selection criterion swapped from "best net $" to "best daily Sharpe".

Grid (pre-registered, not touched after seeing any result): RR in
{0.5, 0.75, 1.0, 1.5, 2.0 (Round 171's original), 3.0}. For each symbol,
compute daily Sharpe (full calendar, IS period only) at each RR, pick
argmax, then report that one RR's OOS performance for real. Everything
else (opening range, volume filter, stop placement, $300 risk, real
commission + 2-tick slippage, flat by 16:00 ET) unchanged from Round 171.

2 symbols x 1 selected variant each reported as a candidate test = 2 ledger
rows (the grid-search itself is diagnostic, not a separate row per RR --
reporting 6 additional untested RR values as if they were 6 new ideas would
misrepresent a single train/test decision as 12 independent ones). Ledger
k=276 -> 278; OOS bar 1 - 0.01/278.

Candidate: idea_harness.test_idea's own rule, applied to the OOS-evaluated,
IS-selected RR only (positive net and gross; IS P(edge>0) >= 0.95; OOS
P(edge>0) >= the bar at that variant's k).
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
from round167_volume_confirmed_orb import orb_signals
from round171_databento_orb_replication import load_days_databento

RR_GRID = [0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
OOS_START = pd.Timestamp("2025-07-01")


def trades_for(sym, vol_mult, rr):
    days = load_days_databento(sym)
    bars = pd.concat([d[k] for d in days for k in ("on", "session")]).sort_index()
    sig = orb_signals(days, sym, vol_mult, rr)
    tr = H.resolve_bracket(sig, bars, sym, flat_time=dt.time(16, 0))
    tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
    return tr, days


def is_sharpe(tr, days, cutoff=OOS_START):
    all_days = pd.DatetimeIndex(sorted(d["tday"] for d in days))
    is_days = all_days[all_days < cutoff]
    tr_is = tr[pd.to_datetime(tr["entry_ts"]) < cutoff]
    daily = tr_is.groupby(pd.to_datetime(tr_is["entry_ts"]).dt.normalize())["pnl"].sum().reindex(is_days, fill_value=0.0)
    return float(daily.mean() / daily.std()) if daily.std() > 0 else float("nan"), int(len(tr_is))


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    cases = [("NQ", 0.0, "NQ no-filter"), ("GC", 2.5, "GC >=2.5x vol")]

    print("Grid search, IS-only (before 2025-07-01), selecting argmax Sharpe per symbol:\n")
    chosen = {}
    for sym, vm, label in cases:
        print(f"{label}:")
        best_rr, best_sh = None, -np.inf
        for rr in RR_GRID:
            tr, days = trades_for(sym, vm, rr)
            sh, n_is = is_sharpe(tr, days)
            flag = ""
            if sh > best_sh:
                best_sh, best_rr = sh, rr
                flag = "  <- best so far"
            print(f"  RR={rr:<4} n_IS={n_is:<5} IS daily Sharpe={sh:+.4f}{flag}")
        chosen[sym] = best_rr
        print(f"  chosen RR for {label}: {best_rr} (IS Sharpe {best_sh:+.4f}, vs Round 171's RR=2.0)\n")

    if dry:
        print("--dry-run: grid + selection shown above, no OOS judgment or ledger write. Hand-check before the real run.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    rows = []
    for sym, vm, label in cases:
        rr = chosen[sym]
        k = H.ledger_count() + 1
        tr, days = trades_for(sym, vm, rr)
        all_days = [d["tday"] for d in days]
        name = f"Sharpe-optimized ORB exit, {label}, RR={rr} (IS-selected from {{{','.join(map(str, RR_GRID))}}}), Databento"
        r = H.test_idea(name, tr, all_days, sym, k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 173 (pre-registered, IS-selected Sharpe-optimal exit, OOS-validated)",
                               commit, date="2026-09-27")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round173_results.json"), "w") as f:
        json.dump(dict(chosen_rr=chosen, rows=rows), f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
