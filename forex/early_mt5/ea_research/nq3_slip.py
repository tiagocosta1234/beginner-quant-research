"""NQ3 addendum: NSDQ+ with a 1.67-point spread floor and 0..3 points of slippage on market fills (PREREG_NQ3.md addendum).   python -m mt5broker.ea_research.nq3_slip"""
import os
os.environ["NQ3_FLOOR"] = "1.67"
import numpy as np, pandas as pd
from mt5broker.ea_research import nq3 as N

cx = N.Ctx(); lines = []
for slip in (0.0, 1.0, 2.0, 3.0):
    N.SLIP = slip; T3 = pd.DataFrame(N.s3(cx)); d, v, h = N.summ(T3, N.DEV), N.summ(T3, N.VAL), N.summ(T3, N.HOLD); acc = bool(d["n"] >= 40 and d["avg"] >= 30 and d["pf"] >= 1.2 and d["t"] >= 1.65 and v["avg"] > 0)
    lines.append(f"S3, slippage {slip:.0f} pt (spread floor 1.67):  accepted-by-rule: {acc}\n   2022: {N.f(N.summ(T3, N.W22))}\n   DEV 2023-24: {N.f(d)}\n   VAL 2025: {N.f(v)}\n   2026 Jan-Sep (already seen): {N.f(h)}")
    for nq in (0.2, 0.3):
        D = N.daily_series(T3, N.PT * nq); D.index = pd.to_datetime(D.index * 86400, unit="s"); lines.append(f"   at {nq} NQ: " + " | ".join(f"{y}: {D[D.index.year == y].V.sum():+,.0f}" for y in (2022, 2023, 2024, 2025)) + f" | 2026 to Sep: {D[(D.index >= '2026-01-01') & (D.index < '2026-10-01')].V.sum():+,.0f} | total {D.V.sum():+,.0f} | worst day {D.V.min():,.0f}")
    lines.append("")
N.SLIP = 1.0
for k, fn in (("S1", N.s1), ("S2", N.s2)):
    df = pd.DataFrame(fn(cx)); lines.append(f"{k} at slippage 1 pt: DEV {N.f(N.summ(df, N.DEV))} | VAL {N.f(N.summ(df, N.VAL))}")
txt = "\n".join(lines); print(txt); open(os.path.join(os.path.dirname(__file__), "NQ3_SLIP_RESULT.txt"), "w").write(txt)
