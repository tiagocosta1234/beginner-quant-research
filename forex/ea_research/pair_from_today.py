"""The switched-off gold EA pair (final plan of 2026-10-11: ManualSDB 0.18 + XAU5 0.06 = x1.5, guard day stop 1,500, news flat on CPI only,
ManualDip 500) re-simulated from TODAY's account state (balance 97,708.08 on 2026-10-15, counted -2,291.92), first trading day Fri 16 Oct.
Same machinery as combo_grid.py (MIX of the MT5 12-month and FT 2022-26 pools, pass70 MT5 broker rules); also x1.2 without ManualDip for reference.
   python -m forex.ea_research.pair_from_today"""
import numpy as np
import pandas as pd

from forex.ea_research import combo_grid as cg
from forex.ea_research import pass70 as P
from forex.ea_research.event_macro import server_s

P.C0 = -2291.92
START = np.datetime64("2026-10-16")
HZ = {"30 Oct": "2026-10-31", "30 Nov": "2026-12-01", "22 Dec": "2026-12-23", "31 Jan 27": "2027-02-01"}
HN = {k: int(np.busday_count(START, np.datetime64(v))) for k, v in HZ.items()}


def main():
    cal = pd.read_csv("data/data_macro/event_calendar.csv")
    cg.EV = np.array(sorted(server_s(r.date, 8, 30) for r in cal.itertuples() if r.kind == "CPI"))
    dip = cg.dip_days(500)
    H = max(HN.values()) + 1
    print("trading days from Fri 16 Oct:", HN)
    for label, g, ms, mx, dr in (("final plan x1.5 + ManualDip 500, day stop 1,500", 1500.0, 1.5, 1.5, 500), ("x1.2 pair only, day stop 1,500", 1500.0, 1.2, 1.2, 0)):
        res = {}
        for pool in ("MT5", "FT"):
            S = cg.pair_series(pool, ms, mx, g)
            if dr:
                S = cg.add_dip(S, dip, g)
            res[pool] = P.simulate([S] * len(P.MULTS), P.I12, H)
        out = []
        for k, n in HN.items():
            pp = 50 * sum(np.mean((res[p][0] == 1) & (res[p][1] < n)) for p in res)
            bb = 50 * sum(np.mean((res[p][0] == 2) & (res[p][1] < n)) for p in res)
            pe = 100 * np.mean((res["MT5"][0] == 1) & (res["MT5"][1] < n))
            pf = 100 * np.mean((res["FT"][0] == 1) & (res["FT"][1] < n))
            out.append(f"{k}: pass {pp:.1f}% (MT5 12m {pe:.0f}% / FT 2022-26 {pf:.0f}%), breach {bb:.1f}%")
        print(f"{label}:\n   " + "\n   ".join(out))


if __name__ == "__main__":
    main()
