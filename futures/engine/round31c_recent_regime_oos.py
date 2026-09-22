"""
Round 31c: out-of-sample check on Round 31's MNQ+MGC combined sweep.

Round 31/31b built the resampling pool from FULL HISTORY (like Rounds 25/26/28
did) -- both instruments' entire backtest period pooled together. That's the same
shape of risk flagged repeatedly in this campaign: a result built on the whole
history can hide a strategy that only really worked in an earlier, different
regime. This round re-runs the SAME MNQ$225/MGC$600 peak-sizing point (and a
couple of neighbors) using ONLY the most recent walk-forward fold's OOS window
(2026-07-01 .. 2026-09-16, the same "most recent, most representative of what's
about to happen" fold used throughout Rounds 19-30) as the resampling pool,
instead of full history. If the 83.4% success / 3.8% ruin finding is real and not
an artifact of averaging over older, possibly-different market regimes, it should
hold up reasonably close to that on recent-only data. A big divergence would mean
the full-history number overstates what's likely in the next 20 real trading days.
"""
import os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, resample_causal
from round19_random_entry import causal_atr15_lookup, generate_random_entries, build_stop_signals, resolve_trailing
from round30_support_resistance import build_swing_touch_signals
from round30b_sequential_fix import resolve_trailing_sequential
from round28_withdrawal_deadline import N_EVAL_DAYS
from round31_combined_portfolio import combined_daily_series, simulate

RECENT_FOLD_START = pd.Timestamp("2026-07-01")
RECENT_FOLD_END = pd.Timestamp("2026-09-16")

def build_mnq_daily_recent(df1m, atr15, risk, n_seeds=15):
    mask = (df1m.index >= RECENT_FOLD_START) & (df1m.index <= RECENT_FOLD_END)
    df_recent = df1m.loc[mask]
    seeds_daily = []
    for seed in range(n_seeds):
        raw = generate_random_entries(df_recent, seed)
        sig = build_stop_signals(raw, atr15)
        trades = resolve_trailing(sig, df1m, "MNQ", risk, 1.5)  # exits can run past window end, use full df1m for lookups
        trades = trades[pd.to_datetime(trades["ts"]) <= RECENT_FOLD_END]
        trades["date"] = pd.to_datetime(trades["ts"]).dt.date
        daily = trades.groupby("date")["pnl"].sum()
        seeds_daily.append(daily)
    return seeds_daily

def build_mgc_daily_recent(df1m, h15, atr15, risk, swing_k=3, tol=0.50):
    sig = build_swing_touch_signals(df1m, h15, atr15, swing_k, tol)
    sig_recent = sig[(pd.to_datetime(sig["ts"]) >= RECENT_FOLD_START) & (pd.to_datetime(sig["ts"]) <= RECENT_FOLD_END)]
    trades, _ = resolve_trailing_sequential(sig_recent, df1m, "MGC", risk, 1.5)
    trades["date"] = pd.to_datetime(trades["ts"]).dt.date
    daily = trades.groupby("date")["pnl"].sum()
    return daily

if __name__ == "__main__":
    mnq_path = os.path.join("..","data","MNQ_CONTINUOUS.txt")
    mgc_path = os.path.join("..","data","MGC_CONTINUOUS.txt")
    df1m_mnq = load_1m(mnq_path); atr15_mnq = causal_atr15_lookup(df1m_mnq)
    df1m_mgc = load_1m(mgc_path); h15_mgc = resample_causal(df1m_mgc, "15min"); atr15_mgc = causal_atr15_lookup(df1m_mgc)
    print("data loaded", flush=True)

    n_recent_days_mnq = ((df1m_mnq.index >= RECENT_FOLD_START) & (df1m_mnq.index <= RECENT_FOLD_END)).sum()
    print(f"Recent-fold window: {RECENT_FOLD_START.date()} .. {RECENT_FOLD_END.date()} "
          f"({(RECENT_FOLD_END-RECENT_FOLD_START).days} calendar days)", flush=True)

    configs = [
        ("MNQ$188 MGC$500", 188, 500),
        ("MNQ$225 MGC$600 (Round 31 peak)", 225, 600),
        ("MNQ$300 MGC$800", 300, 800),
    ]
    for label, mnq_risk, mgc_risk in configs:
        mnq_seeds = build_mnq_daily_recent(df1m_mnq, atr15_mnq, mnq_risk, n_seeds=15)
        mgc_daily = build_mgc_daily_recent(df1m_mgc, h15_mgc, atr15_mgc, mgc_risk)
        n_mgc_trades_recent = len(mgc_daily)
        combined_series = [combined_daily_series(s, mgc_daily) for s in mnq_seeds]
        avg_days_covered = np.mean([len(s) for s in combined_series])
        res = simulate(combined_series, N_EVAL_DAYS)
        print(f"\n[{label}] recent-fold-only pool: avg {avg_days_covered:.0f} trading days of real data per seed, "
              f"{n_mgc_trades_recent} distinct MGC trade-days")
        print(f"  P(ruin)={res['p_ruin']:.1%} P(success)={res['p_success']:.1%} "
              f"P(neither)={res['p_neither']:.1%} median_final=${res['median_final']:,.2f}", flush=True)

    print("\nDONE.", flush=True)
