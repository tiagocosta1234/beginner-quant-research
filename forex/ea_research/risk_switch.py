"""RS1: gold 200-day-average risk switch for the pair (x1.5 above, x1.0 below), PREREG_RISK_SWITCH.md.   python -m forex.ea_research.risk_switch"""
import os
os.environ["DA_Z"] = "1.5"
import numpy as np, pandas as pd
from forex.ea_research import combo_grid as G, pass70 as P, dip_addon as DA
from forex.ea_research.event_macro import server_s

cal = pd.read_csv("data/data_macro/event_calendar.csv")
G.EV = np.array(sorted(server_s(r.date, 8, 30) for r in cal.itertuples() if r.kind == "CPI"))
P.C0 = 560.0; GUARD = 1500.0; DA.RISK = 500.0
T, bb = DA.trades(); T, Dd = DA.day_arrays(T, bb); Dd = Dd * 0.75
g = pd.read_parquet("forex/data/XAUUSD_D1.parquet", columns=["time", "close"]); g["day"] = g.time // 86400
c = g.drop_duplicates("day").set_index("day").close.sort_index(); sma = c.rolling(200).mean(); on_prev = (c > sma).shift(1)      # filter for day D uses D-1 close and average


def on_for(days):
    idx = pd.Index(days); pos = on_prev.index.searchsorted(idx, side="right") - 1                 # latest filter value known for each server day
    return np.where(pos >= 0, on_prev.to_numpy()[np.clip(pos, 0, None)], False).astype(bool)


def build(pool):
    a, b = G.pair_series(pool, 1.5, 1.5, GUARD), G.pair_series(pool, 1.0, 1.0, GUARD); days = a["days"]; on = on_for(days)
    sw = dict(V=np.where(on, a["V"], b["V"]), B=np.where(on, a["B"], b["B"]), Hi=np.where(on, a["Hi"], b["Hi"]), days=days)
    return a, b, sw, on


def stats(S, on, days, label):
    d = pd.to_datetime(np.asarray(days) * 86400, unit="s"); V = pd.Series(S["V"], index=d); B = pd.Series(S["B"], index=d)
    def part(a, b):
        v, bbv = V[(V.index >= a) & (V.index <= b)], B[(B.index >= a) & (B.index <= b)]; eq = v.cumsum()
        return f"net {v.sum():9,.0f} | max DD {(eq.cummax() - eq).max():7,.0f} | worst day {bbv.min():7,.0f}"
    print(f"  {label:9s} 2022-23: {part('2022-01-01', '2023-12-31')}\n  {'':9s} 2024-26: {part('2024-01-01', '2026-09-30')}")


def curve(res, n): return 50 * sum(np.mean((res[p][0] == 1) & (res[p][1] < n)) for p in res), 50 * sum(np.mean((res[p][0] == 2) & (res[p][1] < n)) for p in res)


sims = {"live x1.5": {}, "switch": {}, "x1.0": {}}
for pool in ("MT5", "FT"):
    a, b, sw, on = build(pool); print(f"\n== {pool}: filter ON {100 * on.mean():.0f}% of days")
    if pool == "FT":
        stats(a, on, a["days"], "x1.5"); stats(b, on, a["days"], "x1.0"); stats(sw, on, a["days"], "switch")
        dd = pd.to_datetime(np.asarray(a["days"]) * 86400, unit="s"); Va = pd.Series(a["V"], index=dd)
        print(f"  x1.5 P&L when ON {Va[on].sum():,.0f} ({on.sum()} d) | when OFF {Va[~on].sum():,.0f} ({(~on).sum()} d)")
    for name, S0 in (("live x1.5", a), ("switch", sw), ("x1.0", b)):
        S = G.add_dip(S0, Dd, GUARD); sims[name][pool] = P.simulate([S] * len(P.MULTS), P.I12, 120)
print("\nMIX pass / breach (bd 36 = 30 Nov, 52 = 22 Dec, 79 = 31 Jan):")
out = {}
for name, res in sims.items():
    p36, _ = curve(res, 36); p52, _ = curve(res, 52); p79, b79 = curve(res, 79); out[name] = (p36, p52, p79, b79)
    print(f"  {name:10s} 30 Nov {p36:5.1f}% | 22 Dec {p52:5.1f}% | 31 Jan {p79:5.1f}% | breach by 31 Jan {b79:4.1f}%")
L_, S_ = out["live x1.5"], out["switch"]
print(f"\ncriterion 1: 30 Nov diff {S_[0]-L_[0]:+.1f}, 22 Dec diff {S_[1]-L_[1]:+.1f} (need >= -1.5 both) -> {S_[0]-L_[0] >= -1.5 and S_[1]-L_[1] >= -1.5}")
print(f"criterion 2 (breach part): {L_[3]-S_[3]:+.1f} points lower (need >= 0.5)")
open(os.path.join(os.path.dirname(__file__), "RISK_SWITCH_OUTPUT.txt"), "w").write(str(out))
