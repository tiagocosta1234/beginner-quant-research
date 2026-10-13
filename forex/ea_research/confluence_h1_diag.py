"""Exploratory diagnostics for families K2 / K2b / K3 (NOT trials; they cannot accept anything). Reproduces the numbers quoted in CONFLUENCE_H1_RESULT.md.
   python -m forex.ea_research.confluence_h1_diag
D1 execution spread by decision hour (the rollover defect of K2); D2 dissection of the S1b seasonality model's gross P&L; D3 the same positions re-marked at minute 5 (boundary-mid artefact);
D4 distribution of the hour x market t-statistics against a placebo (why K3's rule selects nothing)."""
from __future__ import annotations

import numpy as np
import pandas as pd

import forex.ea_research.confluence_h1 as H
from forex.ea_research import seasonal_hour as S


def main():
    P, _ = H.build_panel(); P["sp0"] = (P.cs - H.SLIP) * 2
    print("== D1: relative spread at the execution minute (bp) by decision hour; hour 23 executes at 00:00 (rollover) ==")
    t = P.groupby("hour").sp0.median() * 1e4; print("all markets median:", {int(h): round(float(v), 2) for h, v in t.items() if h in (21, 22, 23, 0, 1, 2)})
    for m in ["EURUSD", "XAUUSD", "SP", "BTCUSD"]:
        r = P[P.mkt == m].groupby("hour").sp0.median() * 1e4; print(f"  {m}:", {int(h): round(float(r.get(h, np.nan)), 2) for h in (21, 22, 23, 0, 1, 2)})
    H.DROP = (22, 23, 0)
    print("\n== D2: S1b gross P&L dissected (test 2024-25) ==")
    R = H.walk(P, "seas", 1, (2024, 2025)); R["w"] = np.where(R.sig > 0, R.pos * H.TARGET / R.sig.where(R.sig > 0, 1), 0.0); R["g"] = R.w * R.nr; R["year"] = R.date.dt.year
    R = R.sort_values(["mkt", "T"]); R["dw"] = R.groupby("mkt").w.diff().abs().fillna(R.w.abs()); R["cost"] = R.cs * R.dw
    print(f"gross {R.groupby('date').g.sum().mean()*1e4:.1f} bp/day vs cost {R.groupby('date').cost.sum().mean()*1e4:.1f} bp/day | position changes per day per market {(R.dw > 1e-9).sum()/R.date.nunique()/R.mkt.nunique():.2f}")
    c = R.groupby(["mkt", "hour", "year"]).g.sum().unstack("year"); print(f"cells {len(c)}; correlation of cell gross between 2024 and 2025: {c[2024].corr(c[2025]):.3f}")
    print("gross by class (bp total):", {H.CLS_NAME[k]: round(v * 1e4) for k, v in R.assign(cl=R.mkt.map(H.CLS)).groupby("cl").g.sum().items()})
    print("\n== D3: same positions marked at minute 5 instead of minute 0 ==")
    alt = {}
    for m in H.MARKETS:
        d = pd.read_parquet(H.DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "ao"]).sort_values("t"); d = d[(d.bo > 0) & (d.ao >= d.bo)]; d5 = d[(d.t % 3600) >= 300]; g = d5.groupby(d5.t // 3600).first()
        alt[m] = pd.Series(((g.bo + g.ao) / 2).to_numpy(), index=g.index.to_numpy() * 3600)
    out = []
    for m, g in P.groupby("mkt", sort=False):
        T = g["T"].to_numpy(); a = alt[m].reindex(T).to_numpy(); out.append(pd.DataFrame({"mkt": m, "T": T, "nr5": np.r_[a[2:] / a[1:-1] - 1.0, [np.nan, np.nan]]}))
    R = R.merge(pd.concat(out), on=["mkt", "T"], how="left"); R["g5"] = R.w * R.nr5
    for y in (2024, 2025):
        x = R[R.year == y]; d1, d5 = x.groupby("date").g.sum(), x.groupby("date").g5.sum()
        print(f"  {y}: gross Sharpe minute-0 marks {d1.mean()/d1.std()*np.sqrt(252):.2f} | minute-5 marks {d5.mean()/d5.std()*np.sqrt(252):.2f}")
    print("  gross by class minute-0 vs minute-5 (bp):", {H.CLS_NAME[k]: (round(a * 1e4), round(b * 1e4)) for k, (a, b) in R.assign(cl=R.mkt.map(H.CLS)).groupby("cl")[["g", "g5"]].sum().iterrows()})
    print("\n== D4: hour x market cell t-statistics in the training window, real vs placebo (hours shuffled within market-date) ==")
    Q = S.build()
    for Y in (2024, 2025, 2026):
        tr = S.train_rows(Q, Y); C = S.cells(tr); pc = S.cells(S.placebo(tr, seed=5)); q = lambda x: {k: int((x.t.abs() >= k).sum()) for k in (2.5, 3, 3.5, 4)}
        print(f"  test {Y}: cells {len(C)} | |t| >= 2.5/3/3.5/4: real {q(C)} placebo {q(pc)} | cells passing the cost hurdle too: {int(C.sel.sum())}")
        top = C.reindex(C.t.abs().sort_values(ascending=False).index).head(5)
        print("     strongest (market, hour, t, mean bp, round-trip cost bp):", [(m, int(h), round(float(r.t), 1), round(float(r.mean_bp), 1), round(float(r.cost_bp), 1)) for (m, h), r in top.iterrows()])


if __name__ == "__main__":
    main()
