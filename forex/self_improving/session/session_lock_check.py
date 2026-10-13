import numpy as np
from forex.self_improving.session import session_lab as S, session_passrate as PR
tm,bc,sp=S.bars; d=np.abs(np.diff(bc)); ok=(np.diff(tm)==60)&((tm[1:]%86400)//3600>=1)&((tm[1:]%86400)//3600<23)
print("1-min |move| in $: p99", round(np.percentile(d[ok],99),2),"p99.9",round(np.percentile(d[ok],99.9),2),"max",round(d[ok].max(),2))
J=float(np.percentile(d[ok],99.9))
def run(T,L,m0,k,r,h,lock):
    S.LOCKJ=J if lock else None; df=S.run(*T,L,m0,k,r,h)
    st,day=PR.boot(df); up=df[df.res==1].pnl-2000; dn=-(df[df.res==-1].pnl+L)
    return dict(up=100*(df.res==1).mean(),dn=100*(df.res==-1).mean(),unres=100*(df.res==0).mean(),p44=100*np.mean((st==1)&(day<44)),p120=100*np.mean((st==1)&(day<120)),breach=100*np.mean(st==2),ov_up_max=up.max() if len(up) else 0,ov_dn_mean=dn.mean() if len(dn) else 0,ov_dn_max=dn.max() if len(dn) else 0,worst=df.low.min())
for nm,T in (("MT5 12m",S.load("MT5")),("FT 2025-26",S.load("FT","2025-01-01","2026-09-30"))):
    for tag,args in (("D",(1500.,3.,1.,0.,3.)),("A",(1000.,4.,0.,1.,0.))):
        for lock in (False,True):
            o=run(T,*args,lock); print(f"{nm:10s} {tag} lock-cap {'ON ' if lock else 'off'}: +2000 {o['up']:.1f}% -L {o['dn']:.1f}% unres {o['unres']:.0f}% | P(pass<=44bd) {o['p44']:.1f}% <=120 {o['p120']:.1f}% breach {o['breach']:.1f}% | overshoot loss mean {o['ov_dn_mean']:.0f} max {o['ov_dn_max']:.0f}, gain max {o['ov_up_max']:.0f} | worst day low {o['worst']:.0f}")
