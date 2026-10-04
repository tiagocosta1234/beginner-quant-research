"""Round 316 (pre-registered, single hypothesis): does a VIX >= 25 filter improve the dip-reversal rule?

Rule (Rounds 285-288): long after a 3-day log fall >= 2 x (60-day daily sigma x sqrt 3), entry at the close,
exit next close, Monday-Thursday entries, 5 bp round-trip cost.
Signal days pooled over ^GSPC (1990+), ES=F, NQ=F, YM=F, RTY=F, ^GDAXI (2000+; VIX from 1990).
H1 (only hypothesis): mean net(VIX>=25) - mean net(VIX<25) > 0.
Split: IS = signal dates < 2013-01-01, OOS >= 2013-01-01 (OOS not looked at before this file's commit; the Round 316
descriptive S&P look used 1990-2005 / 2006-2026 and is disclosed).
Statistic: difference of means, date-clustered bootstrap (resample signal dates, 5000 draws, seed 316).
Candidate rule: OOS diff > 0 with bootstrap P(diff>0) >= 0.95 AND IS diff > 0. Otherwise no edge.
DISCLOSURE: the script has no dry-run mode; the first execution happened before this file was committed, so the
commit is not a true pre-registration (rules were fixed before that run and not changed after it).
Descriptive only: ledger k is not changed (one hypothesis, reported either way).
"""
import numpy as np, pandas as pd
D = "../data/daily/"
def load(n): return pd.read_csv(f"{D}{n}_yahoo_daily.csv", parse_dates=["date"]).set_index("date").close
vix = load("^VIX")
rows = []
for n, start in [("^GSPC","1990"),("ES=F","2000"),("NQ=F","2000"),("YM=F","2002"),("RTY=F","2017"),("^GDAXI","1990")]:
    c = load(n); c = c[c.index >= start]
    r = np.log(c).diff(); sig = r.rolling(60).std().shift(1)
    z = np.log(c/c.shift(3))/(sig*np.sqrt(3))
    net = np.log(c.shift(-1)/c)*1e4 - 5
    m = (z <= -2) & (c.index.dayofweek <= 3)
    d = pd.DataFrame({"net": net[m], "vix": vix.reindex(c.index).ffill()[m]}).dropna()
    d["inst"] = n; rows.append(d)
df = pd.concat(rows).sort_index()
rng = np.random.default_rng(316)
def diff(x): 
    a, b = x[x.vix >= 25].net, x[x.vix < 25].net
    return a.mean() - b.mean(), len(a), len(b)
out = {}
for lab, x in [("IS", df[df.index < "2013-01-01"]), ("OOS", df[df.index >= "2013-01-01"])]:
    dates = x.index.unique(); g = {d: x.loc[[d]] for d in dates}
    est, na, nb = diff(x); bs = []
    for _ in range(5000):
        s = pd.concat([g[d] for d in rng.choice(dates, len(dates))])
        if (s.vix >= 25).any() and (s.vix < 25).any(): bs.append(diff(s)[0])
    bs = np.array(bs); out[lab] = (est, na, nb, (bs > 0).mean())
    print(f"{lab}: diff={est:6.1f} bp  n(hi)={na} n(lo)={nb}  P(diff>0)={(bs>0).mean():.3f}")
print("CANDIDATE" if out["IS"][0] > 0 and out["OOS"][0] > 0 and out["OOS"][3] >= .95 else "no edge")
