"""
Round 223 (the trader, 2026-09-30): "lets try to improve the profit factor of
manual on a new branch thorough aditional confluences, dont modify the
original" -- a new, standalone research script. Nothing in live_bot/,
manual_strategy.py, combined_strategy.py, or any prior round file is
touched; every function this script needs is IMPORTED from its existing
source, never redefined or edited.

Real baseline (already published, Round 205, on the trader's RAW/unclipped
daily series): profit_factor=1.5948, win_rate=52.7%, mean/day=$727.96,
n_active=934/998 days. Reproduced here as a sanity check before trusting
any confluence-filtered number.

the trader is TOD (round19's random-entry/ATR-trail edge, filtered to the last
third of RTH, 13:50-16:00 ET) + VWAP-Z (round49's z-score mean-reversion,
threshold 2.5), combined one-position-at-a-time via round204's own
sequential per-signal-risk resolver -- all three imported directly, not
reimplemented. TOD's entries are, by round19's own explicit design,
UNIFORMLY RANDOM (bar and direction) -- zero entry-timing skill by
construction, all of the trader's real edge on that leg comes from the ATR-
trail exit + time-of-day filter. This makes TOD a real, principled target
for confluence filtering: any genuine directional filter added on top of
pure noise has a fair chance of adding real value, precisely because the
baseline entry carries no information to begin with. VWAP-Z is a real
mean-reversion signal, so the same confluence is read differently there
(see below).

Two confluence filters, tested independently (not AND'd together -- Round
174's own lesson, on a different signal family, was that stacking
confluence conditions buys statistical confidence but collapses trade
frequency so far it stops being useful; kept in mind here, checked
explicitly via trade-count/day before trusting any profit-factor gain):

  1. HTF trend alignment: causal 15-min EMA(50) (round11_fvg_bias's own
     resample_causal, applied fresh here -- not new data, a new lookup on
     data every prior round already uses). Keep a signal only if its
     trade direction agrees with sign(15m close - EMA50) as of the most
     recently closed 15-min bar. Coherent reading for BOTH legs under one
     rule: "don't fight the higher-timeframe trend" -- for TOD (random
     direction) this just keeps the trend-aligned half of pure noise;
     for VWAP-Z (mean reversion) this keeps only the "buy the dip in an
     uptrend / sell the rip in a downtrend" fades, dropping the fully
     counter-trend reversion bets.
  2. Money-flow alignment: same-session cumulative Money Flow Volume
     (Round 170/220's own real, already-tested Chaikin MFM proxy --
     MFM=((close-low)-(high-close))/(high-low), summed with volume from
     the session open) -- keep a signal only if its trade direction
     agrees with that cumulative sign at entry time. A different real
     data dimension from HTF trend (participation-weighted, not price-
     only), tested independently for the same reason Round 220 tested it
     as a standalone idea -- confirmed there to have no edge as an entry
     trigger, but never tested here as a FILTER on an already-validated
     signal, which is a different, real question (does it discriminate
     good the trader setups from bad ones, even though it can't generate good
     entries on its own).

Both filters are causal throughout (only ever look at data available at
or before the signal's own timestamp) and strict-agreement gates (a
signal with an undefined/zero confluence reading, or one on the wrong
side, is dropped, never re-signed).

Reports, for baseline and each filter, on the REAL combined-the trader trade
sequence (same resolver, same $1,680/$1,200 risk, real costs): per-trade
profit factor, this campaign's own established DAILY profit-factor
convention (Round 205's formula, for direct comparability with the
already-published 1.5948 baseline), trade count, active-day count, and
mean $/day -- full history and OOS-only (>= 2025-07-01), so a filter that
only looks good in-sample is caught before being called an improvement.

Not ledger-eligible (a filter/variant tested on an already-validated real
signal/structure, not a new idea test) -- same convention as every Round
206-222 risk-management or filter round on the trader/disciplined_bracket.
"""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd

from round11_fvg_bias import load_1m, resample_causal, POINT_VALUE, TICK_SIZE, COMMISSION_RT
from round19_random_entry import generate_random_entries, build_stop_signals, causal_atr15_lookup, TRAIL_ATR_MULT
from round49_vwap_zscore import compute_session_vwap_z, build_zscore_signals
from round204_multi_account_best_strategies import _resolve_trailing_sequential_per_signal_risk
import round120_goal_judge as J

