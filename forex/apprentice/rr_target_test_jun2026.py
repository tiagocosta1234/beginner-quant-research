import sys, numpy as np, pandas as pd
sys.path.insert(0, r"D:\finance\beginner-quant-research\mt5\apprentice")
import desk as D
d = D.raw(); d = d[(d["lis"] >= "2026-04-28") & (d["lis"] < "2026-06-27")].reset_index(drop=True)
# replay market entries (date, hh:mm, side, entry, stop) from FXR_SESSION_LOG / logs
T = [("2026-04-29","08:00","S",4584.67,4593.48),("2026-05-01","08:00","S",4594.93,4610.61),("2026-05-05","08:00","S",4548.34,4558.79),
("2026-05-06","08:00","L",4669.46,4655.92),("2026-05-07","10:15","L",4734.32,4718.26),("2026-05-11","08:00","L",4678.57,4651.95),
("2026-05-12","08:00","S",4697.09,4713.13),("2026-05-13","10:45","L",4694.11,4680.64),("2026-05-22","10:00","S",4521.84,4534.81),
("2026-05-27","08:00","S",4485.17,4502.93),("2026-05-28","08:00","S",4383.85,4396.03),("2026-05-29","08:15","L",4516.32,4502.59),
("2026-06-01","08:00","S",4501.61,4525.00),("2026-06-02","08:00","L",4535.95,4514.93),("2026-06-03","08:00","S",4463.20,4479.89),
("2026-06-04","08:00","S",4467.87,4488.88),("2026-06-05","08:00","S",4452.95,4463.42),("2026-06-08","08:00","L",4300.16,4260.88),
("2026-06-09","08:00","S",4330.73,4355.84),("2026-06-10","08:15","L",4200.48,4166.58),("2026-06-11","08:00","L",4094.49,4052.98),
("2026-06-12","08:00","L",4184.12,4163.47),("2026-06-12","11:45","L",4215.48,4184.35),("2026-06-15","08:00","S",4308.13,4343.95),
("2026-06-17","08:00","L",4331.82,4309.12),("2026-06-18","08:00","L",4306.66,4259.29),("2026-06-23","08:00","S",4114.49,4150.36)]
RS=[1.0,1.5,2.0,3.0]
def run(day,hm,side,e,s,R,exit_h=21):
    t0=pd.Timestamp(day+" "+hm); x=d[(d["lis"]>=t0)&(d["lis"]<pd.Timestamp(day)+pd.Timedelta(hours=exit_h))]
    if len(x)<30: return None
    off=x["mo"].iloc[0]-e; L=side=="L"; risk=abs(e-s)
    stp=(s+off); tgt=(e+off)+(R*risk if L else -R*risk)
    for q in x.itertuples():
        hit_s = q.ml<=stp if L else q.mh>=stp; hit_t = q.mh>=tgt if L else q.ml<=tgt
        if hit_s: return -1.0
        if hit_t: return R
    last=x["mc"].iloc[-1]; return ((last-(e+off)) if L else ((e+off)-last))/risk
rows=[]
for t in T:
    r=[run(*t,R) for R in RS]; rows.append(r)
a=np.array([[np.nan if v is None else v for v in r] for r in rows],float)
for j,R in enumerate(RS):
    c=a[:,j]; c=c[~np.isnan(c)]
    print("target %.1fR: n %d  wins %d  meanR %+.3f  totalR %+.1f"%(R,len(c),(c>=R-1e-9).sum(),c.mean(),c.sum()))
