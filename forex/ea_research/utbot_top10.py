"""Top cells by excess over buy-and-hold among the 71 UT Bot cells profitable in both periods. python -m forex.ea_research.utbot_top10"""
import sys, numpy as np, pandas as pd
sys.argv = [sys.argv[0]]
from forex.ea_research import utbot as U
a = pd.read_csv("data/tmp/utbot_cells.csv"); a["var"] = "base"; b = pd.read_csv("data/tmp/utbot_variant_cells.csv")
R = pd.concat([a, b]); cells = R[(R.mu_DEV > 0) & (R.mu_VAL > 0)].reset_index(drop=True)
VAR = {"base": (1.0, False), "k2": (2.0, False), "k3": (3.0, False), "ha": (1.0, True)}
cache, rows = {}, []
d0, d1, v1 = pd.Timestamp("2021-12-01"), pd.Timestamp("2024-01-01"), pd.Timestamp("2026-01-01")
for r in cells.itertuples():
    if r.sym not in cache:
        d = pd.read_parquet(U.DATA + f"{r.sym}_M1_rates.parquet", columns=["t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"]).sort_values("t").drop_duplicates("t")
        d = d[(d.t < U.END_T) & (d.bo > 0) & (d.ao >= d.bo)]
        cache[r.sym] = pd.DataFrame({"t": d.t.to_numpy(), "bo": d.bo.to_numpy(), "ao": d.ao.to_numpy(), "mo": ((d.bo + d.ao) / 2).to_numpy(), "mh": ((d.bh + d.ah) / 2).to_numpy(), "ml": ((d.bl + d.al) / 2).to_numpy(), "mc": ((d.bc + d.ac) / 2).to_numpy()})
    bars = U.bars(cache[r.sym], U.TFS[r.tf]); key, ha = VAR[r.var]
    sg = U.signals(bars, key, ha); t, bo, ao = bars.t.to_numpy(), bars.bo.to_numpy(), bars.ao.to_numpy()
    tx, sd, ret = U.trades_from(sg, t, bo, ao, U.allowed_next(t))
    ts = pd.to_datetime(tx, unit="s"); cum = np.cumsum(ret)
    def tot(lo, hi): return ret[(ts >= lo) & (ts < hi)].sum()
    def bh(lo, hi):
        i, j = np.searchsorted(t, lo.timestamp()), min(np.searchsorted(t, hi.timestamp()), len(t)) - 1
        return (bo[j] / ao[i] - 1) * 1e4
    rows.append(dict(sym=r.sym, tf=r.tf, var=r.var, trades=len(ret), win=(ret > 0).mean() * 100, ut=cum[-1], bh=bh(d0, v1), ut_dev=tot(d0, d1), bh_dev=bh(d0, d1), ut_val=tot(d1, v1), bh_val=bh(d1, v1),
                     mdd=float((np.maximum.accumulate(cum) - cum).max()), tdev=r.t_DEV, tval=r.t_VAL))
T = pd.DataFrame(rows); T["excess"] = T.ut - T.bh
T = T.sort_values("excess", ascending=False).reset_index(drop=True)
T.to_csv("data/tmp/utbot_top_cells.csv", index=False)
pd.set_option("display.width", 250)
print(T.head(10)[["sym", "tf", "var", "trades", "win", "ut", "bh", "excess", "ut_dev", "bh_dev", "ut_val", "bh_val", "mdd", "tdev", "tval"]].round(0).to_string())
print("cells where UT Bot beat buy-and-hold in BOTH sub-periods:", int(((T.ut_dev > T.bh_dev) & (T.ut_val > T.bh_val)).sum()), "of", len(T))