HERE = os.path.dirname(os.path.abspath(__file__))
TOD_RISK, VWAPZ_RISK = 1680.0, 1200.0
T2, CLOSE_T, SEED, Z_THRESH, EMA_SPAN = dt.time(13, 50), dt.time(16, 0), 0, 2.5, 50


def build_base_signals(mnq_1m, atr15, mnq_z):
    raw = generate_random_entries(mnq_1m, SEED)
    sig_base = build_stop_signals(raw, atr15)
    t = sig_base["ts"].dt.time
    sig_tod = sig_base[(t >= T2) & (t < CLOSE_T)].copy()
    sig_tod["risk"] = TOD_RISK
    sig_tod["leg"] = "TOD"

    sig_z = build_zscore_signals(mnq_z, atr15, Z_THRESH).copy()
    sig_z["risk"] = VWAPZ_RISK
    sig_z["leg"] = "VWAPZ"
    return sig_tod, sig_z


def htf_trend_lookup(mnq_1m, ema_span=EMA_SPAN):
    h15 = resample_causal(mnq_1m, "15min")
    ema = h15["close"].ewm(span=ema_span, adjust=False).mean()
    return np.sign(h15["close"] - ema)


def attach_causal(sig, series):
    """Same causal-lookup shape as round19's attach_atr: the most recently
    available value strictly as of (at-or-before) each signal's own ts."""
    idx = series.index.values
    pos = np.searchsorted(idx, sig["ts"].values, side="right") - 1
    valid = pos >= 0
    out = sig[valid].copy()
    out["confluence"] = series.values[pos[valid]]
    return out.reset_index(drop=True)


def session_money_flow_sign(mnq_1m):
    dates = pd.Series(mnq_1m.index.date, index=mnq_1m.index)
    rng = (mnq_1m["high"] - mnq_1m["low"]).replace(0, np.nan)
    mfm = ((mnq_1m["close"] - mnq_1m["low"]) - (mnq_1m["high"] - mnq_1m["close"])) / rng
    mfv = mfm.fillna(0) * mnq_1m["vol"]
    cum = mfv.groupby(dates).cumsum()
    return np.sign(cum)


def filter_htf_trend(sig, trend_series):
    out = attach_causal(sig, trend_series)
    keep = (out["confluence"] != 0) & (out["direction"] == out["confluence"])
    return out[keep].drop(columns="confluence").reset_index(drop=True)


def filter_money_flow(sig, mf_sign):
    aligned = mf_sign.reindex(sig["ts"]).values
    keep = (~pd.isna(aligned)) & (aligned != 0) & (aligned == sig["direction"].values)
    return sig[keep].reset_index(drop=True)


def daily_profit_factor(trades, all_days):
    daily = trades.groupby(pd.to_datetime(trades["ts"]).dt.normalize())["pnl"].sum()
    daily = daily.reindex(pd.DatetimeIndex(sorted(set(all_days))), fill_value=0.0)
    active = daily[daily != 0]
    wins, losses = active[active > 0], active[active < 0]
    pf = wins.sum() / abs(losses.sum()) if len(losses) and losses.sum() != 0 else float("nan")
    return dict(n_days=len(daily), n_active=len(active), mean_per_day=float(daily.mean()),
                win_rate=float(len(wins) / len(active)) if len(active) else float("nan"),
                profit_factor_daily=float(pf))


def trade_profit_factor(trades):
    if len(trades) == 0:
        return float("nan")
    wins, losses = trades[trades["pnl"] > 0]["pnl"], trades[trades["pnl"] < 0]["pnl"]
    return float(wins.sum() / abs(losses.sum())) if len(losses) and losses.sum() != 0 else float("nan")


