"""Profile of 'pair x4.0 + ManualDip x4, guard 2,000' against the installed system (pair x1.5 + ManualDip, guard 1,500). the trader 2026-10-12.   python -m forex.ea_research.x4_profile"""
import os
os.environ["DA_Z"] = "1.5"
import numpy as np, pandas as pd
from forex.ea_research import combo_grid as G, pass70 as P, dip_addon as DA
from forex.ea_research.event_macro import server_s

cal = pd.read_csv("D:/finance/data_macro/event_calendar.csv"); G.EV = np.array(sorted(server_s(r.date, 8, 30) for r in cal.itertuples() if r.kind == "CPI"))
DA.RISK = 500.0; T, bb = DA.trades(); T, Dd = DA.day_arrays(T, bb); Dd = Dd * 0.75
P.C0 = 0.0
CFG = {"INSTALLED x1.5, guard 1,500": (1.5, 1.0, 1500.0), "x4.0 (+ManualDip x4), guard 2,000": (4.0, 4.0, 2000.0)}


def replay(S, H):
    V, B, Hi = (np.asarray(S[k], float) for k in ("V", "B", "Hi")); out = {"pass": 0, "breach": 0, "open": 0}
    for i in range(0, len(V) - H):
        cnt = bal = 0.0; res = "open"
        for j in range(i, i + H):
            if B[j] <= -2500 or bal + B[j] <= -8000: res = "breach"; break
            if cnt + min(Hi[j], 2000.0) >= 8100: res = "pass"; break
            cnt += min(V[j], 2000.0); bal += V[j]
            if cnt >= 8000: res = "pass"; break
        out[res] += 1
    t = sum(out.values()); return 100 * out["pass"] / t, 100 * out["breach"] / t


lines = []
for name, (m, k, g) in CFG.items():
    lines.append(f"\n##### {name}  (SDB {0.12 * m:.2f} lot, XAU5 {0.04 * m:.2f} lot, ManualDip day risk {500 * k:.0f} USD)")
    series, res = {}, {}
    for pool in ("MT5", "FT"):
        S = G.add_dip(G.pair_series(pool, m, m, g), Dd * k, g); series[pool] = S; res[pool] = P.simulate([S] * len(P.MULTS), P.I12, 90)
        V = pd.Series(np.asarray(S["V"], float), index=pd.to_datetime(np.asarray(S["days"]) * 86400, unit="s")); B = np.asarray(S["B"], float); eq = V.cumsum(); mo = V.groupby(V.index.to_period("M")).sum(); co = np.minimum(V, 2000.0).groupby(V.index.to_period("M")).sum()
        lines.append(f"{pool} pool ({'last 12 months, real ticks' if pool == 'MT5' else '2022-2026'}): mean/month raw {mo.mean():8,.0f} ({100 * mo.mean() / 1e5:5.1f}%) | counted (2,000/day cap) {co.mean():8,.0f} ({100 * co.mean() / 1e5:4.1f}%) | positive months {100 * (mo > 0).mean():3.0f}% | worst month {mo.min():8,.0f} | max drawdown {(eq.cummax() - eq).max():8,.0f}")
        lines.append(f"      worst floating day {B.min():8,.0f} | days <= -1,500: {int((B <= -1500).sum()):3d} | <= -2,000: {int((B <= -2000).sum()):3d} | <= -2,500 (MT5 broker hard breach): {int((B <= -2500).sum()):3d}")
    f = lambda n, c: 50 * sum(np.mean((res[p][0] == c) & (res[p][1] < n)) for p in res); gp = lambda p, n: 100 * np.mean((res[p][0] == 1) & (res[p][1] < n))
    lines.append("bootstrap, FRESH account, MIX of pools:   " + " | ".join(f"{n} bd: pass {f(n, 1):4.1f}% / breach {f(n, 2):4.1f}%" for n in (14, 22, 30, 44, 60)))
    lines.append("   gold-trend regime (MT5 broker pool) pass:       " + " | ".join(f"{n} bd {gp('MT5', n):4.1f}%" for n in (14, 22, 44)) + "   2022-26 regime (FT pool) pass: " + " | ".join(f"{n} bd {gp('FT', n):4.1f}%" for n in (14, 22, 44)))
    dd = np.concatenate([np.where(res[p][0] == 1, res[p][1] + 1, 9999) for p in ("MT5", "FT")]); lines.append(f"median business day of the pass (when it passes within 90 bd): {int(np.median(dd[dd < 9999])) if (dd < 9999).any() else None}; still open after 90 bd: {100 * np.mean(dd == 9999):.0f}%; ever breached within 90 bd: {50 * sum(np.mean(res[p][0] == 2) for p in res):.1f}%")
    for pool in ("MT5", "FT"):
        rp = {H: replay(series[pool], H) for H in (14, 22, 44)}; lines.append(f"REAL replay from every start day, {pool} pool: " + " | ".join(f"{H} bd pass {a:4.1f}% breach {b:4.1f}%" for H, (a, b) in rp.items()))
txt = "\n".join(lines); print(txt); open(os.path.join(os.path.dirname(__file__), "X4_PROFILE_OUTPUT.txt"), "w").write(txt)
