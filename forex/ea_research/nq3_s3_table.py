"""S3 (overnight bias ORB) by year at 0.2 / 0.3 / 0.5 NQ: totals, worst day, drawdown.   python -m forex.ea_research.nq3_s3_table"""
import numpy as np, pandas as pd
from forex.ea_research import nq3 as N

cx = N.Ctx(); T = pd.DataFrame(N.s3(cx)); T["year"] = T.entry.dt.year; out = []
for nq in (0.2, 0.3, 0.5):
    k = N.PT * nq; D = N.daily_series(T, k); D.index = pd.to_datetime(D.index * 86400, unit="s")
    for y in (2022, 2023, 2024, 2025, 2026, "all"):
        d = D if y == "all" else D[D.index.year == y]; t = T if y == "all" else T[T.year == y]
        if d.empty: continue
        eq = d.V.cumsum(); out.append(dict(size=f"{nq} NQ ({int(nq * 10)} micro)", year=y, trades=len(t), win=round(100 * (t.pts > 0).mean()), total=round(d.V.sum()), avg_trade=round((t.pts * k).mean()), best_day=round(d.V.max()), worst_day=round(d.V.min()), worst_floating=round(d.B.min()), max_dd=round((eq.cummax() - eq).max())))
R = pd.DataFrame(out); print(R.to_string(index=False)); print("\nrisk per trade (average stop distance %.0f pts): 0.2 NQ = %.0f USD, 0.3 NQ = %.0f USD, 0.5 NQ = %.0f USD" % (T.mae.mean(), T.mae.mean() * 4, T.mae.mean() * 6, T.mae.mean() * 10))
