"""
Round 14, Part 2: short-horizon statistical mean-reversion / momentum on 15-min z-score
extremes. Structurally different from every prior round (1-13), which all tested named
chart-pattern signals (ORB, VWAP-reversion, ICT/SMC concepts). This is pure statistical
extremity and reversion -- a rolling z-score of price vs. its own volatility-normalized
mean, no chart pattern, no session structure.

Both MNQ and MGC (Part 2 is not Nasdaq-restricted, unlike Rounds 12-13).

Causal throughout: SMA/std/ATR at bar i use only bars <= i (bar i's own OHLC is only known
once IT closes, per resample_causal's right-labeled convention used in every prior round);
entries execute on the 1m bar strictly AFTER the signal bar's close (same convention as
resolve_outcomes_plain, reused unchanged from Round 12); the volatility-regime filter's
percentile rank at day D only uses days strictly before D.

(n_lookback, z_threshold, mode) are tested as separate parallel configs -- like HTF choice
in Rounds 11-13 -- not fold-selected, to keep this consistent with existing convention and
avoid a combinatorial per-fold grid explosion. R:R remains the only per-fold train-only
selected parameter, via the reused walk_forward_generic.
"""
import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from round11_fvg_bias import (
    load_1m, resample_causal, POINT_VALUE, TICK_SIZE, COMMISSION_RT, BUFFER, FOLDS,
    one_per_day, fold_stats, tail_concentration,
)
from round12_fvg_confirmation import resolve_outcomes_plain, walk_forward_generic, print_results

ATR_MULT = 1.0          # stop distance = ATR_MULT * ATR(14) on the 15m bar, fixed (not grid-searched)
ATR_PERIOD = 14
N_LOOKBACK_GRID = (20, 40)
Z_THRESHOLD_GRID = (1.5, 2.5)
MIN_SIGNALS = 50


def atr_causal(bar_df, n=ATR_PERIOD):
    high, low, close = bar_df["high"], bar_df["low"], bar_df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def zscore_signals(bar_df, n_lookback, z_threshold, atr_series, atr_mult, mode):
    close = bar_df["close"]
    sma = close.rolling(n_lookback, min_periods=n_lookback).mean()
    std = close.rolling(n_lookback, min_periods=n_lookback).std()
    z = (close - sma) / std
    extreme = z.abs() >= z_threshold
    raw_dir = np.sign(z)
    direction_series = -raw_dir if mode == "reversion" else raw_dir
    valid = extreme & std.notna() & (std > 0) & atr_series.notna() & (atr_series > 0) & (direction_series != 0)
    sub_ts = bar_df.index[valid]
    entries = close.loc[sub_ts].values
    dirs = direction_series.loc[sub_ts].values.astype(int)
    stop_dists = atr_series.loc[sub_ts].values * atr_mult
    stops = np.where(dirs == 1, entries - stop_dists, entries + stop_dists)
    return pd.DataFrame({"ts": sub_ts, "direction": dirs, "entry": entries, "stop": stops})


def daily_vol_regime(df1m, lookback_days=20, hist_days=200):
    daily_close = df1m["close"].resample("1D").last().dropna()
    ret = np.log(daily_close).diff()
    vol = ret.rolling(lookback_days, min_periods=lookback_days).std()
    pct_rank = vol.rolling(hist_days, min_periods=hist_days).apply(lambda w: (w <= w.iloc[-1]).mean(), raw=False)
    return pct_rank.dropna()


def attach_vol_regime(signals, vol_pct):
    if len(signals) == 0 or len(vol_pct) == 0:
        out = signals.copy()
        out["vol_pct"] = np.nan
        return out
    dates = pd.to_datetime(signals["ts"]).dt.normalize().values
    vp_ts = vol_pct.index.values
    pos = np.searchsorted(vp_ts, dates, side="right") - 1
    pos = np.clip(pos, 0, len(vol_pct) - 1)
    out = signals.copy()
    out["vol_pct"] = vol_pct.values[pos]
    out.loc[np.searchsorted(vp_ts, dates, side="right") - 1 < 0, "vol_pct"] = np.nan
    return out


