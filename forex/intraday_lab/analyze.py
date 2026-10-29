import pandas as pd, numpy as np, sys
from pathlib import Path
O=Path("data/scratch/lab")
def load(ph): return pd.concat([pd.read_csv(O/f"results_{ph}_{tf}.csv") for tf in (1,5,15)])
def agg(d):
    d=d.copy(); d["se"]=np.where(d.t.abs()>1e-9,(d["mean"]/d.t).abs(),np.nan)
    out=[]
    for k,x in d.groupby(["tf","family","params"]):
        x=x[x.n>=100]
        if len(x)<6: out.append((*k,len(x),np.nan,np.nan,np.nan)); continue
        N=x.n.sum(); pm=(x.n*x["mean"]).sum()/N; se=np.sqrt(np.nansum((x.n*x.se)**2))/N
        out.append((*k,len(x),int((x["mean"]>0).sum()),pm,pm/se if se>0 else np.nan))
    return pd.DataFrame(out,columns=["tf","family","params","syms","pos","pooledR","pooled_t"])
def main(a,b,tag):
    A,B=agg(load(a)),agg(load(b)); m=A.merge(B,on=["tf","family","params"],suffixes=("_a","_b"))
    print(f"[{a} vs {b}] cells:",len(m))
    print(m.groupby(["tf","family"]).agg(cells=("pooledR_a","size"),R_a=("pooledR_a","median"),R_b=("pooledR_b","median"),pos_a=("pooledR_a",lambda x:(x>0).mean()),both=("pooledR_a",lambda s:((s>0)&(m.loc[s.index,"pooledR_b"]>0)).mean())).round(3).to_string())
    c=m[(m.pos_a>=8)&(m.pos_b>=8)&(m.pooled_t_a>=3)&(m.pooled_t_b>=1.5)]
    print("PRE-REGISTERED CANDIDATES:",len(c)); print(c.to_string())
    print("Top 6 by pooled t on",a,"(learning only):"); print(m.sort_values("pooled_t_a",ascending=False).head(6)[["tf","family","params","pos_a","pooledR_a","pooled_t_a","pos_b","pooledR_b","pooled_t_b"]].round(3).to_string(index=False))
    print("corr of pooled R between phases:",round(m.pooledR_a.corr(m.pooledR_b),2)); m.to_csv(O/f"summary_{tag}.csv",index=False)
if __name__=="__main__": main(sys.argv[1],sys.argv[2],sys.argv[3])
