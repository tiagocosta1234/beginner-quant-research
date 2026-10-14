"""Heavier card: multipliers x1.2/1.8/2.5/3.5, lambda 0 (no breach penalty). python -m forex.ea_research.dp_oct14_x35"""
import numpy as np
from forex.ea_research import dp_sizing as D
D.MULTS = (1.2, 1.8, 2.5, 3.5); D.H1, D.H2, D.C0 = 12, 49, -374.30
pools = {"MT5": D.load("MT5"), "FT": D.load("FT")}; sp = [pools["MT5"], pools["FT"]]
pol, W = D.dp(sp, (0.5, 0.5), 0.0)
o = {n: D.simulate(pools, p, pol, H=D.H2) for n, p in (("12M", "MT5"), ("2022-26", "FT"))}
m = [(o["12M"][i] + o["2022-26"][i]) / 2 * 100 for i in range(4)]
print(f"x3.5-capped DP lambda 0: pass 30 Oct {m[0]:.1f}% (12M {o['12M'][0]*100:.1f} / 22-26 {o['2022-26'][0]*100:.1f}) breach {m[1]:.1f}% | 22 Dec pass {m[2]:.1f}% breach {m[3]:.1f}%")
cols = (-2000, -1500, -1000, -500, 0, 1000, 2000, 3000, 4000, 5000, 6000, 7000)
print("counted:    " + " ".join(f"{c:>5d}" for c in cols))
for j in range(D.H1):
    print(f"day {j+1:2d}      " + " ".join(f"{('x'+str(D.MULTS[pol[j][int(round((c - D.GRID[0]) / D.STEP))]])):>5s}" for c in cols))
