"""
Round 58: double the combined sizing from Round 57 (TOD $1,600 -> $3,200,
VWAP-Z $400 -> $800), real backtests at the new sizes (not scaled), then
answer three direct stats questions on the combined, gated stream:
  1. Average REAL dollar risk per trade (contracts * stop_distance * point_value,
     not the nominal target -- contract-count flooring means actual risk taken
     is always <= the nominal figure, same effect already seen in the 4x/8x
     sizing checks this session).
  2. EV/day (total net profit / number of distinct trading days the combined
     stream actually traded on).
  3. Total net profit broken down by day of week.
"""
import json
import os
import datetime as dt
import numpy as np
import pandas as pd

from round11_fvg_bias import load_1m, POINT_VALUE
from round19_random_entry import causal_atr15_lookup, generate_random_entries, build_stop_signals, resolve_trailing, TRAIL_ATR_MULT
from round30b_sequential_fix import resolve_trailing_sequential
from round49_vwap_zscore import compute_session_vwap_z, build_zscore_signals
from round57_tod1600_vwapz400_combined import resolve_trailing_sequential_per_signal_risk, to_dated_cum, worst_dd, worst_monthly_dd
from round11_fvg_bias import TICK_SIZE, COMMISSION_RT


def resolve_sequential_with_real_risk(sig_df, df1m, symbol, trail_mult, max_hold_bars=390):
    """Same as round57's resolve_trailing_sequential_per_signal_risk, but also
    emits the REAL dollar risk realized per trade (contracts * init_dist *
    point_value) directly from the same loop that computes contracts -- safer
    than re-deriving it via an external join afterward, which broke on
    duplicate timestamps (two signals firing in the same 1-minute bar)."""
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
        real_risk = contracts * init_dist * pv
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
        results.append((r.ts, symbol, r.direction, risk_dollar, real_risk, contracts, pnl, outcome, r.source))
        next_free_pos = exit_i + 1
    out = pd.DataFrame(results, columns=["ts", "symbol", "direction", "risk", "real_risk", "contracts", "pnl", "outcome", "source"])
    return out, skipped_overlap

TOD_RISK = 3200
VWAPZ_RISK = 800

_T2 = dt.time(13, 50)
_CLOSE = dt.time(16, 0)
Z_THRESH = 2.5
SEED = 0

print("Loading MNQ...", flush=True)
mnq_1m = load_1m(os.path.join("..", "data", "MNQ_CONTINUOUS.txt"))
atr15_mnq = causal_atr15_lookup(mnq_1m)
mnq_z = compute_session_vwap_z(mnq_1m)

raw = generate_random_entries(mnq_1m, SEED)
sig_base = build_stop_signals(raw, atr15_mnq)
t = sig_base["ts"].dt.time
sig_tod = sig_base[(t >= _T2) & (t < _CLOSE)]
sig_z = build_zscore_signals(mnq_z, atr15_mnq, Z_THRESH)

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

sig_tod_tagged = sig_tod.copy()
sig_tod_tagged["risk"] = TOD_RISK
sig_tod_tagged["source"] = "tod"
sig_z_tagged = sig_z.copy()
sig_z_tagged["risk"] = VWAPZ_RISK
sig_z_tagged["source"] = "vwapz"
combined_sig = pd.concat([sig_tod_tagged, sig_z_tagged], ignore_index=True).sort_values("ts").reset_index(drop=True)
trades_combined, skipped = resolve_sequential_with_real_risk(combined_sig, mnq_1m, "MNQ", TRAIL_ATR_MULT)

daily_combined = to_dated_cum(trades_combined)
dd_combined, dd_combined_date = worst_dd(daily_combined)
wr_combined = round(float((trades_combined["pnl"] > 0).mean() * 100), 1)
worst_month_combined = worst_monthly_dd(daily_combined)
print(f"\nCOMBINED (TOD@${TOD_RISK} + VWAP-Z@${VWAPZ_RISK}, gated): trades={len(trades_combined)} "
      f"(skipped {skipped} overlapping of {len(trades_combined)+skipped} raw) win_rate={wr_combined}% "
      f"final=${daily_combined['cum_pnl'].iloc[-1]:,.0f} worst_dd=${dd_combined:,.0f} at {dd_combined_date} "
      f"worst_monthly_dd=${worst_month_combined:,.0f}")
