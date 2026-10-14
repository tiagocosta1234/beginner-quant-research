import numpy as np
from forex.self_improving.day2k import day2k as D
A=D.load("XAUUSD"); t=A["t"]; days=D.trading_days(D.LO,D.VAL_HI); full=D.trading_days("2021-10-01",D.VAL_HI)
atr=D.atr20(A,full)[np.isin(full,days)]; sc=D.scores_for(A,full,D.atr20(A,full))[np.isin(full,days)]
def trade(i0,side,Dd,tmax):
    """walk bars from i0 until TP/SL or bar time >= tmax; returns (R, bars, gap_overshoot)"""
    E=A["ao"][i0] if side>0 else A["bo"][i0]; tp=E+side*Dd; sl=E-side*Dd
    j1=np.searchsorted(t,tmax); hi=A["bh"][i0:j1] if side>0 else A["ah"][i0:j1]; lo=A["bl"][i0:j1] if side>0 else A["al"][i0:j1]
    op=A["bo"][i0:j1] if side>0 else A["ao"][i0:j1]
    if side>0: hit_tp=hi>=tp; hit_sl=lo<=sl
    else: hit_tp=lo<=tp; hit_sl=hi>=sl
    a=np.argmax(hit_tp) if hit_tp.any() else 10**9; b=np.argmax(hit_sl) if hit_sl.any() else 10**9
    if a==b==10**9: return np.nan,j1-i0,0.0
    if b<=a:
        fill=op[b] if (side>0 and op[b]<sl) or (side<0 and op[b]>sl) else sl   # gap through the stop fills at the open
        return side*(fill-E)/Dd, b, side*(sl-fill)/Dd
    fill=tp; return 1.0,a,0.0
for ti,T in enumerate(D.TS):
    print(f"\n== entry {T//3600:02d}:{(T%3600)//60:02d}, side = direction of the last 24 h ==")
    for k in (0.1,0.15,0.2,0.25,0.3,0.4):
        out=[]
        for di,d in enumerate(days):
            s=sc[di,ti,1]
            if not np.isfinite(s) or s==0 or not np.isfinite(atr[di]): continue
            i0=np.searchsorted(t,d*86400+T+60)
            if i0>=len(t) or t[i0]!=d*86400+T+60: continue
            r,_,_=trade(i0,1 if s>0 else -1,k*atr[di],d*86400+D.EXIT); out.append(r)
        out=np.array(out); res=np.isfinite(out); r=out[res]
        print(f"  same-day, stop {k:.2f} ATR: resolved {100*res.mean():.1f}% of {len(out)} days | of resolved: win {100*(r>0).mean():.1f}% | mean {2000*np.mean(np.nan_to_num(out)):+.0f} USD/day (unresolved counted 0)")
    # hold until hit, one trade at a time
    for k in (0.4,0.7):
        res=[]; busy_until=0
        for di,d in enumerate(days):
            if d*86400+T<busy_until: continue
            s=sc[di,ti,1]
            if not np.isfinite(s) or s==0 or not np.isfinite(atr[di]): continue
            i0=np.searchsorted(t,d*86400+T+60)
            if i0>=len(t) or t[i0]!=d*86400+T+60: continue
            r,nb,ov=trade(i0,1 if s>0 else -1,k*atr[di],d*86400+T+14*86400)
            res.append((r,nb,ov)); busy_until=t[min(i0+nb,len(t)-1)]+60
        R=np.array([x[0] for x in res]); ov=np.array([x[2] for x in res]); held=np.array([x[1] for x in res])/60/24
        ok=np.isfinite(R)
        print(f"  HOLD UNTIL HIT, stop {k} ATR: {len(R)} trades in {len(days)} days | resolved within 14 days {100*ok.mean():.1f}% | win {100*(R[ok]>0).mean():.1f}% | mean {2000*R[ok].mean():+.0f} USD/trade | held median {np.median(held[ok]):.1f} days, 90th pct {np.percentile(held[ok],90):.1f} | stop gapped through on {int((ov>0).sum())} trades, worst loss {2000*R[ok].min():.0f} USD")
