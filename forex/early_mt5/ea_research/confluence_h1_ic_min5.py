"""Diagnostic (NOT a trial, cannot accept anything): the cross-sectional rank IC of the K2 / K2b hourly models re-measured on minute-5 labels.
   python -m mt5broker.ea_research.confluence_h1_ic_min5
Open lead from CONFLUENCE_H1_RESULT.md: the IC of +0.02..+0.04 (t 5-16) was measured on first-minute-to-first-minute labels, which are partly a quote-boundary artefact.
y1 (K2 label)  = ln(m0_(k+2) / m0_(k+1)) / sig, m0 = mid at the first minute of the bar.
With a_j = ln(m5_j / m0_j) (the move of the first five minutes of bar j):  y1 = core5 + a_(k+1) - a_(k+2),  core5 = ln(m5_(k+2) / m5_(k+1)) / sig is what a minute-5 execution can earn.
Same for the 4-hour label. IC rows exclude decision hours 22, 23, 0 in every column (the rollover window), and also report the all-hours figure that K2 published."""
from __future__ import annotations

import numpy as np
import pandas as pd

import mt5broker.ea_research.confluence_h1 as H

ROLL = (22, 23, 0)


def minute5_marks(P: pd.DataFrame) -> pd.DataFrame:
    """Per market, aligned to the panel rows: m5 at the first minute with minute-of-hour >= 5 (bid/ask mid) and the adjacency of the bars used by each label."""
    out = []
    for m, g in P.groupby("mkt", sort=False):
        d = pd.read_parquet(H.DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "ao"]).sort_values("t"); d = d[(d.bo > 0) & (d.ao >= d.bo)]
        d5 = d[(d.t % 3600) >= 300]; f = d5.groupby(d5.t // 3600).first(); a = pd.Series(((f.bo + f.ao) / 2).to_numpy(), index=f.index.to_numpy() * 3600)
        T = g["T"].to_numpy("int64"); m5 = a.reindex(T).to_numpy(); m0 = np.exp(np.log(g.m.to_numpy())) if "m" in g else None
        sh = lambda x, k: np.r_[x[k:], np.full(k, np.nan)]
        Tn1, Tn2, Tn5 = sh(T.astype(float), 1), sh(T.astype(float), 2), sh(T.astype(float), 5)
        adj1 = (Tn1 - T == 3600) & (Tn2 - T == 7200); adj4 = (Tn5 - Tn1 == 14400) & (Tn1 - T == 3600)
        out.append(pd.DataFrame({"mkt": m, "T": T, "m5_1": sh(m5, 1), "m5_2": sh(m5, 2), "m5_5": sh(m5, 5), "adj1": adj1, "adj4": adj4}))
    return pd.concat(out, ignore_index=True)


def day_ic(df: pd.DataFrame, ycol: str, minn=20):
    d = df.dropna(subset=[ycol, "pred"]); d = d[d.groupby("T").pred.transform("size") >= minn]
    rp = d.groupby("T").pred.rank(); ry = d.groupby("T")[ycol].rank()
    rp = rp - rp.groupby(d["T"]).transform("mean"); ry = ry - ry.groupby(d["T"]).transform("mean")
    ic = ((rp * ry).groupby(d["T"]).sum() / np.sqrt((rp ** 2).groupby(d["T"]).sum() * (ry ** 2).groupby(d["T"]).sum())).dropna()
    day = ic.groupby(pd.to_datetime(ic.index, unit="s").normalize()).mean()
    return float(day.mean()), float(day.mean() / (day.std(ddof=1) / np.sqrt(len(day)))), len(day), len(d)


def main():
    P, _ = H.build_panel(); M = minute5_marks(P)
    print("== IC of the walk-forward models (test 2024-25), cross-sectional rank IC by server day, t over days ==")
    print("columns: ALL = K2's published figure (all hours, minute-0 label); then rollover hours 22/23/0 excluded: MIN0 = minute-0 label; MIN5 = minute-5 label (core5, adjacent bars only); BND = boundary term a(k+1)-a(k+2)")
    for variant, drop in (("K2 ", ()), ("K2b", ROLL)):
        H.DROP = drop
        for kind, nm in (("seas", "S"), ("gbm", "G")):
            for h in (1, 4):
                R = H.walk(P, kind, h, (2024, 2025)); R = R.merge(M, on=["mkt", "T"], how="left"); sg = R.sig.astype("float64")
                if h == 1: R["y5"] = np.log(R.m5_2 / R.m5_1) / sg; ok = R.adj1
                else: R["y5"] = np.log(R.m5_5 / R.m5_1) / (sg * 2); ok = R.adj4
                R["y5"] = R.y5.where(ok); R["bnd"] = (R.y - R.y5)           # y - core5 = a(k+1) - a(k+2) (in sigma units); only where the minute-5 label exists
                keep = ~R.hour.isin(ROLL)
                a = day_ic(R, "y"); b = day_ic(R[keep], "y"); c = day_ic(R[keep], "y5"); e = day_ic(R[keep], "bnd")
                print(f"{variant} {nm}{h}: ALL {a[0]:+.4f} (t {a[1]:+6.2f}) | MIN0 {b[0]:+.4f} (t {b[1]:+6.2f}) | MIN5 {c[0]:+.4f} (t {c[1]:+6.2f}, {c[2]} days, {c[3]} rows) | BND {e[0]:+.4f} (t {e[1]:+6.2f})", flush=True)
    H.DROP = ()


if __name__ == "__main__":
    main()
