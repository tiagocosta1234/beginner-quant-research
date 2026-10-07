"""Iteration 25 (pre-registered in lab/PREREG.md): the frozen cross-fade grid on index relative value (7 indices, 21 combinations).   python -m mt5broker.intraday_lab.iter25_index_cross"""
from __future__ import annotations

from itertools import combinations, product

import numpy as np
import pandas as pd

from mt5broker.intraday_lab.lab import DATA

IDX = ("US100.cash", "US30.cash", "US500.cash", "US2000.cash", "GER40.cash", "UK100.cash", "FRA40.cash")


def load():
    px55, px00, spr = {}, {}, {}
    for s in IDX:
        m = pd.read_parquet(DATA / f"{s}_M1_ticks_full.parquet", columns=["time", "open", "ask_open"])
        mid = (m.open.values + m.ask_open.values) / 2; sp = (m.ask_open.values - m.open.values) / mid
        d = pd.DataFrame({"mid": mid, "sp": sp}, index=pd.to_datetime(m.time.values, unit="s"))
        h0 = d[(d.index.minute == 0)]; h55 = d[(d.index.minute == 55)].copy(); h55.index = h55.index + pd.Timedelta(minutes=5)
        px00[s] = h0.mid; spr[s] = h0.sp; px55[s] = h55.mid
    grid = pd.date_range("2021-10-01", "2026-10-02", freq="h")
    f = lambda D: pd.DataFrame({s: D[s][~D[s].index.duplicated()].reindex(grid) for s in IDX})
    return f(px55), f(px00), f(spr)


def trades(l55, l00, spv, idx, W, th, H):
    n = len(idx); out = []
    for (i, j) in combinations(range(len(IDX)), 2):
        x55 = pd.Series(l55[:, i] - l55[:, j]); mu = x55.rolling(W, min_periods=W // 2).mean(); sd = x55.rolling(W, min_periods=W // 2).std(); z = ((x55 - mu) / sd).values; x00 = l00[:, i] - l00[:, j]
        t = W + 1
        while t < n - H:
            if np.isnan(z[t]) or np.isnan(x00[t]) or np.isnan(x00[t + H]) or np.isnan(spv[[t, t + H]][:, [i, j]]).any() or abs(z[t]) < th:
                t += 1; continue
            pos = -np.sign(z[t]); gross = pos * (x00[t + H] - x00[t]); cost = 0.5 * (spv[t, i] + spv[t, j] + spv[t + H, i] + spv[t + H, j])
            out.append((idx[t + H].normalize(), gross - cost, gross, cost)); t += H
    return out


def sharpe(x):
    return float(x.mean() / x.std(ddof=1) * np.sqrt(252)) if len(x) > 40 and x.std(ddof=1) > 0 else np.nan


def main():
    P55, P00, SP = load(); l55 = np.log(P55.values); l00 = np.log(P00.values); spv = SP.values; idx = P00.index; days = pd.bdate_range("2021-10-01", "2026-10-02"); rows = []
    for W, th, H in product((120, 168, 240), (2.5, 3.0, 3.5), (36, 48, 72)):
        df = pd.DataFrame(trades(l55, l00, spv, idx, W, th, H), columns=["d", "net", "gross", "cost"])
        if not len(df):
            rows.append(dict(W=W, theta=th, H=H, trades=0)); continue
        day = df.groupby("d").net.sum().reindex(days).fillna(0.0)
        rows.append(dict(W=W, theta=th, H=H, trades=len(df), gross_bp=df.gross.mean() * 1e4, cost_bp=df.cost.mean() * 1e4, dev=sharpe(day.loc["2021-10-01":"2023-12-31"]), val=sharpe(day.loc["2024-01-01":"2024-12-31"]), hold=sharpe(day.loc["2025-01-01":"2026-10-02"])))
        print(rows[-1], flush=True)
    T = pd.DataFrame(rows); T.to_csv(r"D:\finance\scratch\lab\iter25_raw.csv", index=False)
    c = T[(T.W == 168) & (T.theta == 3.0) & (T.H == 48)].iloc[0]; hit = bool((T.dev > 0).mean() >= .7 and (T.val > 0).mean() >= .7 and c.dev >= .5 and c.val >= .5)
    print(T[["W", "theta", "H", "trades", "gross_bp", "cost_bp", "dev", "val"]].round(2).to_string(index=False))
    print(f"\nshare positive: DEV {(T.dev > 0).mean():.0%}, VAL {(T.val > 0).mean():.0%}; centre DEV {c.dev:.2f} VAL {c.val:.2f}; PLATEAU HIT: {hit}")
    if hit:
        print("HOLD (printed because the plateau holds):", T.hold.round(2).tolist())


if __name__ == "__main__":
    main()
