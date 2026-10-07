"""Iteration 18 (pre-registered in lab/PREREG.md): daily FX trend on 6 USD pairs, a one-off exception to the no-daily rule, measurement only.   python -m mt5broker.intraday_lab.iter18_fx_daily"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mt5broker.intraday_lab.iter16_fx_xsection import COMM, SGN
from mt5broker.intraday_lab.lab import DATA, FX, PHASES


def load():
    P, S = {}, {}
    for s in FX:
        m = pd.read_parquet(DATA / f"{s}_M1_ticks_full.parquet", columns=["time", "open", "ask_open"])
        idx = pd.to_datetime(m.time.values, unit="s"); mid = (m.open.values + m.ask_open.values) / 2; sp = (m.ask_open.values - m.open.values) / mid
        d = pd.DataFrame({"mid": mid, "sp": sp}, index=idx); d = d[(d.index.hour == 2) & (d.index.minute == 0)]
        d.index = d.index.normalize(); d = d[~d.index.duplicated(keep="first")]; d = d[d.index.dayofweek < 5]
        P[s], S[s] = d.mid, d.sp
    days = pd.bdate_range("2021-09-27", "2026-10-02")
    return pd.DataFrame({s: P[s].reindex(days) for s in FX}), pd.DataFrame({s: S[s].reindex(days) for s in FX})


def run(P, S, mode, Ns):
    sg = np.array([SGN[s] for s in FX]); lp = np.log(P.values) * sg; n = len(P)
    r = np.vstack([np.full((1, 6), np.nan), np.diff(lp, axis=0)])                    # r[t] = return from day t-1 to t
    vol = pd.DataFrame(r).rolling(60, min_periods=40).std().shift(1).values; spv = S.values
    W = np.zeros((n, 6)); pnl = np.full(n, np.nan); contrib = np.zeros((n, 6)); wprev = np.zeros(6)
    for t in range(max(Ns) + 1, n - 1):
        v = vol[t]
        if np.isnan(v).any() or np.isnan(lp[t]).any() or np.isnan(lp[t + 1]).any() or np.isnan(spv[t]).any():
            continue
        sigs = []
        for N in Ns:
            x = lp[t] - lp[t - N]
            if np.isnan(x).any():
                break
            if mode == "TS":
                sigs.append(np.sign(x))
            else:
                o = np.argsort(x); s_ = np.zeros(6); s_[o[-2:]] = 1; s_[o[:2]] = -1; sigs.append(s_)
        else:
            sig = np.mean(sigs, axis=0); w = sig / v; g = np.abs(w).sum()
            if g == 0:
                continue
            w = w / g; ret = w * (lp[t + 1] - lp[t]); cost = np.abs(w - wprev) * (0.5 * spv[t] + COMM)
            pnl[t] = ret.sum() - cost.sum(); contrib[t] = ret - cost; wprev = w
    D = pd.Series(pnl, index=P.index).dropna(); C = pd.DataFrame(contrib, index=P.index, columns=FX).loc[D.index]
    return D, C


def sharpe(x):
    return float(x.mean() / x.std(ddof=1) * np.sqrt(252)) if len(x) > 30 and x.std(ddof=1) > 0 else np.nan


def main():
    P, S = load(); rows = []; hits = []
    cells = [("TS", (N,)) for N in (10, 20, 40, 60, 120)] + [("XS", (N,)) for N in (10, 20, 40, 60, 120)] + [("TS", (20, 60, 120))]
    for mode, Ns in cells:
        D, C = run(P, S, mode, Ns); r = dict(mode=mode, N="+".join(map(str, Ns)), days=len(D))
        for ph, (a, b) in PHASES.items():
            x = D.loc[a:b]; r[f"net_{ph}"] = sharpe(x); r[f"pos_{ph}"] = int((C.loc[a:b].sum() > 0).sum())
        dv = D.loc[PHASES["dev"][0]:PHASES["val"][1]]; r["t_devval"] = float(dv.mean() / (dv.std(ddof=1) / np.sqrt(len(dv)))); cv = C.loc[PHASES["dev"][0]:PHASES["val"][1]].sum(); r["pairs_pos_devval"] = int((cv > 0).sum())
        gross = None; rows.append(r)
        if r["net_dev"] > .5 and r["net_val"] > .5 and r["t_devval"] >= 2.0 and r["pairs_pos_devval"] >= 4:
            hits.append(r)
    T = pd.DataFrame(rows); T.to_csv(r"D:\finance\scratch\lab\iter18_raw.csv", index=False); print(T.round(2).to_string(index=False))
    print(f"\nPRE-REGISTERED HITS (k = {len(T)}): {len(hits)}")
    for h in hits:
        print(h)


if __name__ == "__main__":
    main()
