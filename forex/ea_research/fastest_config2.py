"""Fastest-pass configuration after MT5 broker support's written reply of 2026-10-11 (opposite positions inside one account not prohibited;
   no strict 1%-per-trade rule, only no all-or-nothing). Same pass70 rules and start (+560 counted, 2026-10-12) as fastest_config.py;
   compares the no-hedge guard ON vs OFF, and weekend-flat XAU5.   python -m forex.ea_research.fastest_config2"""
import numpy as np
from forex.ea_research import pass70 as P
from forex.ea_research import clean_boot_lib as L

P.C0 = 560.0; H = 80; HZ = {"30 Oct": 15, "30 Nov": 36, "22 Dec": 52, "31 Jan": 79}
print("config                         | P(pass) MIX (MT5-12m;2022-26) by 30 Oct / 30 Nov / 22 Dec / 31 Jan | breach by 31 Jan MIX | median pass")
for mult in (1.2, 1.5, 1.8):
    for nm, get in (("no-hedge ON ", lambda p: P.series_nh(p, mult)), ("no-hedge OFF", lambda p: L.series(p, mult)), ("OFF + XAU5 weekend-flat", lambda p: L.series(p, mult, "FLAT_XAU5"))):
        if nm.startswith("OFF +") and mult == 1.2: continue
        res = {}
        for pool in ("MT5", "FT"):
            S = get(pool); st, day = P.simulate([S] * len(P.MULTS), P.I12, H); res[pool] = (st, day)
        cells = []
        for h, n in HZ.items():
            e = np.mean((res["MT5"][0] == 1) & (res["MT5"][1] < n)); f = np.mean((res["FT"][0] == 1) & (res["FT"][1] < n)); cells.append(f"{50*(e+f):4.1f} ({100*e:.0f};{100*f:.0f})")
        br = 50 * sum(np.mean((res[p][0] == 2) & (res[p][1] < 79)) for p in ("MT5", "FT"))
        dd = np.concatenate([np.where(res[p][0] == 1, res[p][1] + 1, 999) for p in ("MT5", "FT")])
        print(f"x{mult} {nm:24s} | " + " / ".join(cells) + f" | {br:4.1f}% | {np.median(dd):.0f} bd")