def report(label, trades, all_days):
    is_tr = trades[pd.to_datetime(trades["ts"]) < J.OOS_START]
    oos_tr = trades[pd.to_datetime(trades["ts"]) >= J.OOS_START]
    d_full = daily_profit_factor(trades, all_days)
    oos_start_date = J.OOS_START.date()
    d_is = daily_profit_factor(is_tr, [dd for dd in all_days if dd < oos_start_date])
    d_oos = daily_profit_factor(oos_tr, [dd for dd in all_days if dd >= oos_start_date])
    pf_trade_full = trade_profit_factor(trades)
    pf_trade_oos = trade_profit_factor(oos_tr)
    print(f"\n{label}")
    print(f"  FULL : n_trades={len(trades):>5} n_active_days={d_full['n_active']:>4}/{d_full['n_days']} "
          f"mean/day=${d_full['mean_per_day']:+8.2f} win%={d_full['win_rate']:.1%} "
          f"PF_daily={d_full['profit_factor_daily']:.3f} PF_trade={pf_trade_full:.3f}")
    print(f"  IS   : n_trades={len(is_tr):>5} n_active_days={d_is['n_active']:>4}/{d_is['n_days']} "
          f"mean/day=${d_is['mean_per_day']:+8.2f} PF_daily={d_is['profit_factor_daily']:.3f}")
    print(f"  OOS  : n_trades={len(oos_tr):>5} n_active_days={d_oos['n_active']:>4}/{d_oos['n_days']} "
          f"mean/day=${d_oos['mean_per_day']:+8.2f} PF_daily={d_oos['profit_factor_daily']:.3f} "
          f"PF_trade={pf_trade_oos:.3f}", flush=True)
    st_is, st_oos = J.edge_stats(is_tr), J.edge_stats(oos_tr)
    print(f"  bootstrap P(edge>0): IS={st_is['p_pos']:.4f} (n={st_is['n']})  "
          f"OOS={st_oos['p_pos']:.4f} (n={st_oos['n']})", flush=True)
    return dict(label=label, n_trades=len(trades), full=d_full, is_=d_is, oos=d_oos,
                pf_trade_full=pf_trade_full, pf_trade_oos=pf_trade_oos,
                p_pos_is=st_is["p_pos"], p_pos_oos=st_oos["p_pos"])


if __name__ == "__main__":
    mnq_1m = load_1m(os.path.join(HERE, "..", "data", "MNQ_CONTINUOUS.txt"))
    atr15 = causal_atr15_lookup(mnq_1m)
    mnq_z = compute_session_vwap_z(mnq_1m)
    all_days = sorted(set(mnq_1m.index.normalize().date))

    sig_tod, sig_z = build_base_signals(mnq_1m, atr15, mnq_z)
    trend = htf_trend_lookup(mnq_1m)
    mf_sign = session_money_flow_sign(mnq_1m)

    results = {}

    def run(name, tod, z):
        combined = pd.concat([tod, z], ignore_index=True).sort_values("ts").reset_index(drop=True)
        trades = _resolve_trailing_sequential_per_signal_risk(combined, mnq_1m, "MNQ", TRAIL_ATR_MULT)
        results[name] = report(name, trades, all_days)

    print("=== BASELINE (sanity check vs. published Round 205: PF_daily=1.5948, win%=52.7%, "
          "mean/day=$727.96, n_active=934/998) ===")
    run("baseline", sig_tod, sig_z)

    print("\n=== FILTER 1: HTF (15-min EMA50) trend alignment, both legs ===")
    run("htf_trend_both_legs", filter_htf_trend(sig_tod, trend), filter_htf_trend(sig_z, trend))

    print("\n=== FILTER 2: same-session money-flow alignment, both legs ===")
    run("money_flow_both_legs", filter_money_flow(sig_tod, mf_sign), filter_money_flow(sig_z, mf_sign))

    print("\n=== FILTER 1b: HTF trend alignment, TOD leg only (VWAP-Z leg unfiltered) ===")
    run("htf_trend_tod_only", filter_htf_trend(sig_tod, trend), sig_z)

    print("\n=== FILTER 2b: money-flow alignment, TOD leg only (VWAP-Z leg unfiltered) ===")
    run("money_flow_tod_only", filter_money_flow(sig_tod, mf_sign), sig_z)

    with open(os.path.join(HERE, "round223_results.json"), "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"\nSaved round223_results.json ({len(results)} variants).", flush=True)