print("by source:", trades_combined["source"].value_counts().to_dict())

# --- 1. Average REAL dollar risk per trade (actual, not nominal) ---
avg_nominal_risk = trades_combined["risk"].mean()
avg_real_risk = trades_combined["real_risk"].mean()
avg_real_risk_tod = trades_combined.loc[trades_combined["source"] == "tod", "real_risk"].mean()
avg_real_risk_vwapz = trades_combined.loc[trades_combined["source"] == "vwapz", "real_risk"].mean()
print(f"\nAVG RISK/TRADE (combined, all {len(trades_combined)} trades): "
      f"nominal (blended by count) = ${avg_nominal_risk:,.2f}, "
      f"REAL (contracts x stop_dist x point_value) = ${avg_real_risk:,.2f}")
print(f"  by source: TOD real avg=${avg_real_risk_tod:,.2f} (nominal ${TOD_RISK}), "
      f"VWAP-Z real avg=${avg_real_risk_vwapz:,.2f} (nominal ${VWAPZ_RISK})")

# --- 2. EV/day ---
total_pnl = trades_combined["pnl"].sum()
n_trading_days = daily_combined["date"].nunique()
ev_per_day = total_pnl / n_trading_days
print(f"EV/DAY: total_pnl=${total_pnl:,.2f} / {n_trading_days} active trading days = ${ev_per_day:,.2f}/day")

# --- 3. Net profit by day of week ---
trades_combined_dated = trades_combined.copy()
trades_combined_dated["dow"] = pd.to_datetime(trades_combined_dated["ts"]).dt.day_name()
by_dow = trades_combined_dated.groupby("dow")["pnl"].agg(["sum", "count", "mean"])
dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
by_dow = by_dow.reindex([d for d in dow_order if d in by_dow.index])
print("\nNET PROFIT BY DAY OF WEEK:")
print(by_dow.to_string())

# --- save chart data ---
def points_from_daily(daily):
    return [{"t": d.isoformat(), "v": round(float(c), 2)} for d, c in zip(daily["date"], daily["cum_pnl"])]

curve_path = "two_curves/curve_data.js"
existing = json.loads(open(curve_path, encoding="utf-8").read().split("window.CURVE_DATA = ", 1)[1].rstrip("\n;"))
spx_entry = existing.get("spx")

out = {
    "tod3200": {
        "label": "TOD filter @ $3,200/trade",
        "points": points_from_daily(daily_tod),
        "trades": int(len(trades_tod)), "winRate": wr_tod,
        "finalPnl": round(float(daily_tod["cum_pnl"].iloc[-1]), 0),
        "worstDD": round(float(dd_tod), 0), "worstDDDate": dd_tod_date.isoformat(),
        "worstMonthlyDD": round(worst_monthly_dd(daily_tod), 0),
    },
    "vwapz800": {
        "label": "VWAP-Z @ $800/trade",
        "points": points_from_daily(daily_z),
        "trades": int(len(trades_z)), "winRate": wr_z,
        "finalPnl": round(float(daily_z["cum_pnl"].iloc[-1]), 0),
        "worstDD": round(float(dd_z), 0), "worstDDDate": dd_z_date.isoformat(),
        "worstMonthlyDD": round(worst_monthly_dd(daily_z), 0),
    },
    "combined3200_800": {
        "label": "Combined (TOD $3,200 + VWAP-Z $800, gated)",
        "points": points_from_daily(daily_combined),
        "trades": int(len(trades_combined)), "winRate": wr_combined,
        "finalPnl": round(float(daily_combined["cum_pnl"].iloc[-1]), 0),
        "worstDD": round(float(dd_combined), 0), "worstDDDate": dd_combined_date.isoformat(),
        "worstMonthlyDD": round(worst_month_combined, 0),
    },
}
if spx_entry:
    out["spx"] = spx_entry

with open(curve_path, "w", encoding="utf-8") as f:
    f.write("window.CURVE_DATA = " + json.dumps(out) + ";\n")
print("\nwrote", curve_path)
print("DONE.")
