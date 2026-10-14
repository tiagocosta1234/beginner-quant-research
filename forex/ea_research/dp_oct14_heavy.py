"""Frontier of heavier sizing from the 2026-10-14 live state. python -m forex.ea_research.dp_oct14_heavy"""
import numpy as np
from forex.ea_research import dp_sizing as D
D.H1, D.H2, D.C0 = 12, 49, -374.30
def run(mults, lams):
    D.MULTS = mults
    pools = {"MT5": D.load("MT5"), "FT": D.load("FT")}
    sp = [pools["MT5"], pools["FT"]]
    for lam in lams:
        pol, W = D.dp(sp, (0.5, 0.5), lam)
        o = {n: D.simulate(pools, p, pol, H=D.H2) for n, p in (("12M", "MT5"), ("2022-26", "FT"))}
        m = [(o["12M"][i] + o["2022-26"][i]) / 2 * 100 for i in range(4)]
        print(f"mults {mults} lambda {lam}: pass 30 Oct {m[0]:.1f}% (12M {o['12M'][0]*100:.1f}) breach {m[1]:.1f}% | 22 Dec pass {m[2]:.1f}% breach {m[3]:.1f}%")
run((1.2, 1.8, 2.5), (0.0, 0.1, 0.3))
run((1.2, 1.8, 2.5, 3.5), (0.0, 0.3))
run((1.2, 1.8, 2.5, 3.5, 5.0), (0.0, 0.3))
D.MULTS = (1.2, 1.8, 2.5, 3.5, 5.0); pools = {"MT5": D.load("MT5"), "FT": D.load("FT")}
for a, m in ((2, 2.5), (3, 3.5)):
    o = {n: D.simulate(pools, p, a, H=D.H2) for n, p in (("12M", "MT5"), ("2022-26", "FT"))}
    print(f"constant x{m}: 30 Oct pass {(o['12M'][0]+o['2022-26'][0])*50:.1f}% breach {(o['12M'][1]+o['2022-26'][1])*50:.1f}% | day-1 only matters: 12M mean day USD at x{m}: {pools['MT5'][a]['V'].mean():.0f}, worst day {pools['MT5'][a]['V'].min():.0f}, worst in-day low {pools['MT5'][a]['B'].min():.0f}")
