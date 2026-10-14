"""dp_oct14 restricted to multipliers <= x2.5 (no x3.5/x5.0: weekend-gap risk, margin and MT5 broker comfort). python -m forex.ea_research.dp_oct14_capped"""
import numpy as np
from forex.ea_research import dp_sizing as D
D.MULTS = (1.2, 1.8, 2.5); D.H1, D.H2, D.C0 = 12, 49, -374.30
pools = {"MT5": D.load("MT5"), "FT": D.load("FT")}
def ev(pol):
    o = {n: D.simulate(pools, p, pol, H=D.H2) for n, p in (("12M", "MT5"), ("2022-26", "FT"))}
    m = [(o["12M"][i] + o["2022-26"][i]) / 2 * 100 for i in range(4)]
    return f"30 Oct pass {m[0]:5.1f}% (12M {o['12M'][0]*100:4.1f} / 22-26 {o['2022-26'][0]*100:4.1f}) breach {m[1]:4.1f}% | 22 Dec pass {m[2]:5.1f}% breach {m[3]:4.1f}%"
sp = [pools["MT5"], pools["FT"]]
cols = (-2000, -1500, -1000, -500, 0, 1000, 2000, 3000, 4000, 5000, 6000, 7000)
for lam in (0.3, 1.0):
    pol, W = D.dp(sp, (0.5, 0.5), lam)
    print(f"\nCAPPED DP lambda {lam}: {ev(pol)}")
    print("            " + " ".join(f"{c:>6d}" for c in cols))
    for j in range(D.H1):
        print(f"day {j+1:2d}/12   " + " ".join(f"{('x'+str(D.MULTS[pol[j][int(round((c - D.GRID[0]) / D.STEP))]])):>6s}" for c in cols))
    np.save(f"D:/finance/tmp/dp_oct14_capped_lam{lam}.npy", pol)
