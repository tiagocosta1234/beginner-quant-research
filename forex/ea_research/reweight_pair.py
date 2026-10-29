"""the trader 2026-10-11: "(original wording omitted)" Re-weight SDB vs XAU5 under the v5 rules
(guard day stop 1,500, news flat, no-hedge off, pass70 rules, start +560). Planning simulation.   python -m forex.ea_research.reweight_pair"""
import numpy as np, pandas as pd
from forex.ea_research import clean_boot_lib as L, pass70 as P
from forex.ea_research.daystop_under_2000 import news_flat
from forex.ea_research.event_macro import server_s
from forex.ea_batch.mt5_mc_config import CH

P.C0 = 560.0; HZ = {"30 Nov": 36, "22 Dec": 52, "31 Jan": 79}
cal = pd.read_csv("data/data_macro/event_calendar.csv")
EV = np.array(sorted(server_s(r.date, 8, 30) if r.kind in ("CPI", "NFP") else server_s(r.date, 14, 0) for r in cal.itertuples() if r.kind in ("CPI", "NFP", "FOMC")))
bars = L.bars(); print("SDB lot | XAU5 lot || P(pass) MIX 30 Nov / 22 Dec / 31 Jan | breach | worst day MT5 / FT | days < -1,900 | mean/day MT5 / FT")
for ms, mx in ((1.5, 1.5), (1.0, 2.0), (1.0, 2.5), (0.5, 2.5), (0.5, 3.0), (0.0, 3.0), (0.0, 4.0), (1.0, 3.0), (1.5, 2.0)):
    res, info = {}, []
    for pool in ("MT5", "FT"):
        src, a, b = L.POOLS[pool]; lo, hi = L.day(a), L.day(b); parts = []
        if ms > 0: parts.append(L.ea_trades(src, "sdb", CH["sdb"] * ms, lo))
        parts.append(L.ea_trades(src, "xau5", CH["xau5"] * mx, lo))
        tr = parts[0] if len(parts) == 1 else L.merge(*parts); tr = news_flat(tr, EV, bars)
        r = L.C.simulate(bars, tr, lo, hi, None, 1500.0); S = dict(V=r["V"], B=r["B"], Hi=r["Hi"], days=r["days"])
        w = np.minimum(S["V"], S["B"]); info.append((w.min(), int((w < -1900).sum()), S["V"].mean()))
        st, day = P.simulate([S] * len(P.MULTS), P.I12, 80); res[pool] = (st, day)
    cells = [f"{50*(np.mean((res['MT5'][0]==1)&(res['MT5'][1]<n))+np.mean((res['FT'][0]==1)&(res['FT'][1]<n))):.1f}%" for n in HZ.values()]
    br = 50 * sum(np.mean((res[p][0] == 2) & (res[p][1] < 79)) for p in ("MT5", "FT"))
    print(f"{CH['sdb']*ms:.2f} | {CH['xau5']*mx:.2f} || " + " / ".join(cells) + f" | {br:.1f}% | {info[0][0]:,.0f} / {info[1][0]:,.0f} | {info[0][1]} / {info[1][1]} | {info[0][2]:.0f} / {info[1][2]:.0f}")
