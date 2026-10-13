"""Iteration 7 (pre-registered in lab/PREREG.md): does a gold trendiness filter known at the start of the day separate the pair's flat years from its good years?   python -m forex.intraday_lab.iter7_regime"""
from __future__ import annotations

import numpy as np
import pandas as pd

from forex.ea_batch import floating
from forex.intraday_lab.lab import PHASES, Bars
from forex.intraday_lab.scan6 import thin

PH_YEARS = {"dev": (2021, 2023), "val": (2024, 2024), "hold": (2025, 2026)}


def phase_of(ts):
    y = pd.DatetimeIndex(pd.to_datetime(np.asarray(ts), unit="s")).year.values
    return np.where(y <= 2023, "dev", np.where(y == 2024, "val", "hold"))


def regimes():
    m = pd.read_parquet("forex/data/XAUUSD_M1_ticks_full.parquet")
    d = pd.Series(((m.close + m.ask_close) / 2).values, index=pd.to_datetime(m.time, unit="s")).resample("1D").last().dropna()
    dc = d.diff(); r1 = (d - d.shift(20)).abs() / dc.abs().rolling(20).sum()
    r2 = ((d - d.shift(60)) / (dc.rolling(60).std() * np.sqrt(60)))
    v1 = dc.rolling(120).var(); d5 = (d - d.shift(5)); v5 = d5.rolling(120).var()
    r3 = v5 / (5 * v1)
    R = pd.DataFrame({"R1_er20": r1, "R2_trend60": r2.abs(), "R3_vr5": r3}).shift(1)        # known at the START of the day
    return R


def split(t, v, R, thr):
    day = pd.to_datetime(t, unit="s").normalize(); x = R.reindex(day).values
    return x


def stat(a, b):
    if len(a) < 5 or len(b) < 5:
        return np.nan, np.nan, np.nan
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b)); return a.mean(), b.mean(), (a.mean() - b.mean()) / se


def main():
    R = regimes(); dev_days = R[(R.index >= "2021-10-01") & (R.index <= "2023-12-31")]
    thr = dev_days.median(); print("DEV medians (frozen thresholds):", thr.round(3).to_dict(), "\n")
    # (a) the pair's actual trades
    rows = []
    for ea in ("mkt_xau5min", "77900"):
        for y in (2022, 2023, 2024, 2025, 2026):
            d = pd.read_csv(f"forex/ea_batch/results_{y}/{ea}.csv")
            p, _ = floating.pair_positions(d, floating.prior_k("XAUUSD", pd.Timestamp(f"{y}-01-01"), pd.Timestamp(f"{y}-12-31")))
            te = (pd.to_datetime(p.te).astype("int64") // 10**9).values
            # normalise profit per EA to R units: profit / std of the EA's profits in DEV (so two EAs pool)
            rows.append(pd.DataFrame(dict(ea=ea, year=y, t=te, pnl=p.profit.values)))
    T = pd.concat(rows); sd = T[T.year <= 2023].groupby("ea").pnl.std(); T["z"] = T.pnl / T.ea.map(sd)
    T["phase"] = phase_of(T.t)
    print("=== (a) the pair's trades: mean z-scored P&L per trade, filter ON vs OFF (pooled over both EAs) ===")
    out = []
    for name in R.columns:
        x = R.reindex(pd.to_datetime(T.t, unit="s").dt.normalize()).values[:, list(R.columns).index(name)]
        on = x >= thr[name]
        for ph in ("dev", "val", "hold"):
            s = (T.phase == ph).values
            m_on, m_off, tt = stat(T.z[s & on].values, T.z[s & ~on].values)
            out.append(dict(measure=name, phase=ph, n_on=int((s & on).sum()), n_off=int((s & ~on).sum()), mean_on=m_on, mean_off=m_off, t_diff=tt))
    A = pd.DataFrame(out); print(A.round(3).to_string(index=False))
    # by-year totals for the best measure of each
    print("\nTotal z-scored P&L by year, ON vs OFF (R3_vr5 and R1_er20):")
    for name in ("R1_er20", "R3_vr5", "R2_trend60"):
        x = R.reindex(pd.to_datetime(T.t, unit="s").dt.normalize()).values[:, list(R.columns).index(name)]; T["on"] = x >= thr[name]
        print(name, T.groupby(["year", "on"]).z.sum().unstack().round(1).to_dict("index"))
    # (b) generic trend-only rule on gold, 5-minute, ret96 >= 5 ATR, h = 288, signed forward return
    b = Bars("XAUUSD", 5); atr = b.atr(14); s = pd.Series(b.mid)
    r96 = ((s - s.shift(96)) / pd.Series(atr)).values; r48 = ((s - s.shift(48)) / pd.Series(atr)).values
    hh = pd.Series(b.bh).rolling(96).max(); ll = pd.Series(b.bl).rolling(96).min(); pos = ((s - ll) / (hh - ll)).values
    sign = np.where((r96 >= 5) & (r48 > 0) & (pos > 0.5), 1.0, np.where((r96 <= -5) & (r48 < 0) & (pos < 0.5), -1.0, 0.0)); h = 288
    fwd = np.full(b.n, np.nan); ok = np.arange(b.n - h); fwd[ok] = (b.mid[ok + h] - b.mid[ok]) / atr[ok]
    ix = thin(np.flatnonzero((sign != 0) & np.isfinite(fwd)), h); sg = sign[ix] * fwd[ix]; tt = b.t[ix]; ph = phase_of(tt)
    print("\n=== (b) generic trend-only rule on gold (5m, ret96>=5 ATR, 24-hour hold): signed forward return (ATR), ON vs OFF ===")
    out = []
    for name in R.columns:
        x = R.reindex(pd.to_datetime(tt, unit="s").normalize()).values[:, list(R.columns).index(name)]; on = x >= thr[name]
        for p in ("dev", "val", "hold"):
            m = (ph == p)
            m_on, m_off, t_ = stat(sg[m & on], sg[m & ~on]); out.append(dict(measure=name, phase=p, n_on=int((m & on).sum()), n_off=int((m & ~on).sum()), mean_on=m_on, mean_off=m_off, t_diff=t_))
    B = pd.DataFrame(out); print(B.round(3).to_string(index=False))
    for nm, X in (("a_pair_trades", A), ("b_generic_rule", B)):
        piv = X.pivot_table(index="measure", columns="phase", values=["t_diff", "mean_on", "mean_off"])
        hit = [m for m in piv.index if piv.loc[m, ("t_diff", "val")] >= 2 and piv.loc[m, ("t_diff", "hold")] >= 2 and piv.loc[m, ("mean_on", "dev")] >= 0]
        print(f"\nPRE-REGISTERED HIT for {nm}:", hit or "none")


if __name__ == "__main__":
    main()
