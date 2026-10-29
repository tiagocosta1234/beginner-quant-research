"""Independent check of the pass probabilities of the INSTALLED system (pair x1.5 + ManualDip 500, guard 1,500, CPI news flat): replay the real daily series from EVERY historical start day and count passes and breaches,
then compare with the block-bootstrap numbers (pass70). Rules as eval_cycles_2026_final.py: counted profit = min(day, 2,000); pass at counted >= 8,000 or lock when counted + min(day high, 2,000) >= 8,100;
breach when the day's floating low <= -2,500 or equity <= -8,000 from the start. Start state +560 counted (this account) and 0 (fresh).   python -m forex.ea_research.replay_check"""
import os
os.environ["DA_Z"] = "1.5"
import numpy as np, pandas as pd
from forex.ea_research import combo_grid as G, pass70 as P, dip_addon as DA
from forex.ea_research.event_macro import server_s

cal = pd.read_csv("data/data_macro/event_calendar.csv"); G.EV = np.array(sorted(server_s(r.date, 8, 30) for r in cal.itertuples() if r.kind == "CPI"))
DA.RISK = 500.0; T, bb = DA.trades(); T, Dd = DA.day_arrays(T, bb); Dd = Dd * 0.75


def replay(S, c0, H):
    V, B, Hi = np.asarray(S["V"]), np.asarray(S["B"]), np.asarray(S["Hi"]); n = len(V); out = {"pass": 0, "breach": 0, "open": 0}
    for i in range(0, n - H):
        cnt = bal = c0; res = "open"
        for j in range(i, i + H):
            if B[j] <= -2500 or bal + B[j] <= -8000: res = "breach"; break
            if cnt + min(Hi[j], 2000.0) >= 8100: res = "pass"; break
            cnt += min(V[j], 2000.0); bal += V[j]
            if cnt >= 8000: res = "pass"; break
        out[res] += 1
    tot = sum(out.values()); return 100 * out["pass"] / tot, 100 * out["breach"] / tot, tot


lines = []
for c0, lab in ((560.0, "THIS ACCOUNT (+560 counted)"), (0.0, "FRESH account")):
    P.C0 = c0; lines.append(f"\n{lab}: empirical REPLAY from every real start day vs the block-bootstrap (pass70), percent pass / breach")
    for pool in ("MT5", "FT"):
        S = G.add_dip(G.pair_series(pool, 1.5, 1.5, 1500.0), Dd, 1500.0); sim = P.simulate([S] * len(P.MULTS), P.I12, 90)
        for H in (22, 44, 60):
            rp, rb, tot = replay(S, c0, H); bp = 100 * np.mean((sim[0] == 1) & (sim[1] < H)); bb_ = 100 * np.mean((sim[0] == 2) & (sim[1] < H))
            lines.append(f"  {pool} pool, {H:2d} business days ({tot} start days): replay pass {rp:5.1f}% / breach {rb:4.1f}%   |   bootstrap pass {bp:5.1f}% / breach {bb_:4.1f}%")
txt = "\n".join(lines); print(txt); open(os.path.join(os.path.dirname(__file__), "REPLAY_CHECK_OUTPUT.txt"), "w").write(txt)
