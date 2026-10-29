import numpy as np, pandas as pd
import forex.ea_research.orb11_entry as oe
T = pd.read_parquet("data/si_ledgers/ORB11_ENTRY.parquet"); T = T[(T.sess=="NY") & T.mkt.isin(["NSDQ","XAUUSD"])]
C = T[T.trig=="CTRL"].set_index(["mkt","day"])[["r1","rh"]].rename(columns={"r1":"c1","rh":"ch"})
X = T[T.trig!="CTRL"].join(C, on=["mkt","day"])
pd.set_option("display.width",250)
for lab, a in (("3 meses", "2026-07-03"), ("6 meses", "2026-04-03")):
    for mk in ("NSDQ","XAUUSD"):
        g = X[X.mkt==mk]; rows=[]; rnd=[]
        for tg in oe.TRIGS:
            for f in oe.FILTS:
                s = g[(g.trig==tg).to_numpy() & oe.fmask(g,f)]
                w = s[s.day>=a]; pre = s[s.day<"2026-01-01"]; h1 = s[(s.day>="2026-01-01")&(s.day<a)]
                if len(w)<10: continue
                for x,cx in (("r1","c1"),("rh","ch")):
                    rnd.append(w[cx].sum())
                    rows.append(dict(rule=f"{tg} {f} {'1:1' if x=='r1' else 'hold'}", n=len(w), total=w[x].sum(), per=w[x].mean(), win=(w[x]>0).mean(),
                                     t=oe.tstat(w[x]), before_2026=h1[x].mean() if lab=="3 meses" else np.nan, y22_25=pre[x].mean(), n22_25=len(pre)))
        S = pd.DataFrame(rows).sort_values("total", ascending=False)
        print(f"\n=== {mk} NY, last {lab} (from {a} to 2026-10-02), {len(S)} rules; best random-entry total on the same days {max(rnd):+.1f} R")
        print(S.head(6).round(3).to_string(index=False))
        print("   ORB11 baseline (TOUCH F0 1:1):", S[S.rule=="TOUCH F0 1:1"].round(3).to_dict("records"))
