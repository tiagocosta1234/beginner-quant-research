import numpy as np, pandas as pd
from forex.self_improving.day2k import day2k as D
A=D.load("XAUUSD"); t=A["t"]; days=D.trading_days(D.LO,D.VAL_HI); full=D.trading_days("2021-10-01",D.VAL_HI)
atr_f=D.atr20(A,full); m=np.isin(full,days); atr=atr_f[m]; sc=D.scores_for(A,full,atr_f)[m]
T=16*3600+35*60; TI=1; K=0.4
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
tr=[]; busy=0; lossday=-1
for di,d in enumerate(days):
    if d*86400+T<busy or d==lossday: continue
    s=sc[di,TI,1]
    if not np.isfinite(s) or s==0 or not np.isfinite(atr[di]): continue
    i0=np.searchsorted(t,d*86400+T+60)
    if i0>=len(t) or t[i0]!=d*86400+T+60: continue
    side=1 if s>0 else -1; r,ix=trade(i0,side,K*atr[di],d*86400+T+14*86400)
    if not np.isfinite(r): continue
    xt=int(t[ix]); tr.append(dict(entry=d, entry_t=d*86400+T+60, exit_t=xt, exit_day=xt//86400, side=side, R=r, hold_h=(xt-(d*86400+T+60))/3600))
    busy=xt+60
    if r<0: lossday=xt//86400
tr=pd.DataFrame(tr)
def report(risk):
    x=tr.copy(); x["usd"]=x.R*risk
    daily=pd.Series(0.0,index=days); g=x.groupby("exit_day").usd.sum(); daily.loc[g.index.intersection(daily.index)]+=g[g.index.intersection(daily.index)]
    V=daily.to_numpy(); n=len(V)
    print(f"\n######## RISK {risk:.0f} USD per trade (gold, 16:35 server, direction of last 24 h, stop = target = 0.4 x ATR20, hold until hit) ########")
    w=x[x.R>0]; l=x[x.R<0]
    print(f"TRADES {len(x)} in {n} trading days (2021-12-01..2025-12-31) | wins {len(w)} ({100*len(w)/len(x):.1f}%) losses {len(l)} | long {100*(x.side>0).mean():.0f}%")
    print(f"  avg win {w.usd.mean():+.0f}  avg loss {l.usd.mean():+.0f}  expectancy {x.usd.mean():+.0f} USD/trade  profit factor {w.usd.sum()/-l.usd.sum():.2f}  total {x.usd.sum():+,.0f}")
    print(f"  losses worse than -{risk:.0f} (gap through stop): {int((x.R<-1.0001).sum())}, worst trade {x.usd.min():+.0f} | hold: median {x.hold_h.median():.1f} h, 90th pct {x.hold_h.quantile(.9):.1f} h, max {x.hold_h.max():.0f} h | trades held over a weekend {int(((x.exit_t//86400)-(x.entry)>=3).sum())}")
    st=(np.sign(x.R).to_numpy()); runs=[]; c=0; last=0
    for v in st:
        c = c+1 if v==last else 1; last=v; runs.append((v,c))
    print(f"  longest losing streak {max([c for v,c in runs if v<0])}, longest winning streak {max([c for v,c in runs if v>0])}")
    print(f"DAYS: +{risk:.0f}-or-more days {int((V>=risk*0.999).sum())} ({100*(V>=risk*0.999).mean():.1f}%) | -{risk:.0f}-or-worse days {int((V<=-risk*0.999).sum())} ({100*(V<=-risk*0.999).mean():.1f}%) | zero days {int((V==0).sum())} ({100*(V==0).mean():.1f}%) | other {int(((V!=0)&(abs(V)<risk*0.999)).sum())} | days below -2,500 {int((V<=-2500).sum())} | best day {V.max():+.0f} worst day {V.min():+.0f}")
    eq=np.cumsum(V); dd=eq-np.maximum.accumulate(eq); print(f"  equity over the period {eq[-1]:+,.0f}, max drawdown {dd.min():,.0f}")
    yr=pd.Series(V,index=pd.to_datetime(days.astype('datetime64[D]'))).groupby(lambda q:q.year).sum(); print("  by year:", {k:f"{v:+,.0f}" for k,v in yr.items()})
    # rolling-start MT5 broker cycles
    rows=[]
    for s in range(n):
        cnt=0.0; low=0.0; out="open"; end=n-1; nt=0
        for j in range(s,n):
            if V[j]<=-2500: out="BREACH-day"; end=j; break
            cnt+= min(V[j],2000.0) if V[j]>0 else V[j]; low=min(low,cnt)
            if cnt<=-8000: out="BREACH-floor"; end=j; break
            if cnt>=8000: out="PASS"; end=j; break
        rows.append(dict(start=str(np.datetime64(int(days[s]),'D')),out=out,bd=end-s+1,low=low,trades=int(((x.exit_day>=days[s])&(x.exit_day<=days[end])).sum())))
    c=pd.DataFrame(rows); fin=c[c.out!="open"]; p=c[c.out=="PASS"]
    print(f"EVALUATION CYCLES (one test started on every trading day, run on the real sequence): {len(c)} starts, finished {len(fin)}")
    print(f"  PASS {len(p)} ({100*len(p)/len(fin):.1f}%) | BREACH by daily -2,500 {int((c.out=='BREACH-day').sum())} | BREACH by -8,000 floor {int((c.out=='BREACH-floor').sum())} | still open {int((c.out=='open').sum())}")
    print(f"  business days to pass: median {p.bd.median():.0f}, mean {p.bd.mean():.1f}, 10th pct {p.bd.quantile(.1):.0f}, 90th pct {p.bd.quantile(.9):.0f}, fastest {p.bd.min()}, slowest {p.bd.max()} | trades per pass: median {p.trades.median():.0f}")
    print(f"  deepest point before a pass: median {p.low.median():,.0f}, worst {p.low.min():,.0f} | breaches after median {c[c.out.str.startswith('BREACH')].bd.median():.0f} business days")
    c["mo"]=c.start.str[:7]; g=c.groupby(c.mo.str[:4]).apply(lambda q: f"pass {int((q.out=='PASS').sum())}/{int((q.out!='open').sum())} median {q[q.out=='PASS'].bd.median():.0f} bd")
    print("  by start year:", g.to_dict())
    # bootstrap of the daily series (5-day blocks), P(pass) by a date
    rng=np.random.default_rng(1); P=20000; H=60; res=np.zeros(P,int); dday=np.full(P,999)
    for i in range(P):
        cnt=0.0; j=0
        while j<H:
            st0=rng.integers(0,n-5)
            for v in V[st0:st0+5]:
                if j>=H: break
                if v<=-2500: res[i]=2; dday[i]=j; j=H; break
                cnt+= min(v,2000.0) if v>0 else v
                if cnt<=-8000: res[i]=2; dday[i]=j; j=H; break
                if cnt>=8000: res[i]=1; dday[i]=j; j=H; break
                j+=1
    for h,lab in ((12,"30 Oct"),(33,"30 Nov"),(49,"22 Dec"),(60,"60 bd")):
        print(f"  bootstrap P(pass) by {lab} ({h} bd): {100*np.mean((res==1)&(dday<h)):.1f}%  breach by then {100*np.mean((res==2)&(dday<h)):.1f}%")
    c.to_csv(f"D:/finance/si_ledgers/GOLD_CYCLES_risk{int(risk)}.csv",index=False); x.to_csv(f"D:/finance/si_ledgers/GOLD_TRADES_risk{int(risk)}.csv",index=False)
for rk in (2000.0,900.0): report(rk)