def summarize_aggregate(sig, df1m, symbol, label):
    """Quick single-pass (no fold split) aggregate check used only to decide whether a
    config is even worth a full walk-forward run -- NOT reported as a result on its own."""
    if len(sig) < MIN_SIGNALS:
        print(f"  [{label}] n={len(sig)} < {MIN_SIGNALS}, skipped (insufficient for any read)", flush=True)
        return None
    tr = resolve_outcomes_plain(sig, df1m, symbol, rr=1.5, risk_dollar=400)
    exp = tr["pnl"].mean() if len(tr) else float("nan")
    print(f"  [{label}] n={len(sig)} quick-screen(rr=1.5,$400) exp=${exp:.2f}", flush=True)
    return exp


if __name__ == "__main__":
    for symbol, path in [("MNQ", "../data/MNQ_CONTINUOUS.txt"), ("MGC", "../data/MGC_CONTINUOUS.txt")]:
        print(f"\n\n################ {symbol} ################", flush=True)
        df1m = load_1m(path)
        print(f"{symbol}: {len(df1m)} 1m bars, {df1m.index.min()} -> {df1m.index.max()}", flush=True)
        bar15 = resample_causal(df1m, "15min")
        atr15 = atr_causal(bar15)
        vol_pct = daily_vol_regime(df1m)
        print(f"{symbol}: {len(bar15)} 15m bars; vol-regime series {len(vol_pct)} days "
              f"({vol_pct.index.min() if len(vol_pct) else None} -> {vol_pct.index.max() if len(vol_pct) else None})",
              flush=True)

        screen = {}
        for n_lb in N_LOOKBACK_GRID:
            for z_thr in Z_THRESHOLD_GRID:
                for mode in ("reversion", "momentum"):
                    sig = one_per_day(zscore_signals(bar15, n_lb, z_thr, atr15, ATR_MULT, mode))
                    label = f"{symbol} n={n_lb} z={z_thr} mode={mode}"
                    exp = summarize_aggregate(sig, df1m, symbol, label)
                    screen[(n_lb, z_thr, mode)] = (sig, exp)

        print(f"\n---- {symbol}: full walk-forward on every screened config (n_lookback x z_threshold x mode) ----",
              flush=True)
        best_key, best_exp = None, -1e18
        for (n_lb, z_thr, mode), (sig, exp) in screen.items():
            if len(sig) < MIN_SIGNALS:
                continue
            label = f"{symbol} n_lookback={n_lb} z_thr={z_thr} mode={mode}"
            res = walk_forward_generic(sig, df1m, symbol, resolve_outcomes_plain, {})
            print_results(label, res)
            if exp is not None and exp > best_exp:
                best_exp, best_key = exp, (n_lb, z_thr, mode)

        if best_key is not None:
            n_lb, z_thr, mode = best_key
            print(f"\n---- {symbol}: vol-regime filter (mid-tercile, 33rd-67th pct) applied to best screened "
                  f"config n_lookback={n_lb} z_thr={z_thr} mode={mode} ----", flush=True)
            base_sig, _ = screen[best_key]
            sig_vf = attach_vol_regime(base_sig, vol_pct)
            sig_vf = sig_vf[(sig_vf["vol_pct"] >= 0.33) & (sig_vf["vol_pct"] <= 0.67)].drop(columns="vol_pct")
            print(f"  vol-filtered signal count: {len(sig_vf)} (from {len(base_sig)} unfiltered)", flush=True)
            if len(sig_vf) >= MIN_SIGNALS:
                res_vf = walk_forward_generic(sig_vf, df1m, symbol, resolve_outcomes_plain, {})
                print_results(f"{symbol} VOL-FILTERED n_lookback={n_lb} z_thr={z_thr} mode={mode}", res_vf)
            else:
                print(f"  SKIPPED: {len(sig_vf)} < {MIN_SIGNALS}, insufficient for a 6-fold walk-forward read",
                      flush=True)
        else:
            print(f"\n{symbol}: no config reached the minimum signal count for any read.", flush=True)

    print("\n\n################ Round 14 Part 2 complete ################", flush=True)
