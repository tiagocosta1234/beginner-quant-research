"""Iteration 16 (pre-registered in lab/PREREG.md): cross-sectional FX portfolio on 6 USD pairs, judged on net portfolio Sharpe.   python -m forex.intraday_lab.iter16_fx_xsection"""
from __future__ import annotations

from itertools import product

import numpy as np
import pandas as pd

from forex.intraday_lab.lab import DATA, FX, PHASES

SGN = {"EURUSD": 1, "GBPUSD": 1, "AUDUSD": 1, "USDJPY": -1, "USDCAD": -1, "USDCHF": -1}
COMM = 0.3e-4                                           # 0.3 bp a side (USD 6 a 100K lot round turn)


def load():
    px55, px00, spr = {}, {}, {}
    for s in FX:
        m = pd.read_parquet(DATA / f"{s}_M1_ticks_full.parquet", columns=["time", "open", "ask_open"])
        mid = (m.open.values + m.ask_open.values) / 2; sp = (m.ask_open.values - m.open.values) / mid
        idx = pd.to_datetime(m.time.values, unit="s"); d = pd.DataFrame({"mid": mid, "sp": sp}, index=idx)
        h0 = d[d.index.minute == 0]; h55 = d[d.index.minute == 55]
        px00[s] = h0.mid; spr[s] = h0.sp
        h55 = h55.copy(); h55.index = h55.index + pd.Timedelta(minutes=5); px55[s] = h55.mid   # price known 5 minutes before the hour, stamped on the hour
    grid = pd.date_range("2021-10-01", "2026-10-02", freq="h")
    f = lambda D: pd.DataFrame({s: D[s].reindex(grid) for s in FX})
    return f(px55), f(px00), f(spr)


def run(P55, P00, SP, L, H, mode):
    sg = np.array([SGN[s] for s in FX]); lp55 = np.log(P55.values) * sg; lp00 = np.log(P00.values) * sg
    n = len(P00); sig = lp55 - np.roll(lp55, L, axis=0); sig[:L] = np.nan
    hr = pd.DataFrame(lp00 - np.roll(lp00, 1, axis=0)); vol = hr.rolling(480, min_periods=240).std().shift(1).values
    spread_med = np.nanmedian(SP.values, axis=0); spv = SP.values
    W = np.zeros((n, 6)); pnl = np.full(n, np.nan); gross = np.full(n, np.nan); contrib = np.zeros((n, 6)); wprev = np.zeros(6)
    idx = P00.index; hrs = np.arange(n)
    for t in range(L + 1, n - H):
        if (t - 2) % H != 0:
            continue
        s = sig[t]; v = vol[t]; ent = lp00[t]; ex = lp00[t + H]
        if np.isnan(s).any() or np.isnan(v).any() or np.isnan(ent).any() or np.isnan(ex).any() or (spv[t] > 3 * spread_med).any():
            continue
        order = np.argsort(s); w = np.zeros(6); top, bot = order[-2:], order[:2]
        w[top] = 1 / v[top]; w[bot] = -1 / v[bot]
        w = w / np.abs(w).sum()
        if mode == "REV":
            w = -w
        ret = w * (ex - ent); cost = np.abs(w - wprev) * (0.5 * spv[t] + COMM)
        pnl[t] = ret.sum() - cost.sum(); gross[t] = ret.sum(); contrib[t] = ret - cost; wprev = w
    D = pd.DataFrame({"net": pnl, "gross": gross}, index=idx).dropna(); C = pd.DataFrame(contrib, index=idx, columns=FX).loc[D.index]
    return D, C


def sharpe(x):
    return float(x.mean() / x.std(ddof=1) * np.sqrt(252)) if len(x) > 20 and x.std(ddof=1) > 0 else np.nan


def main():
    P55, P00, SP = load(); rows = []; hits = []
    for L, H, mode in product((1, 4, 12, 24), (1, 4, 12), ("MOM", "REV")):
        D, C = run(P55, P00, SP, L, H, mode); day = D.groupby(D.index.date).sum(); day.index = pd.DatetimeIndex(day.index); cday = C.groupby(C.index.date).sum(); cday.index = pd.DatetimeIndex(cday.index)
        r = dict(L=L, H=H, mode=mode, trades=len(D))
        for ph, (a, b) in PHASES.items():
            x = day.loc[a:b]; r[f"net_{ph}"] = sharpe(x.net); r[f"gross_{ph}"] = sharpe(x.gross); r[f"pos_{ph}"] = int((cday.loc[a:b].sum() > 0).sum())
        dv = day.loc[PHASES["dev"][0]:PHASES["val"][1]].net; r["t_devval"] = float(dv.mean() / (dv.std(ddof=1) / np.sqrt(len(dv)))) if len(dv) > 20 else np.nan
        rows.append(r)
        if r["net_dev"] > 0.5 and r["net_val"] > 0.5 and r["t_devval"] >= 3.0 and r["pos_dev"] >= 4 and r["pos_val"] >= 4:
            hits.append(r)
    T = pd.DataFrame(rows); T.to_csv(r"data\scratch\lab\iter16_raw.csv", index=False)
    print(T.round(2).to_string(index=False))
    print(f"\nPRE-REGISTERED HITS (k = {len(T)}): {len(hits)}")
    for h in hits:
        print(h)
    print(f"share of cells with net Sharpe > 0: DEV {(T.net_dev > 0).mean():.0%}, VAL {(T.net_val > 0).mean():.0%}; best DEV {T.net_dev.max():.2f}, best VAL {T.net_val.max():.2f}; mean gross DEV {T.gross_dev.mean():.2f}, mean net DEV {T.net_dev.mean():.2f}")


if __name__ == "__main__":
    main()
