"""Round 317 (single hypothesis, descriptive; first run happens after this file is written, no dry-run mode).

Open lead from CURRENT_STATE: the dollar fade was never tested. Dollar proxy = 6E=F (euro future, inverted).
H1: after a day when 6E=F moves >= 1 sigma (60-day) in either direction, ES=F's NEXT close-to-close return
    has the opposite sign to 6E's move scaled by... simplest form: trade ES long after a strong euro-DOWN day
    (dollar up) is the fade-of-dollar? We pre-fix: signal s = -sign(6E return) * (|6E z| >= 1);
    position in ES next day = s (long after euro up, short after euro down is the CO-MOVEMENT; its negation is the fade).
    Both reported; hypothesis tested is the FADE (position = -sign(6E z)), 5 bp round-trip cost.
Split: IS < 2013-01-01, OOS >= 2013-01-01. Statistic: mean net bp per trade, date bootstrap 5000, seed 317.
Candidate: IS P(mean>0)>=0.95 and OOS mean>0 and OOS P>=0.95. Otherwise no edge. Ledger k unchanged.
"""
import numpy as np, pandas as pd
D="../data/daily/"
ld=lambda n: pd.read_csv(f"{D}{n}_yahoo_daily.csv",parse_dates=["date"]).set_index("date").close
e,s=ld("6E=F"),ld("ES=F"); df=pd.concat([e,s],axis=1,keys=["e","s"],sort=True).dropna()
re_=np.log(df.e).diff(); z=re_/re_.rolling(60).std().shift(1)
nxt=np.log(df.s.shift(-1)/df.s)*1e4
sig=np.sign(z).where(z.abs()>=1,0)
rng=np.random.default_rng(317)
for name,pos in [("co-movement",sig),("FADE (tested)",-sig)]:
    net=(pos*nxt-5*(pos!=0)).where(pos!=0).dropna()
    for lab,x in [("IS",net[net.index<"2013-01-01"]),("OOS",net[net.index>="2013-01-01"])]:
        b=np.array([x.values[rng.integers(0,len(x),len(x))].mean() for _ in range(5000)])
        print(f"{name:14} {lab:3} n={len(x):4d} mean={x.mean():6.2f}bp P(>0)={(b>0).mean():.3f}")
