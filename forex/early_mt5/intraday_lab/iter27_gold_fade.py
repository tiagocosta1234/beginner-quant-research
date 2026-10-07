"""Iteration 27 (pre-registered in lab/PREREG.md): the frozen weekly-extreme fade on gold alone, swap charged.   python -m mt5broker.intraday_lab.iter27_gold_fade"""
from __future__ import annotations

from itertools import product

import numpy as np
import pandas as pd

from mt5broker.intraday_lab.iter23_cross_swap_rules import nights
from mt5broker.intraday_lab.lab import DATA, commission_price

SWAP_USD = {1: -75.0, -1: -4.0}


def load():
    m = pd.read_parquet(DATA / "XAUUSD_M1_ticks_full.parquet", columns=["time", "open", "ask_open"]); mid = (m.open.values + m.ask_open.values) / 2; sp = (m.ask_open.values - m.open.values) / mid
    d = pd.DataFrame({"mid": mid, "sp": sp}, index=pd.to_datetime(m.time.values, unit="s")); grid = pd.date_range("2021-10-01", "2026-10-02", freq="h")
    h0 = d[d.index.minute == 0]; h55 = d[d.index.minute == 55].copy(); h55.index = h55.index + pd.Timedelta(minutes=5)
    f = lambda x: x[~x.index.duplicated()].reindex(grid)
    return f(h55.mid), f(h0.mid), f(h0.sp)


def sharpe(x):
    return float(x.mean() / x.std(ddof=1) * np.sqrt(252)) if len(x) > 40 and x.std(ddof=1) > 0 else np.nan


def main():
    p55, p00, sp = load(); idx = p00.index; l55 = np.log(p55.values); l00 = np.log(p00.values); spv = sp.values; n = len(idx); price = float(np.nanmedian(p00.values)); notional = 100 * price
    comm_bp = commission_price("XAUUSD", price) / price; days = pd.bdate_range("2021-10-01", "2026-10-02"); rows = []
    sw_bp = {s: v / notional * 1e4 for s, v in SWAP_USD.items()}
    for W, th, H in product((120, 168, 240), (2.5, 3.0, 3.5), (36, 48, 72)):
        x = pd.Series(l55); z = ((x - x.rolling(W, min_periods=W // 2).mean()) / x.rolling(W, min_periods=W // 2).std()).values; out = []; t = W + 1
        while t < n - H:
            if np.isnan(z[t]) or np.isnan(l00[t]) or np.isnan(l00[t + H]) or np.isnan(spv[t]) or np.isnan(spv[t + H]) or abs(z[t]) < th:
                t += 1; continue
            pos = -int(np.sign(z[t])); gross = pos * (l00[t + H] - l00[t]); cost = 0.5 * (spv[t] + spv[t + H]) + comm_bp; sw = nights(idx[t], idx[t + H]) * sw_bp[pos] * 1e-4
            out.append((idx[t + H].normalize(), gross - cost + sw, gross, cost, sw)); t += H
        df = pd.DataFrame(out, columns=["d", "net", "gross", "cost", "sw"]); day = df.groupby("d").net.sum().reindex(days).fillna(0.0)
        rows.append(dict(W=W, theta=th, H=H, trades=len(df), gross_bp=df.gross.mean() * 1e4, cost_bp=df.cost.mean() * 1e4, swap_bp=df.sw.mean() * 1e4, dev=sharpe(day.loc["2021-10-01":"2023-12-31"]), val=sharpe(day.loc["2024-01-01":"2024-12-31"]), hold=sharpe(day.loc["2025-01-01":"2026-10-02"])))
    T = pd.DataFrame(rows); T.to_csv(r"D:\finance\scratch\lab\iter27_raw.csv", index=False); print(T[["W", "theta", "H", "trades", "gross_bp", "cost_bp", "swap_bp", "dev", "val"]].round(2).to_string(index=False))
    c = T[(T.W == 168) & (T.theta == 3.0) & (T.H == 48)].iloc[0]; hit = bool((T.dev > 0).mean() >= .7 and (T.val > 0).mean() >= .7 and c.dev >= .5 and c.val >= .5)
    print(f"\nshare positive: DEV {(T.dev > 0).mean():.0%}, VAL {(T.val > 0).mean():.0%}; centre DEV {c.dev:.2f} VAL {c.val:.2f}; PLATEAU HIT: {hit}")
    if hit:
        print("HOLD (printed because the plateau holds):", T.hold.round(2).tolist())


if __name__ == "__main__":
    main()
