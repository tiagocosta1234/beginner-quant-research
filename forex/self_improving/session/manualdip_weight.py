"""How much does ManualDip (index dip-reversal, the only non-gold signal) reduce the dependence on gold? MT5 broker pool, same pipeline as faster_than_live.py (1-minute guard daily series + day-block bootstrap). Pair size {1.0, 1.5, 2.0} x ManualDip day risk {0, 500, 1000, 2000, 3000}
(x0.75 as in combo_grid.dip_days). Gold-dependence stress: the same bootstrap with the strongest gold run (2026-01-12 .. 2026-03-10) removed from the days. python -m forex.self_improving.session.manualdip_weight"""
import os
os.environ["DA_Z"] = "1.5"; os.environ["NQ3_FLOOR"] = "1.67"
import numpy as np, pandas as pd
from forex.ea_research import combo_grid as G, pass70 as P, clean_boot_lib as L

P.C0 = 0.0; H = 250


def stats(S):
    st, dy = P.simulate([S] * len(P.MULTS), P.I12, H); ps = st == 1
    return dict(p44=100 * np.mean(ps & (dy < 44)), p120=100 * np.mean(ps & (dy < 120)), breach=100 * np.mean(st == 2), med=float(np.median(dy[ps] + 1)) if ps.any() else np.nan)


def main():
    rows = []; dips = {r: (G.dip_days(r) if r else None) for r in (0, 500, 1000, 2000, 3000)}
    d0 = (pd.Timestamp("2026-01-12") - pd.Timestamp("1970-01-01")).days; d1 = (pd.Timestamp("2026-03-10") - pd.Timestamp("1970-01-01")).days
    for m, g in ((1.0, 1500.0), (1.5, 1500.0), (2.0, 2000.0)):
        base = G.pair_series("MT5", m, m, g); days = np.asarray(base["days"]); keep = ~((days >= d0) & (days <= d1))
        for r, D in dips.items():
            S = base if D is None else G.add_dip(base, D, g)
            full = stats(S); cut = stats({k: (np.asarray(v)[keep] if k != "days" else days[keep]) for k, v in S.items()})
            kd = 0.0 if D is None else float(D.reindex(days).fillna(0).V.sum()); gold = float(np.asarray(base["V"]).sum())
            rows.append(dict(size=m, loss=g, dip_risk=r, dip_net_12m=kd, gold_net_12m=gold, p44=full["p44"], p120=full["p120"], breach=full["breach"], med=full["med"], p44_nogoldrun=cut["p44"], p120_nogoldrun=cut["p120"], breach_nogoldrun=cut["breach"], med_nogoldrun=cut["med"]))
            print({k: (round(float(v), 1) if not isinstance(v, str) else v) for k, v in rows[-1].items()}, flush=True)
    pd.DataFrame(rows).to_csv("D:/finance/si_ledgers/MANUALDIP_WEIGHT.csv", index=False)


if __name__ == "__main__":
    main()
