"""Descriptive (not a test): best ORB11_ENTRY rule per symbol over the last 3 months of data, with its earlier record and the random-entry luck ceiling.
   PYTHONPATH=. python forex/ea_research/best3m_lookup.py"""
import numpy as np, pandas as pd
import forex.ea_research.orb11_entry as oe
T = pd.read_parquet("data/si_ledgers/ORB11_ENTRY.parquet")
C = T[T.trig == "CTRL"].set_index(["mkt", "sess", "day"])[["r1", "rh"]].rename(columns={"r1": "c1", "rh": "ch"})
X = T[T.trig != "CTRL"].join(C, on=["mkt", "sess", "day"]).reset_index(drop=True)
A, B = pd.Timestamp("2026-07-03"), pd.Timestamp("2026-10-02")
L3 = ((X.day >= A) & (X.day <= B)).to_numpy(); PRE = (X.day < "2026-01-01").to_numpy(); H1 = ((X.day >= "2026-01-01") & (X.day < A)).to_numpy()
rows = []
for mk, g in X.groupby("mkt"):
    best = None; brnd = -9
    for ss in ("LON", "NY"):
        for tg in [t for t in oe.TRIGS if t != "FADE" or "--fade" in __import__("sys").argv]:
            for f in oe.FILTS:
                m = g.index[(g.sess == ss).to_numpy() & (g.trig == tg).to_numpy() & oe.fmask(g, f)]
                l3 = m[L3[m]]
                if len(l3) < 15: continue
                for x, cx in (("r1", "c1"), ("rh", "ch")):
                    tot = X.loc[l3, x].sum(); brnd = max(brnd, X.loc[l3, cx].sum())
                    if best is None or tot > best["R_3m"]:
                        best = dict(mkt=mk, rule=f"{ss} {tg} {f} {'1:1' if x == 'r1' else 'hold'}", n_3m=len(l3), R_3m=tot,
                                    R_trade=X.loc[l3, x].mean(), win=(X.loc[l3, x] > 0).mean(),
                                    jan_jun=X.loc[m[H1[m]], x].mean(), y22_25=X.loc[m[PRE[m]], x].mean())
    if best: best["rnd_best_3m"] = brnd; rows.append(best)
S = pd.DataFrame(rows).sort_values("R_3m", ascending=False)
pd.set_option("display.width", 250)
print(S.round(3).to_string(index=False))
print(f"\n{len(S)} symbols; median best 3-month total {S.R_3m.median():+.1f} R; median best of RANDOM entries {S.rnd_best_3m.median():+.1f} R; "
      f"best rule positive in Jan-Jun 2026: {int((S.jan_jun > 0).sum())}, in 2022-25: {int((S.y22_25 > 0).sum())}; mean earlier R/trade {S.y22_25.mean():+.3f}")
S.to_csv("data/scratch/best3m.csv", index=False)
