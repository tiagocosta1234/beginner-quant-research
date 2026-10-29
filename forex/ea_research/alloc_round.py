"""PREREG_ALLOC.md.   python -m forex.ea_research.alloc_round"""
import os
os.environ["DA_Z"] = "1.5"; os.environ["NQ3_FLOOR"] = "1.67"
import itertools, numpy as np, pandas as pd
from forex.ea_research import combo_grid as G, pass70 as P, dip_addon as DA
from forex.ea_research.event_macro import server_s
cal = pd.read_csv("data/data_macro/event_calendar.csv"); G.EV = np.array(sorted(server_s(r.date, 8, 30) for r in cal.itertuples() if r.kind == "CPI"))
DA.RISK = 500.0; Tk, bb = DA.trades(); Tk, Dd = DA.day_arrays(Tk, bb); Dd = Dd * 0.75; GUARD = 1500.0; P.C0 = 0.0
def curve(r, n, c): return 100 * np.mean((r[0] == c) & (r[1] < n))
rows = []; cache = {}
for ms, mx in itertools.product((0.75, 1.0, 1.5, 2.0, 2.5), repeat=2):
    for pool in ("MT5", "FT"): cache[(ms, mx, pool)] = G.pair_series(pool, ms, mx, GUARD)
for ms, mx, d in itertools.product((0.75, 1.0, 1.5, 2.0, 2.5), (0.75, 1.0, 1.5, 2.0, 2.5), (0.5, 1.0, 1.5)):
    o = dict(ms=ms, mx=mx, d=d)
    for pool in ("MT5", "FT"):
        S = G.add_dip(cache[(ms, mx, pool)], Dd * d, GUARD); r = P.simulate([S] * len(P.MULTS), P.I12, 90); o[f"p44_{pool}"] = curve(r, 44, 1); o[f"b60_{pool}"] = curve(r, 60, 2)
    o["p44"] = (o["p44_mt5"] + o["p44_FT"]) / 2; o["b60"] = (o["b60_mt5"] + o["b60_FT"]) / 2; rows.append(o); print(o, flush=True)
df = pd.DataFrame(rows); base = df[(df.ms == 1.5) & (df.mx == 1.5) & (df.d == 1.0)].iloc[0]
df["dp44"] = df.p44 - base.p44; df["db60"] = df.b60 - base.b60; df["dE8"] = df.p44_mt5 - base.p44_mt5; df["dFT"] = df.p44_FT - base.p44_FT
df["accept"] = (df.dp44 >= 3) & (df.db60 <= 1) & (df.dE8 > 0) & (df.dFT > 0)
df.to_csv("data/si_ledgers/ALLOC.csv", index=False); pd.set_option("display.width", 250)
print("BASE", base.to_dict()); print(df.sort_values("dp44", ascending=False).head(12).round(1).to_string()); print("ACCEPTED:", int(df.accept.sum()), "of", len(df))
