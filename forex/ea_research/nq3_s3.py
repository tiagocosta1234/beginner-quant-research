"""S3 (overnight bias ORB) alone and as a leg next to the installed system, via the pass70 simulator.   python -m forex.ea_research.nq3_s3"""
import os
os.environ["DA_Z"] = "1.5"
import numpy as np, pandas as pd
from forex.ea_research import nq3 as N, combo_grid as G, pass70 as P, dip_addon as DA
from forex.ea_research.event_macro import server_s

cal = pd.read_csv("data/data_macro/event_calendar.csv"); G.EV = np.array(sorted(server_s(r.date, 8, 30) for r in cal.itertuples() if r.kind == "CPI"))
cx = N.Ctx(); T3 = pd.DataFrame(N.s3(cx)); DA.RISK = 500.0; Tk, bb = DA.trades(); Tk, Dd = DA.day_arrays(Tk, bb); Dd = Dd * 0.75
print(f"S3 trades {len(T3)}; points per trade: mean {T3.pts.mean():+.1f}, median {T3.pts.median():+.1f}, worst {T3.pts.min():.0f}, best {T3.pts.max():.0f}; stop distance avg {T3.mae.mean():.0f} pts MAE")


def curve(res, n, code): return 50 * sum(np.mean((res[p][0] == code) & (res[p][1] < n)) for p in res)


rows = []
P.C0 = 0.0
for nq in (0.2, 0.3, 0.5, 1.0, 2.0):
    D = N.daily_series(T3, N.PT * nq); res = {pool: P.simulate([G.add_dip(G.pair_series(pool, 0, 0, 1500.0), D, 1500.0)] * len(P.MULTS), P.I12, 90) for pool in ("MT5", "FT")}
    rows.append((f"S3 alone, {nq:.1f} NQ ({int(nq * 10)} micro)", nq, *(curve(res, n, 1) for n in (22, 44, 60)), curve(res, 44, 2)))
R = pd.DataFrame(rows, columns=["config", "nq", "pass22", "pass44", "pass60", "breach44"])
print("\nS3 alone, fresh account, guard 1,500, MIX of pools:"); print(R.drop(columns="nq").round(1).to_string(index=False))
print("\nInstalled system + the S3 leg (FRESH account, MIX), guard 1,500:")
P.C0 = 0.0; out = []
for nq in (0.0, 0.2, 0.3, 0.5, 1.0):
    D = N.daily_series(T3, N.PT * nq) if nq else None; res = {}
    for pool in ("MT5", "FT"):
        S = G.add_dip(G.pair_series(pool, 1.5, 1.5, 1500.0), Dd, 1500.0)
        if D is not None: S = G.add_dip(S, D, 1500.0)
        res[pool] = P.simulate([S] * len(P.MULTS), P.I12, 90)
    out.append((f"installed + S3 {nq:.1f} NQ", *(curve(res, n, 1) for n in (22, 44, 60)), curve(res, 44, 2), curve(res, 60, 2)))
print(pd.DataFrame(out, columns=["config", "pass22", "pass44", "pass60", "breach44", "breach60"]).round(1).to_string(index=False))
S3D = N.daily_series(T3, N.PT * 0.5); days = G.pair_series("FT", 1.5, 1.5, 1500.0)["days"]; V = pd.Series(G.pair_series("FT", 1.5, 1.5, 1500.0)["V"]); x = S3D.reindex(days).fillna(0.0).V.values
print(f"\nFT-pool daily correlation of the S3 leg with the installed pair: {np.corrcoef(V, x)[0, 1]:+.2f}")
