"""EC: does the installed system's own recent P&L predict the pass rate of an account started now? (PREREG_OUTSIDE_BOX.md)   python -m mt5broker.ea_research.equity_start"""
import os
os.environ["DA_Z"] = "1.5"
import numpy as np, pandas as pd
from mt5broker.ea_research import combo_grid as G, dip_addon as DA
from mt5broker.ea_research.event_macro import server_s

cal = pd.read_csv("D:/finance/data_macro/event_calendar.csv"); G.EV = np.array(sorted(server_s(r.date, 8, 30) for r in cal.itertuples() if r.kind == "CPI"))
DA.RISK = 500.0; T, bb = DA.trades(); T, Dd = DA.day_arrays(T, bb); Dd = Dd * 0.75


def run_from(V, B, Hi, i, H):
    cnt = bal = 0.0
    for j in range(i, i + H):
        if B[j] <= -2500 or bal + B[j] <= -8000: return "breach"
        if cnt + min(Hi[j], 2000.0) >= 8100: return "pass"
        cnt += min(V[j], 2000.0); bal += V[j]
        if cnt >= 8000: return "pass"
    return "open"


lines = []
for pool in ("FT", "MT5"):
    S = G.add_dip(G.pair_series(pool, 1.5, 1.5, 1500.0), Dd, 1500.0); V, B, Hi = (np.asarray(S[k], float) for k in ("V", "B", "Hi")); n = len(V); trail = np.array([V[max(0, i - 40):i].sum() if i >= 40 else np.nan for i in range(n)])
    for H in (22, 44):
        rows = []
        for i in range(40, n - H): rows.append((trail[i] > 0, run_from(V, B, Hi, i, H)))
        R = pd.DataFrame(rows, columns=["on", "res"])
        for lab, g in (("ON  (trailing 40d P&L > 0)", R[R.on]), ("OFF (trailing 40d P&L <= 0)", R[~R.on])):
            lines.append(f"{pool} pool, {H:2d} bd, {lab}: start days {len(g):4d} | pass {100 * (g.res == 'pass').mean():5.1f}% | breach {100 * (g.res == 'breach').mean():4.1f}%")
        on, off = R[R.on], R[~R.on]; lines.append(f"   ratio ON/OFF pass: {((on.res == 'pass').mean() / max((off.res == 'pass').mean(), 1e-9)):.2f}\n")
txt = "\n".join(lines); print(txt); open(os.path.join(os.path.dirname(__file__), "EQUITY_START_OUTPUT.txt"), "w").write(txt)
