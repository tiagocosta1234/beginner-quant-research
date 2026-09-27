"""
Round 168: "continue until you find the strategy needed." Round 167 found
that volume confirmation on an opening-range breakout has a genuine,
monotonic dose-response (tighter volume filter -> better expectancy in 3 of
4 exit types), best cell OOS P=0.928 -- not a candidate, but the strongest,
most honestly-earned near-miss in this ledger. The natural next question,
not a re-tune of the same rule: does volume confirmation generalize to the
OTHER breakout levels Round 148 already found have a real (if too-small)
edge -- round numbers (N1), the previous day's high/low (N2), the overnight
high/low broken in RTH (N3) -- or was the opening range special?

Reuses Round 148's exact level/entry/stop machinery unchanged (first
1-minute close through a level after every earlier close of the session sat
on the other side; stop = 0.15x the 20-day average session range; target =
2x that stop, same as Round 148's own "exit a"). The ONLY new ingredient:
the breakout bar's own volume must clear a multiple of its trailing 30-bar
average (causal -- only bars before it, never a look-ahead average). vol
multiplier in {0 (replicates Round 148 exactly, the baseline), 1.5, 2.5}
(same thresholds as Round 167, not re-picked after seeing anything here).

Step 0, honest before running: this could easily NOT generalize -- the
opening range is a special 15-minute window right after the biggest
information event of the day (the open itself), so volume there may carry
different information than volume breaking a level at 11am or 2pm. Testing
because Round 167's dose-response was real enough to be worth checking for
generality, not because success is expected.

MNQ + MGC, 2022-12 -- 2026-09, $300 risk, real commission + 2-tick slippage,
flat by 16:00 ET. 3 levels (N1/N2/N3) x 3 volume multipliers = 9 variants.

9 variants. Ledger k=237 -> 246; OOS bar 1 - 0.01/246 at the last variant.

Candidate (each variant): idea_harness.test_idea's own rule (positive net
and gross; IS P(edge>0) >= 0.95; OOS P(edge>0) >= the bar at that variant's k).
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
from round147_batch_m import GRID, LAST_ENTRY, RISK, full, stop_sizes, load
from round148_batch_n import first_breaks, round_crosses, level_crosses

VOL_MULTS = [0.0, 1.5, 2.5]
TARGET_MULT = 2.0  # Round 148's own "exit a": target = 2x the stop


def vol_confirmed(b, idx, dirs, vol_mult):
    if vol_mult <= 0 or len(idx) == 0:
        return idx, dirs
    trail = b["vol"].rolling(30, min_periods=10).mean().shift(1).values
    ok = b["vol"].values[idx] >= vol_mult * trail[idx]
    ok &= ~np.isnan(trail[idx])
    return idx[ok], dirs[ok]


def signals(days, sym, setup, vol_mult):
    S_by_day = stop_sizes(days)
    rows, prev = [], None
    for d in days:
        b = full(d)
        S = S_by_day.get(d["tday"], np.nan)
        pos, dirs = np.array([], int), np.array([], int)
        if S > 0 and setup == "N1":
            pos, dirs = first_breaks(b, *round_crosses(GRID[sym]))
        elif S > 0 and setup == "N2" and prev is not None and prev["contract"] == d["contract"] \
                and (d["tday"] - prev["tday"]).days <= 5:
            pb = full(prev)
            pos, dirs = first_breaks(b, *level_crosses([pb["high"].max(), pb["low"].min()]))
        elif S > 0 and setup == "N3" and len(d["on"]) >= 300:
            pos, dirs = first_breaks(b, *level_crosses([d["on"]["high"].max(), d["on"]["low"].min()]), rth_only=True)
        pos, dirs = vol_confirmed(b, pos, dirs, vol_mult)
        for i, dr in zip(pos, dirs):
            e = b["close"].values[i]
            rows.append((b.index[i], dr, e, e - dr * S, e + dr * TARGET_MULT * S))
        prev = d
    return pd.DataFrame(rows, columns=["ts", "direction", "entry", "sl", "tp"])


def build_trades(data, setup, vol_mult):
    parts = []
    for sym, (days, bars) in data.items():
        tr = H.resolve_bracket(signals(days, sym, setup, vol_mult), bars, sym, risk=RISK)
        tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
        parts.append(tr)
    return pd.concat(parts, ignore_index=True)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    data = load()
    all_days = sorted({d["tday"] for days, _ in data.values() for d in days})

    grid = [(setup, vm) for setup in ("N1", "N2", "N3") for vm in VOL_MULTS]

    if dry:
        for setup, vm in grid:
            tr = build_trades(data, setup, vm)
            print(f"{setup} vol>={vm}x: {len(tr)} trades")
        print("\n--dry-run: counts only (trades ARE resolved for real, just not logged). Hand-check before the real run.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    labels = {"N1": "N1 round-number breakout", "N2": "N2 previous-day high/low breakout",
              "N3": "N3 overnight high/low breakout in RTH"}
    rows = []
    for setup, vm in grid:
        k = H.ledger_count() + 1
        tr = build_trades(data, setup, vm)
        vm_label = "no filter (replicates Round 148)" if vm == 0.0 else f">={vm}x trailing-30-bar vol"
        name = f"{labels[setup]}, target 2S, {vm_label}, MNQ+MGC"
        r = H.test_idea(name, tr, all_days, "MNQ", k, risk=RISK)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 168 (pre-registered, does volume confirmation generalize past the ORB?)",
                               commit, date="2026-09-27")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round168_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
