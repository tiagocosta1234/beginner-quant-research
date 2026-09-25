"""
Round 130: re-check the two live_bot strategies never tested flat at the close.

live_bot/main.py can run five strategies (BOT_STRATEGY). Round 120b settled
`manual` and `vwap_zscore` (no edge flat at the close) and Round 76 `ote_fvg`
(negative). The other two were validated only with resolvers that hold
positions past the session close (round19 resolve_trailing, max_hold_bars not
session-bounded -- EDGE_AUDIT_2026-09-20):

  random_entry_atr_trail   one random entry per RTH day, random direction, stop
                           1.0 x ATR15, trail 1.5x (Round 19; the bot's default
                           tod_filter=False = all day). Seeds 0-4 pooled.
  support_resistance_bounce  MGC, fade the first touch of a confirmed 15-minute
                           swing level (swing_k=3, tol_atr=0.50, the live
                           parameters), stop 1.0 x ATR15, trail 1.5x (Round 30/30b).
                           Its backtest fills at the touching bar's extreme
                           (min(bar high, level) for a short) -- a price not
                           knowable in advance. Tested both ways: as validated,
                           and entering at the touching bar's close (the verdict).

Same parameters as live_bot; nothing tuned. Through idea_harness.resolve_trailing
(flat at each session's last bar), $300 risk, RTH 09:30-16:00 ET (MGC converted
from UTC). 3 variants take the ledger from k=63 to k=66.
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
from round11_fvg_bias import resample_causal
from round19_random_entry import causal_atr15_lookup, generate_random_entries, build_stop_signals
from round30_support_resistance import build_swing_touch_signals

if __name__ == "__main__":
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k_final = H.ledger_count() + 3
    rows = []

    mnq = J.load_mnq()
    atr_nq = causal_atr15_lookup(mnq)
    trs = [H.resolve_trailing(build_stop_signals(generate_random_entries(mnq, seed), atr_nq), mnq, "MNQ") for seed in range(5)]
    rows.append(H.test_idea("live random_entry_atr_trail, all day, MNQ, seeds 0-4 pooled",
                            pd.concat(trs, ignore_index=True), mnq.index.normalize().unique(), "MNQ", k_final))

    mgc = J.load_mgc_et()
    atr_gc = causal_atr15_lookup(mgc)
    sig = build_swing_touch_signals(mgc, resample_causal(mgc, "15min"), atr_gc, 3, 0.50)[["ts", "direction", "entry", "stop"]]
    gc_days = mgc.index.normalize().unique()
    rows.append(H.test_idea("live support_resistance_bounce MGC, fill at bar extreme (as validated)",
                            H.resolve_trailing(sig, mgc, "MGC"), gc_days, "MGC", k_final))
    close = mgc["close"].reindex(pd.to_datetime(sig["ts"])).to_numpy()
    dist = (sig["entry"] - sig["stop"]).abs().to_numpy()
    honest = sig.assign(entry=close, stop=close - sig["direction"].to_numpy() * dist)
    rows.append(H.test_idea("live support_resistance_bounce MGC, entry at touch bar's close",
                            H.resolve_trailing(honest, mgc, "MGC"), gc_days, "MGC", k_final))

    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(H.ledger_rows(rows, "Round 130 (live_bot re-check)", commit)) + "\n")
    with open(os.path.join(H.HERE, "round130_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n==== {sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()} ====")
