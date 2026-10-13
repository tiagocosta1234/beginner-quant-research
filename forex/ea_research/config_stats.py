"""Full statistics of the chosen live configuration (the trader 2026-10-11): pair x1.5, no-hedge OFF, guard day stop 1,500 (1.5%).
   python -m forex.ea_research.config_stats"""
import numpy as np, pandas as pd
from forex.ea_research import clean_boot_lib as L
from forex.ea_research import pass70 as P
from forex.ea_batch.mt5_mc_config import CH

MULT, STOP = 1.5, 1500.0
P.C0 = 560.0; HZ = {"30 Oct": 15, "30 Nov": 36, "22 Dec": 52, "31 Jan": 79}
def pf(x): return x[x > 0].sum() / -x[x < 0].sum()
res = {}
for pool in ("MT5", "FT"):
    src, a, b = L.POOLS[pool]; lo, hi = L.day(a), L.day(b)
    tr = L.merge(L.ea_trades(src, "sdb", CH["sdb"] * MULT, lo), L.ea_trades(src, "xau5", CH["xau5"] * MULT, lo))
    r = L.C.simulate(L.bars(), tr, lo, hi, None, STOP); S = dict(V=r["V"], B=r["B"], Hi=r["Hi"], days=r["days"])
    v = pd.Series(S["V"], index=pd.to_datetime(S["days"] * 86400, unit="s")); m = v.resample("ME").sum(); eq = v.cumsum(); w = np.minimum(S["V"], S["B"])
    halts = sum(1 for e in r["ev"] if e == "loss")
    print(f"{pool} ({a}..{b}): days {len(v)} | mean/day {v.mean():.0f} | mean/month {m.mean():,.0f} (median {m.median():,.0f}; best {m.max():,.0f}; worst {m.min():,.0f}) | months positive {100*(m > 0).mean():.0f}%"
          f" | daily PF {pf(v):.2f} | trades {len(tr['pl'])} | days stopped by the guard {halts} ({100*halts/len(v):.1f}%) | worst day {w.min():,.0f} | days < -1,900 {(w < -1900).sum()} | max DD {(eq.cummax() - eq).max():,.0f}")
    if pool == "FT": print("   by year (USD):", v.groupby(v.index.year).sum().round(-2).astype(int).to_dict())
    st, day = P.simulate([S] * len(P.MULTS), P.I12, 80); res[pool] = (st, day)
cells = []
for h, n in HZ.items():
    e = np.mean((res["MT5"][0] == 1) & (res["MT5"][1] < n)); f = np.mean((res["FT"][0] == 1) & (res["FT"][1] < n)); cells.append(f"{h}: {50*(e+f):.1f}% ({100*e:.0f} / {100*f:.0f})")
br = 50 * sum(np.mean((res[p][0] == 2) & (res[p][1] < 79)) for p in ("MT5", "FT"))
dd = np.concatenate([np.where(res[p][0] == 1, res[p][1] + 1, 999) for p in ("MT5", "FT")])
print("P(pass) MIX (12m / 2022-26): " + " | ".join(cells) + f" | breach by 31 Jan {br:.1f}% | median pass {np.median(dd):.0f} business days from 12 Oct = {np.busday_offset('2026-10-12', int(np.median(dd)) - 1, roll='forward')}")
