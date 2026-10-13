"""Iteration 4 (pre-registered in lab/PREREG.md): direction-neutral cross-sectional momentum / reversal inside FX6 and IDX4.   python -m forex.intraday_lab.scan4"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from forex.intraday_lab.lab import FX, Bars, commission_price

OUT = Path(r"D:\finance\scratch\lab")
GROUPS = {"FX6": FX, "IDX4": ("US100.cash", "US30.cash", "US500.cash", "GER40.cash")}
PH = {"dev": ("2021-10-01", "2023-12-31"), "val": ("2024-01-01", "2024-12-31"), "hold": ("2025-01-01", "2026-10-02")}


def panel(syms, tf):
    bs = [Bars(s, tf) for s in syms]
    common = bs[0].t
    for b in bs[1:]:
        common = np.intersect1d(common, b.t)
    ix = [np.searchsorted(b.t, common) for b in bs]
    mid = np.column_stack([b.mid[i] for b, i in zip(bs, ix)]); atr = np.column_stack([b.atr(14)[i] for b, i in zip(bs, ix)])
    cost = np.column_stack([((b.ao - b.bo)[i] + commission_price(b.sym, float(np.nanmedian(b.mid)))) / b.atr(14)[i] for b, i in zip(bs, ix)])
    return common, mid, atr, cost


def main():
    rows = []
    for gname, syms in GROUPS.items():
        for tf in (5, 15):
            t, mid, atr, cost = panel(syms, tf); n = len(t)
            for k in (4, 16, 48):
                score = np.full_like(mid, np.nan); score[k:] = (mid[k:] - mid[:-k]) / atr[k:]
                for h in (4, 16, 48):
                    fwd = np.full_like(mid, np.nan); fwd[:-h] = (mid[h:] - mid[:-h]) / atr[:-h]
                    okgap = np.r_[(t[h:] - t[:-h]) <= h * tf * 60 * 3, np.zeros(h, bool)]
                    for ph, (a, b) in PH.items():
                        lo, hi = int(pd.Timestamp(a).timestamp()), int(pd.Timestamp(b).timestamp()) + 86400
                        ix = np.flatnonzero((t >= lo) & (t < hi) & okgap)[::h]
                        ix = ix[np.all(np.isfinite(score[ix]), axis=1) & np.all(np.isfinite(fwd[ix]), axis=1) & np.all(np.isfinite(cost[ix]), axis=1)]
                        top = np.argmax(score[ix], axis=1); bot = np.argmin(score[ix], axis=1); r = np.arange(len(ix))
                        ls = fwd[ix][r, top] - fwd[ix][r, bot]; cst = cost[ix][r, top] + cost[ix][r, bot]
                        for hyp, sgn in (("mom", 1), ("rev", -1)):
                            net = sgn * ls - cst
                            rows.append(dict(group=gname, tf=tf, k=k, h=h, hyp=hyp, phase=ph, n=len(ix), gross=float(np.mean(sgn * ls)), cost=float(np.mean(cst)), net=float(np.mean(net)), t=float(np.mean(net) / (np.std(net, ddof=1) / np.sqrt(len(ix)))), gross_t=float(np.mean(sgn * ls) / (np.std(sgn * ls, ddof=1) / np.sqrt(len(ix))))))
    D = pd.DataFrame(rows); D.to_csv(OUT / "scan4_raw.csv", index=False)
    P = D.pivot_table(index=["group", "tf", "k", "h", "hyp"], columns="phase", values=["net", "t", "gross", "gross_t", "cost"]); P.columns = [f"{a}_{b}" for a, b in P.columns]; P = P.reset_index()
    print("tests K =", len(P))
    hit = P[(P.net_dev > 0) & (P.t_dev >= 3.5) & (P.net_val > 0) & (P.t_val >= 2)]
    cols = ["group", "tf", "k", "h", "hyp", "gross_dev", "cost_dev", "net_dev", "t_dev", "net_val", "t_val", "net_hold", "t_hold"]
    print("PRE-REGISTERED HITS:", len(hit)); print(hit[cols].round(3).to_string(index=False) if len(hit) else "none")
    print("\nTop 10 by GROSS t on dev (learning only):"); print(P.sort_values("gross_t_dev", ascending=False).head(10)[["group", "tf", "k", "h", "hyp", "gross_dev", "cost_dev", "gross_t_dev", "gross_val", "gross_t_val", "gross_hold"]].round(3).to_string(index=False))
    print("\nmedian gross / cost (ATR units):", round(P.gross_dev.median(), 3), round(P.cost_dev.median(), 3))


if __name__ == "__main__":
    main()
