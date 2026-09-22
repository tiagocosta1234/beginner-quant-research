import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
import pandas as pd
import numpy as np
from round11_fvg_bias import load_1m
from round19_random_entry import causal_atr15_lookup, generate_random_entries, build_stop_signals, resolve_trailing

RISK = 2000.0
TRAIL_MULT = 1.5
SEEDS = list(range(8))

df1m = load_1m("../data/MNQ_CONTINUOUS.txt")
print(f"MNQ: {len(df1m)} bars, {df1m.index.min()} -> {df1m.index.max()}", flush=True)
atr15 = causal_atr15_lookup(df1m)

all_curves = {}
summary_rows = []
for seed in SEEDS:
    raw = generate_random_entries(df1m, seed)
    sig = build_stop_signals(raw, atr15)
    trades = resolve_trailing(sig, df1m, "MNQ", RISK, TRAIL_MULT)
    trades = trades.sort_values("ts").reset_index(drop=True)
    trades["cum_pnl"] = trades["pnl"].cumsum()
    all_curves[seed] = trades[["ts", "pnl", "cum_pnl"]].copy()
    peak = trades["cum_pnl"].cummax()
    dd = trades["cum_pnl"] - peak
    summary_rows.append({
        "seed": seed, "n_trades": len(trades), "final_pnl": trades["cum_pnl"].iloc[-1],
        "win_rate": (trades["pnl"] > 0).mean(), "max_drawdown": dd.min(),
    })
    all_curves[seed].to_csv(f"equity2000_seed{seed}.csv", index=False)

summary = pd.DataFrame(summary_rows)
print(summary.to_string(index=False))
summary.to_csv("equity2000_summary.csv", index=False)
