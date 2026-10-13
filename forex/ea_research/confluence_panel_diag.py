"""Exploratory diagnostics for family K (confluence panel) -- NOT trials, cannot accept anything (written after the six registered trials had closed).
   python -m forex.ea_research.confluence_panel_diag
Question: is any of the predictive content timing (within a market, over time) or cross-sectional skill, or is it all drift (the long bias of 2023-25)?"""
from __future__ import annotations

import numpy as np
import pandas as pd

from forex.ea_research import confluence_panel as K


def cluster_slope(x: np.ndarray, y: np.ndarray, date_codes: np.ndarray) -> tuple[float, float]:
    """OLS slope of y on x (both demeaned) with standard errors clustered by date."""
    x = x - x.mean(); y = y - y.mean(); sxx = (x * x).sum(); b = (x * y).sum() / sxx; e = y - b * x
    g = pd.Series(x * e).groupby(date_codes).sum().to_numpy(); se = np.sqrt((g ** 2).sum()) / sxx; return float(b), float(b / se)


def main():
    P, _ = K.build_panel(); ok = P[K.CORE].notna().all(axis=1) & P.nr.notna(); B = P[ok].copy(); B["dc"] = pd.factorize(B.date)[0]
    X = K.c1_components(B); B["score"] = X.score
    print("== D1: C1 slope of y on the score, market-demeaned y (removes each market's own drift in the period), date-clustered t ==")
    for per in ("PRE", "DEV", "VAL", "POOL"):
        a, b = K.PERIODS[per]; m = ((B.date >= a) & (B.date <= b)).to_numpy(); d = B[m]; out = []
        for h in (1, 5):
            y = d[f"y{h}"].clip(-4, 4); y = y - y.groupby(d.mkt).transform("mean"); keep = y.notna().to_numpy()
            s1, t1 = cluster_slope(d.score.to_numpy()[keep], y.to_numpy()[keep], d.dc.to_numpy()[keep]); out.append(f"y{h}: slope {s1:+.4f} t {t1:+.2f}")
        print(f"  {per:5s} {' | '.join(out)}")
    print("\n== D2: each C1 component alone (market-demeaned y1 / y5, POOL 2023-25 and PRE 2021-22), date-clustered t ==")
    for per in ("PRE", "POOL"):
        a, b = K.PERIODS[per]; m = ((B.date >= a) & (B.date <= b)).to_numpy(); d = B[m]; Xd = X[m]
        for comp in "ABCDEG":
            r = []
            for h in (1, 5):
                y = d[f"y{h}"].clip(-4, 4); y = y - y.groupby(d.mkt).transform("mean"); keep = (y.notna() & (Xd[comp] != 0)).to_numpy()
                if keep.sum() < 100: r.append("n/a"); continue
                bb, tt = cluster_slope(Xd[comp].to_numpy()[keep], y.to_numpy()[keep], d.dc.to_numpy()[keep]); r.append(f"y{h} {bb:+.3f} (t {tt:+.2f}, n {int(keep.sum())})")
            print(f"  {per:5s} {comp}: {' | '.join(r)}")
    print("\n== D3: model predictions -- time-series IC (prediction vs y, both demeaned per market) and market-neutral P&L ==")
    for kind, nm in (("ridge", "C2"), ("gbm", "C3")):
        for h, sfx in ((1, "a"), (5, "b")):
            R = K.walk(P, kind, h, (2023, 2024, 2025)); R["dc"] = pd.factorize(R.date)[0]
            p = R.pred - R.groupby("mkt").pred.transform("mean"); y = R.y.clip(-4, 4) - R.y.clip(-4, 4).groupby(R.mkt).transform("mean")
            b, t = cluster_slope(p.to_numpy(), y.to_numpy(), R.dc.to_numpy()); ic_ts = float(np.corrcoef(p, y)[0, 1])
            Rn = R.copy(); Rn["pos"] = Rn.pos - Rn.groupby("date").pos.transform("mean")          # remove the day's average position: market-neutral version
            Rd = R.copy(); Rd["pos"] = Rd.pos - Rd.groupby("mkt").pos.transform("mean")           # remove each market's average position: no static bias
            g, n, _ = K.portfolio(Rn); g2, n2, _ = K.portfolio(Rd); s_n = K.stat(K.sl(n, "POOL")); s_d = K.stat(K.sl(n2, "POOL"))
            print(f"  {nm}{sfx}: time-series IC {ic_ts:+.4f} (slope t {t:+.2f}) | market-neutral net Sharpe {s_n['sharpe']:+.2f} (t {s_n['t']:+.2f}) | no-static-bias net Sharpe {s_d['sharpe']:+.2f} (t {s_d['t']:+.2f})")
    print("\n== D4: the drift yardstick by class (long-only, POOL 2023-25 net Sharpe) ==")
    base = B[["date", "mkt", "sig", "nr", "cls"]]
    for ci, nm in K.CLS_NAME.items():
        sub = base[base.cls == ci].assign(pos=1.0); _, n, _ = K.portfolio(sub); s = K.stat(K.sl(n, "POOL")); print(f"  {nm:6s} long-only net Sharpe {s['sharpe']:+.2f} (t {s['t']:+.2f})")


if __name__ == "__main__":
    main()
