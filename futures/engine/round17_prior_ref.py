"""
Round 17: Prior-day / prior-week reference-level signals -- MNQ + MGC.

None of the 86 variants tested through Round 16 used a prior-period reference level
(yesterday's high/low, this week's open) as the basis for a signal. Round 16's
meta-analysis found no genuine fat-tailed/rare-event structure in the raw daily data,
so this round is tested with full skepticism, not an expectation of a different outcome
just because the signal family is new.

Three sub-tests, all same-day-flatten-compliant (no overnight holds):

  1. Sweep-and-reverse: price wicks beyond yesterday's high/low, then this bar's CLOSE
     comes back inside -> fade entry in the reversal direction. Stop = the day's most
     extreme high/low reached so far (the actual sweep extreme), causal (only uses bars
     up to and including the signal bar).
  2. Breakout-and-continue: first CLOSE beyond yesterday's high/low (no sweep-back
     required) -> trade in the breakout direction. Stop = the OPPOSITE prior-day level
     (a wide, structural stop by construction -- flagged honestly in the results, since
     this can produce large stop distances / low-contract-count sizing).
  3. Weekly-open bias filter applied to Round 12's already-built confirmation-candle FVG
     entry (imported directly, not reimplemented): only take a Round-12 signal if its
     direction agrees with price's position relative to this week's opening price. Tests
     whether a same-day-flatten-compliant weekly bias improves an entry mechanism this
     repo has already partially characterized, rather than introducing two unknowns.

Built causally throughout:
  - prior_high/prior_low for a given calendar day = the FULL previous session's high/low,
    only attached to bars on/after the day boundary (the previous session is fully closed
    by then).
  - sweep state and day-extreme tracking only use bars up to and including the bar being
    evaluated.
  - week_open is set once, at the first bar of each ISO week, and only applies to bars at
    or after that first bar.

Walk-forward, costs, sizing, folds: identical to every prior round (see round11_fvg_bias.py
FOLDS / POINT_VALUE / TICK_SIZE / COMMISSION_RT / BUFFER -- reused directly, not redefined).
"""
import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from round11_fvg_bias import (
    load_1m, resample_causal, detect_fvgs, POINT_VALUE, TICK_SIZE,
    COMMISSION_RT, BUFFER, FOLDS, one_per_day, fold_stats, tail_concentration,
)
from round12_fvg_confirmation import confirmed_entries, resolve_outcomes_plain, walk_forward_generic, print_results


def prior_day_levels(df1m):
    daily = df1m.groupby(df1m.index.date).agg(high=("high", "max"), low=("low", "min"))
    daily.index = pd.to_datetime(daily.index)
    daily = daily.sort_index()
    prior = daily.shift(1)
    prior.columns = ["prior_high", "prior_low"]
    return prior


def attach_prior_levels(df1m, prior):
    dates = pd.to_datetime(df1m.index.date)
    pr = prior.reindex(dates)
    df = df1m.copy()
    df["prior_high"] = pr["prior_high"].values
    df["prior_low"] = pr["prior_low"].values
    return df


def sweep_reverse_signals(df1m_pl):
    h = df1m_pl["high"].values
    l = df1m_pl["low"].values
    c = df1m_pl["close"].values
    ph = df1m_pl["prior_high"].values
    pl_ = df1m_pl["prior_low"].values
    ts = df1m_pl.index.values
    dates = pd.to_datetime(df1m_pl.index.date).values
    n = len(df1m_pl)
    rows = []
    cur_date = None
    swept_high = swept_low = done_high = done_low = False
    day_max_h = -np.inf
    day_min_l = np.inf
    for i in range(n):
        if dates[i] != cur_date:
            cur_date = dates[i]
            swept_high = swept_low = done_high = done_low = False
            day_max_h = -np.inf
            day_min_l = np.inf
        if np.isnan(ph[i]):
            continue
        day_max_h = max(day_max_h, h[i])
        day_min_l = min(day_min_l, l[i])
        if h[i] > ph[i]:
            swept_high = True
        if l[i] < pl_[i]:
            swept_low = True
        if swept_high and not done_high and c[i] <= ph[i]:
            rows.append((ts[i], -1, c[i], day_max_h))
            done_high = True
        if swept_low and not done_low and c[i] >= pl_[i]:
            rows.append((ts[i], 1, c[i], day_min_l))
            done_low = True
    return pd.DataFrame(rows, columns=["ts", "direction", "entry", "stop"])


