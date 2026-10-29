"""LON_RISK (PREREG_LON_RISK.md): risk-per-trade sweep (FLAT / EQRISK) for the 7 kept London rules and all 127 combinations, vectorised MT5 broker cycles.
   python -m forex.ea_research.lon_risk"""
import warnings
from itertools import combinations

import numpy as np
import pandas as pd

from forex.ea_research.best3m_cycle import cycle
from forex.ea_research.lon_combo import series

warnings.filterwarnings("ignore")
XS = np.arange(100, 1501, 100)
WIN = {"2026": ("2026-01-01", "2026-08-31", "2026-06-30", "2026-10-02"), "2022-25": ("2022-01-01", "2025-12-31", "2025-12-31", "2026-10-02"),
       "2020-21": ("2020-01-01", "2021-10-31", "2021-08-31", "2021-11-30")}


def vec_cycles(net, worst, dates, starts, horizon_days):
    """all starts at once; returns pass / breach booleans within horizon_days calendar days."""
    n = len(net); jmax = np.searchsorted(dates, dates[starts] + np.timedelta64(horizon_days, "D"), side="right") - 1
    bal = np.full(len(starts), 100_000.0); st = np.zeros(len(starts), int)
    for k in range(int((jmax - starts).max()) + 1):
        i = starts + k; act = (st == 0) & (i <= jmax) & (i < n)
        if not act.any(): break
        ii = np.minimum(i, n - 1); w = worst[ii]; v = net[ii]
        br = act & ((w <= -2500) | (bal + w <= 92_000)); st[br] = 2
        ok = act & ~br; bal[ok] += np.minimum(v[ok], 2000.0)
        ps = ok & (bal >= 108_000); st[ps] = 1
    return st == 1, st == 2


def main():
    pd.set_option("display.width", 250)
    ser = series(); syms = sorted(ser)
    sd = {m: ser[m][(ser[m].index >= "2022-01-01") & (ser[m].index <= "2024-12-31")].std() for m in syms}
    rows = []
    for k in range(1, len(syms) + 1):
        for combo in combinations(syms, k):
            df = pd.concat({m: ser[m] for m in combo}, axis=1).sort_index()
            for scheme in ("FLAT", "EQRISK"):
                if scheme == "EQRISK" and k == 1: continue
                wts = np.ones(k) if scheme == "FLAT" else np.array([1 / sd[m] for m in combo]); wts = wts / wts.mean()
                R = df.to_numpy() * wts
                net1 = np.nansum(R, axis=1); neg1 = np.nansum(np.minimum(R, 0), axis=1); dates = df.index.values.astype("datetime64[D]")
                for w, (a, b, b90, end) in WIN.items():
                    sub = (dates <= np.datetime64(end)) if w == "2020-21" else (dates >= np.datetime64("2022-01-01"))
                    if w == "2020-21" and combo == ("DOW",): continue
                    dsub = dates[sub]; n_ = net1[sub]; g_ = neg1[sub]
                    s30 = np.flatnonzero((dsub >= np.datetime64(a)) & (dsub <= np.datetime64(b)))
                    s90 = np.flatnonzero((dsub >= np.datetime64(a)) & (dsub <= np.datetime64(b90)))
                    for X in XS:
                        p30, b30 = vec_cycles(n_ * X, n_ * X, dsub, s30, 30)
                        p90, b90_ = vec_cycles(n_ * X, n_ * X, dsub, s90, 90)
                        rows.append(dict(combo="+".join(combo), k=k, scheme=scheme, X=int(X), win=w, p30=p30.mean(), b30=b30.mean(), p90=p90.mean(), b90=b90_.mean()))
    R = pd.DataFrame(rows); R.to_csv("data/si_ledgers/LON_RISK.csv", index=False)
    P = R.pivot_table(index=["combo", "k", "scheme", "X"], columns="win", values=["p30", "b30", "p90", "b90"])
    P.columns = [f"{a}_{b}" for a, b in P.columns]; P = P.reset_index()
    # engine check against the loop version on one cell
    d = pd.concat({m: ser[m] for m in ("USDJPY",)}, axis=1).sort_index(); d = d[d.index >= "2022-01-01"]
    dd = pd.DataFrame({"net": d.sum(axis=1), "neg": d.clip(upper=0).sum(axis=1)})
    st = [i for i, x in enumerate(dd.index) if pd.Timestamp("2022-01-01") <= x <= pd.Timestamp("2025-12-31")]
    loop = np.array([cycle(dd, i, 1000, False) for i in st]); lp = np.mean((loop[:, 0] == 1) & (loop[:, 1] <= 30))
    print(f"engine check USDJPY USD 1000 2022-25 30-day pass: loop {lp:.3f} vs vectorised {P[(P.combo == 'USDJPY') & (P.X == 1000)]['p30_2022-25'].iloc[0]:.3f}")
    cols = ["combo", "scheme", "X", "p30_2026", "b30_2026", "p30_2022-25", "b30_2022-25", "p30_2020-21", "b30_2020-21"]
    cols90 = ["combo", "scheme", "X", "p90_2026", "b90_2026", "p90_2022-25", "b90_2022-25", "p90_2020-21", "b90_2020-21"]
    print("\n1. EACH SYMBOL: best 30-day pass with 30-day breach <= 10% in 2026, any risk:")
    one = P[P.k == 1]
    for m, g in one.groupby("combo"):
        q = g[g.b30_2026 <= 0.10].sort_values("p30_2026", ascending=False).head(1)
        print(q[cols].round(3).to_string(index=False, header=(m == one.combo.iloc[0])))
    for w in ("2026", "2022-25", "2020-21"):
        q = P[P[f"b30_{w}"] <= 0.10].sort_values(f"p30_{w}", ascending=False).head(8)
        print(f"\n2. BEST 30-DAY PASS WITH BREACH <= 10%, chosen on {w} (all combos, schemes, risks):\n" + q[cols].round(3).to_string(index=False))
    for w in ("2026", "2022-25", "2020-21"):
        q = P[P[f"b90_{w}"] <= 0.10].sort_values(f"p90_{w}", ascending=False).head(8)
        print(f"\n3. BEST 90-DAY PASS WITH BREACH <= 10%, chosen on {w}:\n" + q[cols90].round(3).to_string(index=False))
    pr = P[(P["p90_2020-21"] >= 0.30) & (P["p90_2020-21"] > P["b90_2020-21"])]
    print(f"\n4. promising (2020-21 90-day pass >= 30% and > breach): {len(pr)} of {len(P)}")
    if len(pr): print(pr.sort_values("p90_2020-21", ascending=False).head(10)[cols90].round(3).to_string(index=False))
    print("\n5. Frontier, max 30-day pass at each 30-day breach cap (any config), per period:")
    for w in ("2026", "2022-25", "2020-21"):
        print("  ", w, {cap: round(float(P[P[f'b30_{w}'] <= cap][f'p30_{w}'].max()), 3) for cap in (0.02, 0.05, 0.10, 0.20, 0.30, 0.50)})


if __name__ == "__main__":
    main()
