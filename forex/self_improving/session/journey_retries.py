import numpy as np
from forex.ea_research import pass70 as P
from forex.self_improving.session import faster_than_live as F, session_sdbrunner as R
rng=np.random.default_rng(1); tr,lo,hi=R.load_flag("MT5")
for nm,(m,Lc,Pc) in (("live x1.5 L1500",(1.5,1500.,1e9)),("x2.0 L2000",(2.0,2000.,1e9)),("x2.0 L1500",(2.0,1500.,1e9)),("x1.5 L2000",(1.5,2000.,1e9))):
    S=F.series(tr,lo,hi,m,Pc,Lc); st,dy=P.simulate([S]*len(P.MULTS),P.I12,250,paths=40000)
    st=np.asarray(st); dy=np.asarray(dy)+1; n=len(st); tot=[]; att=[]
    for _ in range(20000):
        t=0; a=0
        while True:
            i=rng.integers(0,n); a+=1
            if st[i]==1: t+=dy[i]; break
            t+= dy[i] if st[i]==2 else 250
            if t>400: t=np.nan; break
        tot.append(t); att.append(a)
    tot=np.array(tot); att=np.array(att)
    print(f"{nm:16s}: 1st attempt pass {100*np.mean(st==1):.1f}% breach {100*np.mean(st==2):.1f}% | journey to a pass: median {np.nanmedian(tot):.0f} bd, mean {np.nanmean(tot):.0f}, P(pass within 44 bd incl. retries) {100*np.nanmean(tot<=44):.0f}%, within 60 {100*np.nanmean(tot<=60):.0f}% | attempts mean {att.mean():.2f}, fees (451/attempt) mean {451*att.mean():.0f}")