def breakout_continue_signals(df1m_pl):
    h = df1m_pl["high"].values
    l = df1m_pl["low"].values
    c = df1m_pl["close"].values
    ph = df1m_pl["prior_high"].values
    pl_ = df1m_pl["prior_low"].values
    ts = df1m_pl.index.values
    dates = pd.to_datetime(df1m_pl.index.date).values
    n = len(df1m_pl)
    rows = []
    cur_date = None
    done_up = done_dn = False
    for i in range(n):
        if dates[i] != cur_date:
            cur_date = dates[i]
            done_up = done_dn = False
        if np.isnan(ph[i]):
            continue
        if not done_up and c[i] > ph[i]:
            rows.append((ts[i], 1, c[i], pl_[i]))
            done_up = True
        if not done_dn and c[i] < pl_[i]:
            rows.append((ts[i], -1, c[i], ph[i]))
            done_dn = True
    return pd.DataFrame(rows, columns=["ts", "direction", "entry", "stop"])


def weekly_open_series(df1m):
    iso = df1m.index.isocalendar()
    week_key = (iso["year"].astype(str) + "-W" + iso["week"].astype(str)).values
    o = df1m["open"].values
    n = len(df1m)
    week_open = np.empty(n)
    cur_key = None
    cur_open = np.nan
    for i in range(n):
        if week_key[i] != cur_key:
            cur_key = week_key[i]
            cur_open = o[i]
        week_open[i] = cur_open
    return pd.Series(week_open, index=df1m.index)


def apply_weekly_bias_filter(sig_df, df1m, week_open):
    if len(sig_df) == 0:
        return sig_df
    ts = df1m.index.values
    close = df1m["close"].values
    wopen = week_open.values
    pos = np.searchsorted(ts, sig_df["ts"].values, side="right") - 1
    pos = np.clip(pos, 0, len(df1m) - 1)
    bias = np.sign(close[pos] - wopen[pos])
    sig = sig_df.copy()
    sig["bias"] = bias
    out = sig[sig["direction"] == sig["bias"]].drop(columns="bias").reset_index(drop=True)
    return out


def run_all(symbol, path):
    print(f"\n{'='*70}\n{symbol}\n{'='*70}", flush=True)
    df1m = load_1m(path)
    print(f"{symbol}: {len(df1m)} 1m bars, {df1m.index.min()} -> {df1m.index.max()}", flush=True)

    prior = prior_day_levels(df1m)
    df1m_pl = attach_prior_levels(df1m, prior)

    print(f"\n--- {symbol} SUB-TEST 1: sweep-and-reverse ---", flush=True)
    sig1 = sweep_reverse_signals(df1m_pl)
    sig1 = one_per_day(sig1)
    print(f"signals after 1/day cap: {len(sig1)}", flush=True)
    res1 = walk_forward_generic(sig1, df1m, symbol, resolve_outcomes_plain, {})
    print_results(f"{symbol} sweep-reverse", res1)

    print(f"\n--- {symbol} SUB-TEST 2: breakout-and-continue ---", flush=True)
    sig2 = breakout_continue_signals(df1m_pl)
    sig2 = one_per_day(sig2)
    print(f"signals after 1/day cap: {len(sig2)}", flush=True)
    res2 = walk_forward_generic(sig2, df1m, symbol, resolve_outcomes_plain, {})
    print_results(f"{symbol} breakout-continue", res2)

    print(f"\n--- {symbol} SUB-TEST 3: weekly-open bias x Round-12 confirmation FVG ---", flush=True)
    week_open = weekly_open_series(df1m)
    for htf_rule, htf_name in [("15min", "15m"), ("30min", "30m")]:
        htf = resample_causal(df1m, htf_rule)
        fvgs = detect_fvgs(htf)
        sig_b = confirmed_entries(fvgs, df1m)
        sig_b_biased = apply_weekly_bias_filter(sig_b, df1m, week_open)
        sig_b_biased = one_per_day(sig_b_biased)
        print(f"HTF={htf_name}: unfiltered confirmation signals={len(sig_b)}, "
              f"weekly-bias-filtered (1/day)={len(sig_b_biased)}", flush=True)
        res3 = walk_forward_generic(sig_b_biased, df1m, symbol, resolve_outcomes_plain, {})
        print_results(f"{symbol} weekly-bias-filtered confirmation HTF={htf_name}", res3)


if __name__ == "__main__":
    run_all("MNQ", "../data/MNQ_CONTINUOUS.txt")
    run_all("MGC", "../data/MGC_CONTINUOUS.txt")
