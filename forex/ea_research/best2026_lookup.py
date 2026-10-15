"""Descriptive (not a test): rank the ORB11_ENTRY rules by their 2026 result, with the random-entry luck ceiling. PYTHONPATH=. python forex/ea_research/best2026_lookup.py"""
import numpy as np, pandas as pd
import forex.ea_research.orb11_entry as oe
T = pd.read_parquet("D:/finance/si_ledgers/ORB11_ENTRY.parquet")
C = T[T.trig=="CTRL"].set_index(["mkt","sess","day"])[["r1","rh"]].rename(columns={"r1":"c1","rh":"ch"})
X = T[T.trig!="CTRL"].join(C, on=["mkt","sess","day"]).reset_index(drop=True)
X["yr"] = X.day.dt.year
y26 = (X.day >= "2026-01-01") & (X.day <= "2026-10-02")
rows=[]
for (mk,ss),g in X.groupby(["mkt","sess"]):
    for tg in oe.TRIGS:
        for f in oe.FILTS:
            m = (g.trig==tg).to_numpy() & oe.fmask(g,f)
            s = g[m]
            for x,cx in (("r1","c1"),("rh","ch")):
                a = s[y26[s.index]]
                if len(a) < 30: continue
                rows.append(dict(mkt=mk,sess=ss,trig=tg,filt=f,exit=x,n26=len(a),R26=a[x].mean(),sum26=a[x].sum(),t26=oe.tstat(a[x]),
                    t26_rnd=oe.tstat(a[cx]), **{f"y{y}":s[s.yr==y][x].mean() for y in (2022,2023,2024,2025)},
                    pre=s[s.day<"2026-01-01"][x].mean(), tpre=oe.tstat(s[s.day<"2026-01-01"][x])))
S = pd.DataFrame(rows).sort_values("t26", ascending=False)
pd.set_option("display.width",250)
print(len(S), "rules tested in 2026 (>=30 trades)")
print(S.head(15).round(3).to_string(index=False))
print(f"luck: highest 2026 t on random entries (same days, same exit) {S.t26_rnd.max():.2f}; 99th pct real {np.nanpercentile(S.t26,99):.2f} vs random {np.nanpercentile(S.t26_rnd,99):.2f}")
top = S.head(50); print(f"top 50 by 2026: mean 2026 {top.R26.mean():+.3f}, mean 2022-25 {top.pre.mean():+.3f}, positive 2022-25 {int((top.pre>0).sum())}/50")
S.to_csv("D:/finance/scratch/best2026_entry.csv", index=False)
