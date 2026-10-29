"""
Round 57: TOD filter re-sized to $1,600/trade (8x the $200 reference) and
VWAP-Z re-sized to $400/trade (2x reference), per direct request. Builds:
  1. Each edge alone, real backtest at its new size (not the old numbers
     scaled -- contract-count rounding makes scaling non-linear, confirmed
     already with the TOD-at-4x check earlier this session).
  2. Both combined into ONE sequentially-gated trade stream -- required
     because both are MNQ (same instrument, same account, can't hold two
     positions from two "independent" processes at once), extending
     round30b_sequential_fix.resolve_trailing_sequential (which only takes
     one scalar risk for a whole signal set) to accept each signal's OWN
     risk, tagged before merging, so TOD signals still size at $1,600 and
     VWAP-Z signals still size at $400 inside the one gated stream.
  3. The real deadline Monte Carlo (Round 28/31/34/56's machinery, unchanged)
     against the combined daily P&L series, to answer "what are the real
     odds of reaching the profit target before 2026-10-30 at this sizing."
"""
import json
import os
import datetime as dt
import numpy as np
import pandas as pd

from round11_fvg_bias import load_1m
from round19_random_entry import causal_atr15_lookup, generate_random_entries, build_stop_signals, resolve_trailing, TRAIL_ATR_MULT
from round30b_sequential_fix import resolve_trailing_sequential
from round49_vwap_zscore import compute_session_vwap_z, build_zscore_signals
from round31_combined_portfolio import (
    CURRENT_BALANCE, TRAILING_FLOOR, DAILY_LOSS_LIMIT, PROFIT_TARGET_GAP, BLOCK_SIZE,
)
from round34_fine_sizing_sweep import simulate_first_crossing
from round28_withdrawal_deadline import N_EVAL_DAYS
from round11_fvg_bias import POINT_VALUE, TICK_SIZE, COMMISSION_RT

N_MC_PATHS = 8000
TOD_RISK = 1600
VWAPZ_RISK = 400

_T2 = dt.time(13, 50)
_CLOSE = dt.time(16, 0)
Z_THRESH = 2.5
SEED = 0


