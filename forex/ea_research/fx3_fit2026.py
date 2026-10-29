"""FX3-FIT2026: search simple hourly rules on EURUSD/GBPUSD/USDJPY using 2026 as the DEVELOPMENT window, then validate the picks on 2022-25 (reverse out-of-sample).
Rule grid: pair x server hour h (1..21) x lookback L in (1,2,4) h x {continuation, reversal}; enter minute 5 of hour h (ask/bid), exit minute 5 of h+1; slippage 0.1 bp/side."""
import numpy as np, pandas as pd
from pathlib import Path
D = Path("forex/data_mt5"); out = []
def hourly(m):
    d = pd.read_parquet(D / f"{m}_M1_rates.parquet", columns=["t", "bo", "ao"]); d = d[(d.t % 3600) == 300]
    d = d[(d.bo > 0) & (d.ao >= d.bo)]; d["hb"] = d.t // 3600
    return d.set_index("hb")
rows = []
for m in ("EURUSD", "GBPUSD", "USDJPY"):
    h = hourly(m); idx = h.index.to_numpy(); mid = ((h.bo + h.ao) / 2)
    for hr in range(1, 22):
        for L in (1, 2, 4):
            e = idx[(idx % 24 == hr)]
            for hb in e:
                if (hb in h.index) and (hb + 1 in h.index) and (hb - L in h.index):
                    past = np.log(mid[hb] / mid[hb - L])
                    if past == 0: continue
                    lb = (h.bo[hb + 1] / h.ao[hb] - 1) * 1e4 - 0.2; sb = (h.bo[hb] / h.ao[hb + 1] - 1) * 1e4 - 0.2
                    rows.append((m, hr, L, hb, np.sign(past), lb, sb))
R = pd.DataFrame(rows, columns=["m", "hr", "L", "hb", "s", "lb", "sb"]); R["T"] = pd.to_datetime(R.hb * 3600, unit="s")
R = R[R["T"].dt.dayofweek < 5]
res = []
for (m, hr, L), g in R.groupby(["m", "hr", "L"]):
    for name, sgn in (("cont", 1), ("rev", -1)):
        x = np.where(g.s * sgn > 0, g.lb, g.sb); g2 = g.assign(x=x)
        a = g2[g2["T"] >= "2026-01-01"].x; b = g2[g2["T"] < "2026-01-01"].x
        if len(a) < 100 or len(b) < 500: continue
        res.append((m, hr, L, name, len(a), a.mean(), a.mean() / (a.std() / np.sqrt(len(a))), len(b), b.mean(), b.mean() / (b.std() / np.sqrt(len(b)))))
S = pd.DataFrame(res, columns=["pair", "hour", "L", "rule", "n26", "net26", "t26", "n2225", "net2225", "t2225"])
print("rules searched:", len(S))
top = S.sort_values("t26", ascending=False).head(10)
print("TOP 10 BY 2026 (developed on 2026):"); print(top.round(2).to_string(index=False))
print("\nmean of the top-10: 2026 net %.2f bp | same rules on 2022-25 net %.2f bp (t of mean-of-picks not significant if ~0)" % (top.net26.mean(), top.net2225.mean()))
print("all rules: mean 2022-25 net %.2f bp; share of top-50-by-2026 with positive 2022-25 net: %.2f" % (S.net2225.mean(), (S.sort_values("t26", ascending=False).head(50).net2225 > 0).mean()))
# noise ceiling: how good does the best of this many rules look in 2026 if sides were random? (permute side labels across days)
rng = np.random.default_rng(1); mx = []
for _ in range(30):
    best = -9
    for (m, hr, L), g in R.groupby(["m", "hr", "L"]):
        a = g[g["T"] >= "2026-01-01"]
        if len(a) < 100: continue
        s = rng.permutation(a.s.to_numpy())
        for sg in (1, -1):
            x = np.where(s * sg > 0, a.lb, a.sb); best = max(best, x.mean() / (x.std() / np.sqrt(len(x))))
    mx.append(best)
print("pure-noise best-of-%d t in 2026: median %.2f, 95th %.2f" % (len(S), np.median(mx), np.percentile(mx, 95)))
S.to_csv("data/tmp/fx3_fit2026.csv", index=False)
