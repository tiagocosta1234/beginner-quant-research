"""
Round 226 (the trader, 2026-09-30): "test it in another sample" -- Round 225
already rebuilt the trader's TOD-leg logic on Databento NQ (same index as MNQ,
independent data source) and found the aligned-vs-against pattern
reverses. This round asks the natural next question: does that hold on
markets that are NOT the same index, using the same real Databento
1-minute data already in this repo (2019-2026)?

ES (S&P 500 e-mini) -- a different equity index, still correlated with
Nasdaq but a real, distinct market. GC (gold) -- a genuinely different
asset class, the strongest available test of whether "trend-alignment on
the trader's random-entry TOD leg" is some general microstructure property or
just noise specific to one dataset.

Same exact construction as Round 224/225's Test 1, unmodified: causal
15-min EMA trend lookup, split TOD's random-entry signals into trend-
aligned vs trend-against, resolve each bucket with round19's own
resolve_trailing (unmodified), bootstrap P(aligned mean > against mean),
across the same 5-span grid. Real CME specs added to
round11_fvg_bias's dicts at runtime only (Round 171's own established
pattern): ES $50/pt tick 0.25, GC $100/pt tick 0.10. Same nominal $1,680
risk reused throughout for internal (aligned vs against) consistency,
not cross-instrument dollar comparison -- the same simplification Round
225 already used and justified for NQ.

Not ledger-eligible (a further replication check on an already-proposed
research variant, not a new idea test). manual_strategy.py,
combined_strategy.py, and live_bot remain untouched.
"""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd

from round11_fvg_bias import POINT_VALUE, TICK_SIZE
from round19_random_entry import generate_random_entries, build_stop_signals, causal_atr15_lookup, \
    resolve_trailing, TRAIL_ATR_MULT
from round223_manual_confluence_filters import TOD_RISK
from round224_manual_confluence_robustness import htf_trend_lookup, split_aligned_against, bootstrap_p_greater, SPAN_GRID
from round171_databento_orb_replication import load_days_databento

HERE = os.path.dirname(os.path.abspath(__file__))
POINT_VALUE["ES"], TICK_SIZE["ES"] = 50.0, 0.25
POINT_VALUE["GC"], TICK_SIZE["GC"] = 100.0, 0.10
T2, CLOSE_T, SEED = dt.time(13, 50), dt.time(16, 0), 0


def continuous_bars(sym):
    days = load_days_databento(sym)
    return pd.concat([d[k] for d in days for k in ("on", "session")]).sort_index()


def run_symbol(sym):
    bars = continuous_bars(sym)
    print(f"\n{sym} Databento: {len(bars)} 1-min bars, {bars.index.min()} -> {bars.index.max()}", flush=True)
    atr15 = causal_atr15_lookup(bars)
    raw = generate_random_entries(bars, SEED)
    sig_base = build_stop_signals(raw, atr15)
    t = sig_base["ts"].dt.time
    sig_tod = sig_base[(t >= T2) & (t < CLOSE_T)].copy()
    print(f"  TOD signals (13:50-16:00 ET): {len(sig_tod)}", flush=True)

    rows = []
    for span in SPAN_GRID:
        trend = htf_trend_lookup(bars, span)
        aligned, against, _ = split_aligned_against(sig_tod, trend)
        tr_a = resolve_trailing(aligned[["ts", "direction", "entry", "stop"]], bars, sym, TOD_RISK, TRAIL_ATR_MULT)
        tr_g = resolve_trailing(against[["ts", "direction", "entry", "stop"]], bars, sym, TOD_RISK, TRAIL_ATR_MULT)
        pa, pg = tr_a["pnl"].to_numpy(float), tr_g["pnl"].to_numpy(float)
        p_gt = bootstrap_p_greater(pa, pg)
        a_mean = pa.mean() if len(pa) else float("nan")
        g_mean = pg.mean() if len(pg) else float("nan")
        print(f"  span={span:>3}: aligned n={len(pa):>4} mean=${a_mean:+7.2f}  |  "
              f"against n={len(pg):>4} mean=${g_mean:+7.2f}  |  P(aligned>against)={p_gt:.4f}", flush=True)
        rows.append(dict(span=span, aligned_n=len(pa), aligned_mean=float(a_mean) if pa.size else None,
                          against_n=len(pg), against_mean=float(g_mean) if pg.size else None,
                          p_aligned_gt_against=p_gt))
    return rows


if __name__ == "__main__":
    results = {}
    for sym in ("ES", "GC"):
        results[sym] = run_symbol(sym)
    with open(os.path.join(HERE, "round226_results.json"), "w") as f:
        json.dump(results, f, indent=1, default=str)
    print("\nSaved round226_results.json", flush=True)
