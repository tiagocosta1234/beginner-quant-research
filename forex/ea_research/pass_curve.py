"""P(pass the MT5 broker test) as a function of the DATE, live system (pair x1.5 + ManualDip 500, guard 1,500, CPI news-flat), and what extra size buys by 30 Nov.
the trader 2026-10-12: "(original wording omitted)". MT5 broker has no time limit (mt5_ANSWERS_2026-10-07.md), so the 60% bar is a question
of WHEN. Same pass70 rules and +560 start as final_system_stats.py; MIX = 50/50 of the MT5 12-month pool and the FT 2022-26 pool.   python -m forex.ea_research.pass_curve"""
import os
os.environ["DA_Z"] = "1.5"
import numpy as np, pandas as pd
from forex.ea_research import combo_grid as G, pass70 as P, dip_addon as DA
from forex.ea_research.event_macro import server_s

cal = pd.read_csv("data/data_macro/event_calendar.csv")
G.EV = np.array(sorted(server_s(r.date, 8, 30) for r in cal.itertuples() if r.kind == "CPI"))
P.C0 = 560.0; GUARD = 1500.0; DA.RISK = 500.0
T, bb = DA.trades(); T, Dd = DA.day_arrays(T, bb); Dd = Dd * 0.75
out = []


def run(mult):
    res = {}
    for pool in ("MT5", "FT"):
        S = G.add_dip(G.pair_series(pool, mult, mult, GUARD), Dd, GUARD); res[pool] = P.simulate([S] * len(P.MULTS), P.I12, 160)
    return res


def curve(res, n): return 50 * sum(np.mean((res[p][0] == 1) & (res[p][1] < n)) for p in res), 50 * sum(np.mean((res[p][0] == 2) & (res[p][1] < n)) for p in res)


R = run(1.5)
print("LIVE x1.5: P(pass) by date (MIX), breach so far")
for lab, n in (("30 Nov", 36), ("7 Dec", 41), ("15 Dec", 47), ("22 Dec", 52), ("31 Dec", 58), ("15 Jan", 68), ("31 Jan", 79), ("28 Feb", 99), ("31 Mar", 120), ("end May", 160)):
    p, b = curve(R, n); print(f"  by {lab:8s} (bd {n:3d}): pass {p:5.1f}%   breach {b:4.1f}%"); out.append(f"x1.5 {lab}: pass {p:.1f}% breach {b:.1f}%")
first = {thr: next((n for n in range(20, 161) if curve(R, n)[0] >= thr), None) for thr in (60, 70, 80)}
for thr, n in first.items(): print(f"  first business day with MIX >= {thr}%: {n} -> {np.busday_offset('2026-10-12', n - 1, roll='forward') if n else 'not within 160 bd'}"); out.append(f"first {thr}%: bd {n}")
print("\nWhat more size buys by 30 Nov (same guard 1,500):")
for m in (1.5, 1.8, 2.2, 2.6):
    r = R if m == 1.5 else run(m); p, b = curve(r, 36); p2, b2 = curve(r, 52); print(f"  x{m}: by 30 Nov pass {p:5.1f}% breach {b:4.1f}% | by 22 Dec pass {p2:5.1f}% breach {b2:4.1f}%"); out.append(f"x{m}: 30Nov {p:.1f}/{b:.1f} 22Dec {p2:.1f}/{b2:.1f}")
open(os.path.join(os.path.dirname(__file__), "PASS_CURVE_OUTPUT.txt"), "w").write("\n".join(out))
