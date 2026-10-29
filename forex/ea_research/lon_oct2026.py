"""Descriptive (the trader: 'only 2026'): every London combination x scheme x risk from LON_RISK, run from the REAL account state (balance 97,708,
floor 92,000, target 108,000, 2,500 daily line, +2,000/day counted) over every 11-trading-day window starting in 2026. In-sample by construction.
   PYTHONPATH=. python forex/ea_research/lon_oct2026.py"""
import warnings
from itertools import combinations
import numpy as np, pandas as pd
from forex.ea_research.lon_combo import series
warnings.filterwarnings("ignore")
XS = np.arange(100, 1501, 100); START, DAYS = 97_708.0, 11


def windows(net, starts, worst):
    bal = np.full(len(starts), START); st = np.zeros(len(starts), int)
    for k in range(DAYS):
        i = starts + k; act = (st == 0) & (i < len(net)); ii = np.minimum(i, len(net) - 1)
        br = act & ((worst[ii] <= -2500) | (bal + worst[ii] <= 92_000)); st[br] = 2
        ok = act & ~br; bal[ok] += np.minimum(net[ii][ok], 2000.0); st[ok & (bal >= 108_000)] = 1
    return np.mean(st == 1), np.mean(st == 2)


ser = series(); syms = sorted(ser)
sd = {m: ser[m][(ser[m].index >= "2022-01-01") & (ser[m].index <= "2024-12-31")].std() for m in syms}
rows = []
for k in range(1, len(syms) + 1):
    for combo in combinations(syms, k):
        df = pd.concat({m: ser[m] for m in combo}, axis=1).sort_index(); df = df[df.index >= "2026-01-01"].reindex(pd.bdate_range("2026-01-01", "2026-10-02"))
        for scheme in ("FLAT", "EQRISK"):
            if scheme == "EQRISK" and k == 1: continue
            w = np.ones(k) if scheme == "FLAT" else np.array([1 / sd[m] for m in combo]); w = w / w.mean()
            R = df.to_numpy() * w; net = np.nansum(R, axis=1); neg = np.nansum(np.minimum(R, 0), axis=1)
            starts = np.arange(0, len(net) - DAYS + 1)
            for X in XS:
                po, bo = windows(net * X, starts, net * X); pp, bp = windows(net * X, starts, neg * X)
                rows.append(dict(combo="+".join(combo), k=k, scheme=scheme, X=int(X), pass_opt=po, breach_opt=bo, pass_pess=pp, breach_pess=bp, windows=len(starts)))
R = pd.DataFrame(rows); R.to_csv("data/si_ledgers/LON_OCT2026.csv", index=False)
pd.set_option("display.width", 250)
print(f"{len(R)} configurations, {R.windows.iloc[0]} eleven-day windows in 2026 each (in-sample)\n")
print("Best pass with breach <= 10% (optimistic daily line):")
print(R[R.breach_opt <= 0.10].sort_values("pass_opt", ascending=False).head(8).round(3).to_string(index=False))
print("\nBest pass at ANY breach:")
print(R.sort_values("pass_opt", ascending=False).head(5).round(3).to_string(index=False))
print("\nBest single symbol (breach <= 10%):")
print(R[(R.k == 1) & (R.breach_opt <= 0.10)].sort_values("pass_opt", ascending=False).head(3).round(3).to_string(index=False))