def resolve_trailing_sequential_per_signal_risk(sig_df, df1m, symbol, trail_mult, max_hold_bars=390):
    """Same one-position-at-a-time sequential resolver as
    round30b_sequential_fix.resolve_trailing_sequential, extended to read
    each signal's OWN risk from a `risk` column instead of one shared
    scalar -- needed here because TOD and VWAP-Z signals are merged into
    one MNQ stream but must keep their own distinct sizing ($1,600 vs
    $400). All other mechanics (trailing distance, gating, commission,
    slippage) are identical, not re-derived."""
    pv = POINT_VALUE[symbol]
    tick = TICK_SIZE[symbol]
    slip_dollars_rt = 2 * tick * pv
    ts = df1m.index.values
    hi = df1m["high"].values
    lo = df1m["low"].values
    cl = df1m["close"].values
    n = len(df1m)
    results = []
    next_free_pos = 0
    sig_df = sig_df.sort_values("ts").reset_index(drop=True)
    skipped_overlap = 0
    for r in sig_df.itertuples(index=False):
        pos = np.searchsorted(ts, np.datetime64(r.ts), side="right")
        if pos >= n:
            continue
        if pos < next_free_pos:
            skipped_overlap += 1
            continue
        init_dist = abs(r.entry - r.stop)
        if init_dist <= 0:
            continue
        trail_dist = trail_mult * init_dist
        risk_dollar = r.risk
        contracts = max(1, int(risk_dollar // (init_dist * pv)))
        commission = COMMISSION_RT * contracts
        end_pos = min(pos + max_hold_bars, n - 1)
        cur_stop = r.entry - trail_dist if r.direction == 1 else r.entry + trail_dist
        best = r.entry
        exit_px = None
        outcome = "timeout"
        exit_i = end_pos
        for i in range(pos, end_pos + 1):
            bar_hi, bar_lo = hi[i], lo[i]
            if r.direction == 1:
                if bar_lo <= cur_stop:
                    exit_px = cur_stop
                    outcome = "trail_stop"
                    exit_i = i
                    break
                best = max(best, bar_hi)
                cur_stop = max(cur_stop, best - trail_dist)
            else:
                if bar_hi >= cur_stop:
                    exit_px = cur_stop
                    outcome = "trail_stop"
                    exit_i = i
                    break
                best = min(best, bar_lo)
                cur_stop = min(cur_stop, best + trail_dist)
        if exit_px is None:
            exit_px = cl[end_pos]
            outcome = "session_flatten"
            exit_i = end_pos
        move = (exit_px - r.entry) if r.direction == 1 else (r.entry - exit_px)
        pnl = move * pv * contracts - commission - slip_dollars_rt * contracts
        results.append((r.ts, symbol, r.direction, risk_dollar, contracts, pnl, outcome, r.source))
        next_free_pos = exit_i + 1
    out = pd.DataFrame(results, columns=["ts", "symbol", "direction", "risk", "contracts", "pnl", "outcome", "source"])
    return out, skipped_overlap


def to_dated_cum(trades):
    trades = trades.copy()
    trades["date"] = pd.to_datetime(trades["ts"]).dt.date
    daily = trades.groupby("date", as_index=False)["pnl"].sum().sort_values("date")
    daily["cum_pnl"] = daily["pnl"].cumsum()
    return daily


def worst_dd(daily):
    running_max = daily["cum_pnl"].iloc[0]
    worst = 0.0
    worst_date = None
    for d, c in zip(daily["date"], daily["cum_pnl"]):
        if c > running_max:
            running_max = c
        dd = c - running_max
        if dd < worst:
            worst = dd
            worst_date = d
    return worst, worst_date


def worst_monthly_dd(daily):
    d = daily.copy()
    d["month"] = pd.to_datetime(d["date"]).dt.to_period("M")
    d["running_max_m"] = d["cum_pnl"].cummax()
    d["dd_m"] = d["cum_pnl"] - d["running_max_m"]
    return float(d.groupby("month")["dd_m"].min().min())


print("Loading MNQ...", flush=True)
mnq_1m = load_1m(os.path.join("..", "data", "MNQ_CONTINUOUS.txt"))
atr15_mnq = causal_atr15_lookup(mnq_1m)
mnq_z = compute_session_vwap_z(mnq_1m)

raw = generate_random_entries(mnq_1m, SEED)
sig_base = build_stop_signals(raw, atr15_mnq)
t = sig_base["ts"].dt.time
sig_tod = sig_base[(t >= _T2) & (t < _CLOSE)]
sig_z = build_zscore_signals(mnq_z, atr15_mnq, Z_THRESH)

# --- 1. Each edge alone, at its new size ---
# TOD fires at most once/day by construction -- resolve_trailing (no overlap
# gating needed) matches every prior TOD computation this session. VWAP-Z
# fires many times/day (mean-reversion touches), so it needs the sequential,
# one-position-at-a-time resolver -- using the plain one here first produced
# 38,301 "trades" and $2.3M P&L, wildly inconsistent with every earlier
# VWAP-Z number in this session (~3,391 trades); using resolve_trailing_sequential
# instead, matching round54_generate_equity_curves.py's own convention.
trades_tod = resolve_trailing(sig_tod, mnq_1m, "MNQ", TOD_RISK, TRAIL_ATR_MULT)
trades_z, _ = resolve_trailing_sequential(sig_z, mnq_1m, "MNQ", VWAPZ_RISK, TRAIL_ATR_MULT)

daily_tod = to_dated_cum(trades_tod)
daily_z = to_dated_cum(trades_z)
dd_tod, dd_tod_date = worst_dd(daily_tod)
dd_z, dd_z_date = worst_dd(daily_z)
wr_tod = round(float((trades_tod["pnl"] > 0).mean() * 100), 1)
wr_z = round(float((trades_z["pnl"] > 0).mean() * 100), 1)

print(f"\nTOD @ ${TOD_RISK}: trades={len(trades_tod)} win_rate={wr_tod}% "
      f"final=${daily_tod['cum_pnl'].iloc[-1]:,.0f} worst_dd=${dd_tod:,.0f} at {dd_tod_date}")
print(f"VWAP-Z @ ${VWAPZ_RISK}: trades={len(trades_z)} win_rate={wr_z}% "
      f"final=${daily_z['cum_pnl'].iloc[-1]:,.0f} worst_dd=${dd_z:,.0f} at {dd_z_date}")

# --- 2. Combined, per-signal risk, sequentially gated ---
sig_tod_tagged = sig_tod.copy()
sig_tod_tagged["risk"] = TOD_RISK
sig_tod_tagged["source"] = "tod"
sig_z_tagged = sig_z.copy()
sig_z_tagged["risk"] = VWAPZ_RISK
sig_z_tagged["source"] = "vwapz"
combined_sig = pd.concat([sig_tod_tagged, sig_z_tagged], ignore_index=True).sort_values("ts").reset_index(drop=True)

trades_combined, skipped = resolve_trailing_sequential_per_signal_risk(combined_sig, mnq_1m, "MNQ", TRAIL_ATR_MULT)
daily_combined = to_dated_cum(trades_combined)
dd_combined, dd_combined_date = worst_dd(daily_combined)
wr_combined = round(float((trades_combined["pnl"] > 0).mean() * 100), 1)
worst_month_combined = worst_monthly_dd(daily_combined)

print(f"\nCOMBINED (TOD@${TOD_RISK} + VWAP-Z@${VWAPZ_RISK}, gated): "
      f"trades={len(trades_combined)} (skipped {skipped} overlapping of {len(trades_combined)+skipped} raw) "
      f"win_rate={wr_combined}% final=${daily_combined['cum_pnl'].iloc[-1]:,.0f} "
      f"worst_dd=${dd_combined:,.0f} at {dd_combined_date} worst_monthly_dd=${worst_month_combined:,.0f}")
print("by source:", trades_combined["source"].value_counts().to_dict())

# --- 3. Real deadline Monte Carlo on the combined series ---
combined_daily_series = daily_combined.set_index("date")["pnl"]
series_list = [combined_daily_series]
seed_results = [simulate_first_crossing(series_list, N_EVAL_DAYS, N_MC_PATHS, mc_seed=s) for s in (31, 32, 33)]
p_success = float(np.mean([r["p_success"] for r in seed_results]))
p_ruin = float(np.mean([r["p_ruin"] for r in seed_results]))
p_neither = float(np.mean([r["p_neither"] for r in seed_results]))
print(f"\nDEADLINE MONTE CARLO (N_EVAL_DAYS={N_EVAL_DAYS}, buffer=${CURRENT_BALANCE - TRAILING_FLOOR:,.2f}, "
      f"target=${PROFIT_TARGET_GAP:,.2f}):")
print(f"  P(success)={p_success:.1%}  P(ruin)={p_ruin:.1%}  P(neither)={p_neither:.1%}")

# --- save chart data (calendar-dated points for all three curves) ---
def points_from_daily(daily):
    return [{"t": d.isoformat(), "v": round(float(c), 2)} for d, c in zip(daily["date"], daily["cum_pnl"])]

out = {
    "tod1600": {
        "label": "TOD filter @ $1,600/trade",
        "points": points_from_daily(daily_tod),
        "trades": int(len(trades_tod)), "winRate": wr_tod,
        "finalPnl": round(float(daily_tod["cum_pnl"].iloc[-1]), 0),
        "worstDD": round(float(dd_tod), 0), "worstDDDate": dd_tod_date.isoformat(),
        "worstMonthlyDD": round(worst_monthly_dd(daily_tod), 0),
    },
    "vwapz400": {
        "label": "VWAP-Z @ $400/trade",
        "points": points_from_daily(daily_z),
        "trades": int(len(trades_z)), "winRate": wr_z,
        "finalPnl": round(float(daily_z["cum_pnl"].iloc[-1]), 0),
        "worstDD": round(float(dd_z), 0), "worstDDDate": dd_z_date.isoformat(),
        "worstMonthlyDD": round(worst_monthly_dd(daily_z), 0),
    },
    "combined1600_400": {
        "label": "Combined (TOD $1,600 + VWAP-Z $400, gated)",
        "points": points_from_daily(daily_combined),
        "trades": int(len(trades_combined)), "winRate": wr_combined,
        "finalPnl": round(float(daily_combined["cum_pnl"].iloc[-1]), 0),
        "worstDD": round(float(dd_combined), 0), "worstDDDate": dd_combined_date.isoformat(),
        "worstMonthlyDD": round(worst_month_combined, 0),
    },
}
outpath = "two_curves/curve_data.js"
with open(outpath, "w", encoding="utf-8") as f:
    f.write("window.CURVE_DATA = " + json.dumps(out) + ";\n")
print("\nwrote", outpath)
print("DONE.")
