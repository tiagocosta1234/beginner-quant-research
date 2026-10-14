import numpy as np, pandas as pd
from forex.self_improving.day2k import day2k as D
A=D.load("XAUUSD"); t=A["t"]; days=D.trading_days("2021-12-01","2025-12-31"); full=D.trading_days("2021-01-01","2025-12-31")
atr_f=D.atr20(A,full); T=10*3600+5*60
pT=D.price_at(A,full*86400+T-60)
def trade(i0,side,Dd,tmax):
    E=A["ao"][i0] if side>0 else A["bo"][i0]; tp=E+side*Dd; sl=E-side*Dd; j1=np.searchsorted(t,tmax)
    hi=A["bh"][i0:j1] if side>0 else A["ah"][i0:j1]; lo=A["bl"][i0:j1] if side>0 else A["al"][i0:j1]; op=A["bo"][i0:j1] if side>0 else A["ao"][i0:j1]
    htp,hsl=(hi>=tp,lo<=sl) if side>0 else (lo<=tp,hi>=sl)
    a=np.argmax(htp) if htp.any() else 10**9; b=np.argmax(hsl) if hsl.any() else 10**9
    if a==b==10**9: return np.nan,j1-1
    if b<=a:
        fill=op[b] if (side>0 and op[b]<sl) or (side<0 and op[b]>sl) else sl
        return side*(fill-E)/Dd, i0+b
    return 1.0, i0+a
idx={int(d):i for i,d in enumerate(full)}
print("gold, entry 10:05 server, hold until +2,000 or -2,000, one trade at a time, 2021-12..2025 (EXPLORATORY)")
for look in (20,60,120):
    for k in (0.7,1.0,1.5,2.0,3.0):
        busy=0; rows=[]
        for d in days:
            if d*86400+T<busy: continue
            i=idx[int(d)]
            if i<look or not np.isfinite(pT[i]) or not np.isfinite(pT[i-look]) or not np.isfinite(atr_f[i]): continue
            side=1 if pT[i]>pT[i-look] else -1
            i0=np.searchsorted(t,d*86400+T+60)
            if i0>=len(t) or t[i0]!=d*86400+T+60: continue
            r,ix=trade(i0,side,k*atr_f[i],d*86400+T+120*86400)
            if not np.isfinite(r): break
            rows.append((d,side,r,(t[ix]-t[i0])/86400)); busy=t[ix]+60
        x=pd.DataFrame(rows,columns=["d","side","R","hold"]); yr=pd.to_datetime(x.d.astype("datetime64[D]")).dt.year
        wy=" ".join(f"{y}:{100*(g.R>0).mean():.0f}%({len(g)})" for y,g in x.groupby(yr))
        print(f"  trend {look:3d}d, stop=target {k:.1f} ATR: trades {len(x):4d} | +2,000 {100*(x.R>0).mean():5.1f}% / -2,000 {100*(x.R<0).mean():5.1f}% | mean {2000*x.R.mean():+5.0f} USD/trade | hold median {x.hold.median():4.1f} d | long {100*(x.side>0).mean():3.0f}% | worst {2000*x.R.min():+.0f} | by year {wy}")
