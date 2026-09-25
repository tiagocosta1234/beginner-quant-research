"""
Round 132: try to break the one lead from Round 131 -- "STDV continuation".

The rule (the exact mirror of Round 127's 2.0-SD / range-edge fade, found by
inverting 26 losers, so it was SELECTED from many tries):
  Asian range = bars (20:00, 00:00] ET, width w. Between 00:00 and 12:00, the
  first bar that trades through high + k*w (or low - k*w) by >= 1 tick decides
  the day: go WITH the move at that bar's close; stop at the Asian range edge
  (the high for a long); target = the level + T*w (k=2.0, T=0.5 for the lead).
  Skip the day if the close is already past the target. Flat at 16:00.
  On MNQ 2022-12..2026-09: n=520, +$19.3/trade, IS +$11.3 (P 0.95), OOS +$41.1 (P 0.80).

Pre-registered tests -- committed before any result was run:
  1. Reproduction: this standalone builder must give n=520, +$19.3 on MNQ.
  2. Neighborhood (MNQ, same data, can only FALSIFY): k in {1.5, 1.75, 2.0,
     2.25, 2.5} x T in {0.25, 0.5, 0.75}. If the median net/trade of the 15 is
     <= 0, the lead is an isolated spike -> rejected.
  3. Independent replication on MGC (24-hour files, never used to find the
     rule): exactly k=2.0, T=0.5. One pre-specified test on unseen data, so the
     replication bar is bootstrap P(edge>0) >= 0.99 over all its trades, with
     positive net and before-cost expectancy.
  4. Stability: MNQ lead's net/trade by calendar year (descriptive).
Verdict: a LEAD worth forward-testing only if 2 and 3 both pass; otherwise rejected.
All 16 variants (15 MNQ + 1 MGC) are added to the ledger.

Amendment before any result: the first run stopped at check 1 (n=524, +$19.14 vs 520,
+$19.3) because the 8-tick minimum was applied to the stop side instead of the target
side as in the mirrored original; fixed to mirror it exactly. No other result was produced.
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
from round11_fvg_bias import TICK_SIZE

T_ = dt.time
MIN_STOP_TICKS = 8


def continuation_signals(days, symbol, k, tgt):
    tick, out = TICK_SIZE[symbol], []
    for d in days:
        bars = pd.concat([d["on"], d["session"]])
        t = bars.index.time
        asia = bars[((t > T_(20, 0)) | (t == T_(0, 0))) & (t != T_(20, 0))]
        if len(asia) < 200:
            continue
        a_hi, a_lo = asia["high"].max(), asia["low"].min()
        w = a_hi - a_lo
        if w <= 0:
            continue
        up, dn = a_hi + k * w, a_lo - k * w
        win = bars[(t > T_(0, 0)) & (t <= T_(12, 0))]
        for ts, h, l, c in zip(win.index, win["high"].values, win["low"].values, win["close"].values):
            if h >= up + tick:
                dd, sl, tp = 1, a_hi, up + tgt * w
            elif l <= dn - tick:
                dd, sl, tp = -1, a_lo, dn - tgt * w
            else:
                continue
            # the mirrored original (a fade) required its own stop -- this rule's target -- to be
            # >= 8 ticks away; keep that exactly, plus the usual minimum stop
            if (dd * (c - sl) > 0 and dd * (tp - c) > 0 and abs(c - sl) >= MIN_STOP_TICKS * tick
                    and abs(tp - c) >= MIN_STOP_TICKS * tick):
                out.append((ts, dd, c, sl, tp))
            break  # the first touch of either level decides the day
    return pd.DataFrame(out, columns=["ts", "direction", "entry", "sl", "tp"])


if __name__ == "__main__":
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k_final = H.ledger_count() + 16
    mnq, mgc = H.load_days("MNQ"), H.load_days("MGC")
    nq_bars, gc_bars = H.bars_from_days(mnq, "all"), H.bars_from_days(mgc, "all")
    nq_days, gc_days = [d["tday"] for d in mnq], [d["tday"] for d in mgc]

    lead = H.resolve_bracket(continuation_signals(mnq, "MNQ", 2.0, 0.5), nq_bars, "MNQ")
    ok = len(lead) == 520 and abs(lead["pnl"].mean() - 19.3) < 0.15
    print(f"1. reproduction: n={len(lead)} ${lead['pnl'].mean():+.2f}/trade (want 520, +$19.3) -> {'OK' if ok else 'MISMATCH'}")
    if not ok:
        sys.exit(1)

    print(f"\n2. neighborhood on MNQ (falsification only; k after this round = {k_final})")
    rows, grid = [], {}
    for k in [1.5, 1.75, 2.0, 2.25, 2.5]:
        for tgt in [0.25, 0.5, 0.75]:
            tr = H.resolve_bracket(continuation_signals(mnq, "MNQ", k, tgt), nq_bars, "MNQ")
            r = H.test_idea(f"MNQ STDV continuation k={k} T={tgt}", tr, nq_days, "MNQ", k_final)
            rows.append(r)
            grid[(k, tgt)] = r["exp"]
    tbl = pd.Series(grid).unstack()
    print("\n   net $/trade (rows k, columns T):\n" + tbl.round(1).to_string())
    med = float(np.median(list(grid.values())))
    falsified = med <= 0
    print(f"   median of 15 = ${med:+.1f} -> {'FALSIFIED (isolated spike)' if falsified else 'not falsified'}")

    print("\n3. independent replication on MGC, k=2.0 T=0.5 (bar: P(edge>0) >= 0.99, net and gross > 0)")
    gtr = H.resolve_bracket(continuation_signals(mgc, "MGC", 2.0, 0.5), gc_bars, "MGC")
    g = H.test_idea("MGC STDV continuation k=2.0 T=0.5 (replication)", gtr, gc_days, "MGC", k_final)
    st = J.edge_stats(gtr, n_boot=40_000)
    replicated = st["p_pos"] >= 0.99 and g["exp"] > 0 and g["exp_gross"] > 0
    print(f"   all trades: n={st['n']} ${st['exp']:+.1f}/trade P(edge>0)={st['p_pos']:.4f} -> "
          f"{'REPLICATED' if replicated else 'not replicated'}")
    rows.append(g)

    print("\n4. MNQ lead by calendar year (descriptive)")
    by = lead.groupby(pd.to_datetime(lead["entry_ts"]).dt.year)["pnl"].agg(["count", "mean", "sum"])
    print(by.round(1).to_string())

    verdict = "LEAD: worth forward-testing" if (not falsified and replicated) else "REJECTED"
    print(f"\n==== verdict: {verdict} ====")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(H.ledger_rows(rows, "Round 132 (STDV continuation checks, pre-registered)", commit)) + "\n")
    with open(os.path.join(H.HERE, "round132_results.json"), "w") as f:
        json.dump(dict(rows=rows, grid={f"{k}|{t}": v for (k, t), v in grid.items()}, median=med, falsified=falsified,
                       mgc=dict(st, replicated=replicated), by_year=by.reset_index().to_dict("records"), verdict=verdict),
                  f, indent=1, default=str)
