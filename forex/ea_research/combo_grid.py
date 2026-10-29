"""Every combination of the deployable EAs (ManualSDB, XAUUSD 5 minute, ManualDip: free or ours, the trader 2026-10-11) with sizes adapted to the
daily-loss rule. the trader: "(original wording omitted)".
Grid: SDB x{0, .6, .9, 1.2, 1.5, 1.8} (base 0.12 lot), XAU5 x{0, .6, 1, 1.5, 2} (base 0.04), ManualDip day risk {0, 250, 500, 1000} USD
(x0.75 of the simulated P&L, as the tester showed), guard day stop {1,500, 1,700}; news flat always ON, no-hedge OFF; the guard also closes
the dip ("guarded" view, as in dip_size_grid). FEASIBLE = no day below -1,900 in either pool (the trader's rule) AND breach by 31 Jan <= 3%.
Per subset (SDB, XAU5, DIP, SDB+XAU5, SDB+DIP, XAU5+DIP, all three): the feasible config with the best P(pass) by 30 Nov, and by 22 Dec.
pass70 rules, start +560 counted on 2026-10-12, MIX of the MT5 12-month and FT 2022-26 pools.   python -m forex.ea_research.combo_grid"""
import itertools, os, time
os.environ["DA_Z"] = "1.5"
import numpy as np, pandas as pd
from forex.ea_research import clean_boot_lib as L, pass70 as P, dip_addon as DA
from forex.ea_research.daystop_under_2000 import news_flat
from forex.ea_research.event_macro import server_s
from forex.ea_batch.mt5_mc_config import CH

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "COMBO_GRID_OUTPUT.csv")
P.C0 = 560.0; HZ = {"30Nov": 36, "22Dec": 52, "31Jan": 79}
SDB, XAU, DIP, GUARD = (0, .6, .9, 1.2, 1.5, 1.8), (0, .6, 1.0, 1.5, 2.0), (0, 250, 500, 1000), (1500.0, 1700.0)
cal = pd.read_csv("data/data_macro/event_calendar.csv")
EV = np.array(sorted(server_s(r.date, 8, 30) if r.kind in ("CPI", "NFP") else server_s(r.date, 14, 0) for r in cal.itertuples() if r.kind in ("CPI", "NFP", "FOMC")))
bars = L.bars(); DAYS = {}


def pair_series(pool, ms, mx, g):
    src, a, b = L.POOLS[pool]; lo, hi = L.day(a), L.day(b)
    if pool not in DAYS:
        r = L.C.simulate(bars, L.ea_trades(src, "xau5", CH["xau5"], lo), lo, hi, None, g); DAYS[pool] = r["days"]
    if ms == 0 and mx == 0:
        z = np.zeros(len(DAYS[pool])); return dict(V=z, B=z.copy(), Hi=z.copy(), days=DAYS[pool])
    parts = ([L.ea_trades(src, "sdb", CH["sdb"] * ms, lo)] if ms else []) + ([L.ea_trades(src, "xau5", CH["xau5"] * mx, lo)] if mx else [])
    tr = parts[0] if len(parts) == 1 else L.merge(*parts); tr = news_flat(tr, EV, bars)
    r = L.C.simulate(bars, tr, lo, hi, None, g); S = dict(V=r["V"], B=r["B"], Hi=r["Hi"], days=r["days"])
    if len(S["days"]) != len(DAYS[pool]):
        idx = pd.Index(S["days"]); f = lambda x: pd.Series(x, index=idx).reindex(DAYS[pool]).fillna(0.0).to_numpy()
        S = dict(V=f(S["V"]), B=f(S["B"]), Hi=f(S["Hi"]), days=DAYS[pool])
    return S


def dip_days(risk):
    DA.RISK = float(risk); T, bb = DA.trades(); T, D = DA.day_arrays(T, bb); return D * 0.75


def add_dip(S, D, g):
    X = D.reindex(S["days"]).fillna(0.0); V, B, Hi = S["V"] + X.V.values, S["B"] + X.B.values, S["Hi"] + X.Hi.values
    floor = -(g + 100.0); cut = B < floor
    return dict(V=np.where(cut, np.minimum(S["V"], floor), V), B=np.where(cut, np.minimum(S["B"], floor), B), Hi=Hi, days=S["days"])


def main():
    dips = {r: dip_days(r) for r in DIP if r}; rows = []; t0 = time.time()
    for g, ms, mx in itertools.product(GUARD, SDB, XAU):
        base = {pool: pair_series(pool, ms, mx, g) for pool in ("MT5", "FT")}
        for dr in DIP:
            if ms == 0 and mx == 0 and dr == 0: continue
            res, worst = {}, []
            for pool in ("MT5", "FT"):
                S = add_dip(base[pool], dips[dr], g) if dr else base[pool]
                w = np.minimum(S["V"], S["B"]); worst.append(float(w.min()))
                st, day = P.simulate([S] * len(P.MULTS), P.I12, 80); res[pool] = (st, day)
            row = dict(guard=g, sdb=ms, xau5=mx, dip=dr, worst_mt5=worst[0], worst_FT=worst[1],
                       breach=50 * sum(np.mean((res[p][0] == 2) & (res[p][1] < 79)) for p in ("MT5", "FT")))
            for h, n in HZ.items():
                row[h] = 50 * (np.mean((res["MT5"][0] == 1) & (res["MT5"][1] < n)) + np.mean((res["FT"][0] == 1) & (res["FT"][1] < n)))
            row["subset"] = "+".join(k for k, v in (("SDB", ms), ("XAU5", mx), ("DIP", dr)) if v); rows.append(row)
        pd.DataFrame(rows).to_csv(OUT, index=False); print(f"{time.time()-t0:6.0f}s guard {g} sdb {ms} xau5 {mx} done ({len(rows)} rows)", flush=True)
    R = pd.DataFrame(rows); R["feasible"] = (R[["worst_mt5", "worst_FT"]].min(axis=1) >= -1900) & (R.breach <= 3.0); R.to_csv(OUT, index=False)
    for h in ("30Nov", "22Dec"):
        print(f"\nBEST FEASIBLE per subset by {h}:")
        best = R[R.feasible].sort_values(h, ascending=False).groupby("subset").head(1).sort_values(h, ascending=False)
        print(best[["subset", "guard", "sdb", "xau5", "dip", "30Nov", "22Dec", "31Jan", "breach", "worst_mt5", "worst_FT"]].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
