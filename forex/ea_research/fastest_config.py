"""Fastest-pass configuration for the live account (the trader 2026-10-11: "(original wording omitted)").
   Planning simulation (pass70 rules, start counted +560 on 2026-10-12): constant x1.2 / x1.5 / x1.8, each with and without the DA2
   index dip add-on (1% risk a signal day).   python -m forex.ea_research.fastest_config"""
import os
os.environ["DA_Z"] = "1.5"
import numpy as np
from forex.ea_research import pass70 as P
from forex.ea_research import dip_addon as DA

P.C0 = 560.0
T, bars = DA.trades(); T, D = DA.day_arrays(T, bars)
H = 120
print("config            | P(pass) by 30 Oct / 30 Nov / 22 Dec / 31 Jan (MIX; MT5-12m ; 2022-26) | breach by 31 Jan MIX | median pass day MIX")
for mult in (1.2, 1.5, 1.8):
    for add in (False, True):
        res = {}
        for pool in ("MT5", "FT"):
            S = P.series_nh(pool, mult); X = DA.combine(S, D) if add else S
            st, day = P.simulate([X] * len(P.MULTS), P.I12, H); res[pool] = (st, day)
        hz = {"30 Oct": 15, "30 Nov": 36, "22 Dec": 52, "31 Jan": 79}
        cells = []
        for h, n in hz.items():
            e = np.mean((res["MT5"][0] == 1) & (res["MT5"][1] < n)); f = np.mean((res["FT"][0] == 1) & (res["FT"][1] < n)); cells.append(f"{50*(e+f):4.1f} ({100*e:.0f};{100*f:.0f})")
        br = 50 * (np.mean((res["MT5"][0] == 2) & (res["MT5"][1] < 79)) + np.mean((res["FT"][0] == 2) & (res["FT"][1] < 79)))
        dd = np.concatenate([np.where(res[p][0] == 1, res[p][1] + 1, 999) for p in ("MT5", "FT")])
        print(f"x{mult} {'+ DA2' if add else '      '}      | " + " / ".join(cells) + f" | {br:4.1f}% | {np.median(dd):.0f} bd")
