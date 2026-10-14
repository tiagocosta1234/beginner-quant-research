import numpy as np, pandas as pd
from forex.self_improving.day2k import day2k as D
T=10*3600+5*60; days=D.trading_days("2021-12-01","2025-12-31"); full=D.trading_days("2021-01-01","2025-12-31"); idx={int(d):i for i,d in enumerate(full)}
def run(sym,look,k):
    A=D.load(sym); t=A["t"]; atr=D.atr20(A,full); pT=D.price_at(A,full*86400+T-60); busy=0; rows=[]
    for d in days:
        if d*86400+T<busy: continue
        i=idx[int(d)]
        if i<look or not np.isfinite(pT[i]) or not np.isfinite(pT[i-look]) or not np.isfinite(atr[i]): continue
        side=1 if pT[i]>pT[i-look] else -1; i0=np.searchsorted(t,d*86400+T+60)
        if i0>=len(t) or t[i0]!=d*86400+T+60: continue
        E=A["ao"][i0] if side>0 else A["bo"][i0]; Dd=k*atr[i]; tp=E+side*Dd; sl=E-side*Dd; j1=np.searchsorted(t,d*86400+T+200*86400)
        hi=A["bh"][i0:j1] if side>0 else A["ah"][i0:j1]; lo=A["bl"][i0:j1] if side>0 else A["al"][i0:j1]; op=A["bo"][i0:j1] if side>0 else A["ao"][i0:j1]
        htp,hsl=(hi>=tp,lo<=sl) if side>0 else (lo<=tp,hi>=sl)
        a=np.argmax(htp) if htp.any() else 10**9; b=np.argmax(hsl) if hsl.any() else 10**9
        if a==b==10**9: continue                                  # unresolved at the data end: not counted
        if b<=a:
            fill=op[b] if (side>0 and op[b]<sl) or (side<0 and op[b]>sl) else sl; r=side*(fill-E)/Dd; ix=i0+b
        else: r=1.0; ix=i0+a
        rows.append((d,side,r)); busy=t[ix]+60
    x=pd.DataFrame(rows,columns=["d","side","R"]); return x
mk=["XAUUSD","XAGUSD","SP","NSDQ","DOW","DAX","NIKKEI","BTCUSD","ETHUSD","EURUSD","USDJPY","GBPUSD","AUDUSD","USDCAD","WTI"]
for look,k in ((60,1.5),(60,2.0),(120,1.5)):
    print(f"\n== trend {look}d, stop = target {k} ATR, hold until hit (EXPLORATORY, 2021-12..2025) ==")
    allw=[]; 
    for s in mk:
        x=run(s,look,k); w=(x.R>0).mean(); allw.append((s,len(x),w,x.R.mean(),(x.side>0).mean()))
        print(f"  {s:7s} trades {len(x):3d} | +2,000 {100*w:5.1f}% | mean {2000*x.R.mean():+5.0f} USD/trade | long {100*(x.side>0).mean():3.0f}%")
    n=sum(a[1] for a in allw); ww=sum(a[1]*a[2] for a in allw)/n; print(f"  POOLED excl. gold: {sum(a[1] for a in allw[1:])} trades, +2,000 {100*sum(a[1]*a[2] for a in allw[1:])/sum(a[1] for a in allw[1:]):.1f}% | markets above 50%: {sum(a[2]>0.5 for a in allw)} of {len(allw)}")
