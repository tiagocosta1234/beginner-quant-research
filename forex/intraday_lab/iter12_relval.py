"""Iteration 12 (pre-registered in lab/PREREG.md): index relative value (pairs fade), direction-neutral, holds of hours.   python -m forex.intraday_lab.iter12_relval"""
from __future__ import annotations

from itertools import product

import numpy as np
import pandas as pd

from forex.intraday_lab.lab import Bars
from forex.intraday_lab.scan6 import thin

PAIRS = (("US100.cash", "US500.cash"), ("US100.cash", "US30.cash"), ("US500.cash", "US30.cash"))


def main():
    rows = []
    for a, bsym in PAIRS:
        A, B = Bars(a, 5), Bars(bsym, 5)
        t = np.intersect1d(A.t, B.t); ia = np.searchsorted(A.t, t); ib = np.searchsorted(B.t, t)
        ma, mb = A.mid[ia], B.mid[ib]; r = np.log(ma) - np.log(mb); rs = pd.Series(r)
        sp = ((A.ao - A.bo)[ia] / ma + (B.ao - B.bo)[ib] / mb)
        dvol = np.nanstd(np.diff(r)) * np.sqrt(288)
        year = pd.DatetimeIndex(pd.to_datetime(t, unit="s")).year.values
        for L, thr, H in product((288, 1440), (2.0, 3.0), (12, 24, 48)):
            z = ((rs - rs.rolling(L).mean()) / rs.rolling(L).std()).values
            prev = np.r_[np.nan, z[:-1]]
            cond = ((z >= thr) & (prev < thr)) | ((z <= -thr) & (prev > -thr))
            ix = np.flatnonzero(cond & np.isfinite(z)); ix = ix[ix + H < len(t)]
            ok = (t[ix + H] - t[ix]) <= H * 5 * 60 * 3; ix = ix[ok]
            ix = thin(ix, H)
            sgn = -np.sign(z[ix]); fwd = sgn * (r[ix + H] - r[ix]) / dvol; cost = sp[ix] / dvol
            for ph, m in (("dev", year[ix] <= 2023), ("val", year[ix] == 2024), ("hold", year[ix] >= 2025)):
                rows.append(dict(pair=a + "/" + bsym, L=L, thr=thr, H=H, phase=ph, n=int(m.sum()), sig=float(fwd[m].mean()) if m.sum() else np.nan, net=float((fwd - cost)[m].mean()) if m.sum() else np.nan,
                                 sd=float((fwd - cost)[m].std(ddof=1)) if m.sum() > 2 else np.nan, cost=float(cost[m].mean()) if m.sum() else np.nan))
    D = pd.DataFrame(rows); D.to_csv(r"D:\finance\scratch\lab\iter12_raw.csv", index=False)
    out = []
    for k, x in D[D.n >= 20].groupby(["L", "thr", "H", "phase"]):
        N = x.n.sum(); m = (x.n * x.net).sum() / N; se = np.sqrt((((x.sd) * np.sqrt(x.n)) ** 2).sum()) / N
        out.append(dict(L=k[0], thr=k[1], H=k[2], phase=k[3], n=int(N), net=m, t=m / se, pos=int((x.net > 0).sum()), gross=(x.n * x.sig).sum() / N, cost=(x.n * x.cost).sum() / N))
    P = pd.DataFrame(out).pivot_table(index=["L", "thr", "H"], columns="phase", values=["n", "net", "t", "pos", "gross", "cost"]); P.columns = [f"{a}_{b}" for a, b in P.columns]; P = P.reset_index()
    print("K =", len(P), "(pairs pooled per cell; 36 pair-cells in total)")
    hit = P[(P.net_dev > 0) & (P.t_dev >= 3.6) & (P.net_val > 0) & (P.t_val >= 2) & (P.pos_dev >= 2) & (P.pos_val >= 2)]
    cols = ["L", "thr", "H", "n_dev", "gross_dev", "cost_dev", "net_dev", "t_dev", "pos_dev", "n_val", "net_val", "t_val", "pos_val", "net_hold", "t_hold"]
    print("PRE-REGISTERED HITS:", len(hit)); print(hit[cols].round(4).to_string(index=False) if len(hit) else "none")
    print("\nAll cells by DEV t:"); print(P.sort_values("t_dev", ascending=False)[cols].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
