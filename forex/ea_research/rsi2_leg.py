"""RSI(2) US dips as a third leg: does it move P(pass)? (PREREG_RSI2_LEG.md)   python -m forex.ea_research.rsi2_leg"""
import os
os.environ["DA_Z"] = "1.5"
import numpy as np, pandas as pd
from forex.ea_research import combo_grid as G, pass70 as P, dip_addon as DA, fincept_mt5_verify as V, more_eas as ME
from forex.ea_research.event_macro import server_s

cal = pd.read_csv("data/data_macro/event_calendar.csv"); G.EV = np.array(sorted(server_s(r.date, 8, 30) for r in cal.itertuples() if r.kind == "CPI"))
P.C0 = 560.0; GUARD = 1500.0; RISK = 500.0; KSTOP = 3.0


def rsi2_trades_table():
    rows, bars = [], {}
    for m in ("SP", "NSDQ", "DOW"):
        d = DA.load(m); bars[m] = d; s = d[d.hm == 1559].drop_duplicates("date").set_index("date"); b, a, t = s.bo, s.ao, s.t
        r2 = V.rsi(b); s200, s5 = b.rolling(200).mean(), b.rolling(5).mean(); sd = b.pct_change().rolling(60, min_periods=40).std(); i = 200
        while i < len(b) - 1:
            if r2.iat[i] < 10 and b.iat[i] > s200.iat[i] and np.isfinite(sd.iat[i]):
                e = i; j = i + 1
                while j < len(b) - 1 and not (b.iat[j] > s5.iat[j] or r2.iat[j] > 70 or j - e >= 5): j += 1
                rows.append(dict(mkt=m, date=b.index[e], t_in=int(t.iat[e]), t_out=int(t.iat[j]), e=float(a.iat[e]) * (1 + DA.SLIP), sd=float(sd.iat[i]))); i = j + 1
            else: i += 1
    T = pd.DataFrame(rows); T["n"] = T.groupby("date").mkt.transform("count")
    T["q"] = np.minimum(RISK / T.n / (KSTOP * T.sd), DA.CAP) / T.e; T["stop"] = T.e * (1 - KSTOP * T.sd); return T, bars


T2, bars2 = rsi2_trades_table(); T2, D2 = DA.day_arrays(T2, bars2); D2 = D2 * 0.75
DA.RISK = RISK; T, bb = DA.trades(); T, Dd = DA.day_arrays(T, bb); Dd = Dd * 0.75
print(f"RSI(2) leg: {len(T2)} trades on {T2.date.nunique()} days 2022-26, mean {T2.pl.mean():+.0f} USD per trade, stopped {100 * T2.stopped.mean():.0f}%")


def curve(res, n): return 50 * sum(np.mean((res[p][0] == 1) & (res[p][1] < n)) for p in res), 50 * sum(np.mean((res[p][0] == 2) & (res[p][1] < n)) for p in res)


out = {}
for name, legs in (("0 live: pair + ManualDip 500", [Dd]), ("1 + RSI(2) leg 500", [Dd, D2]), ("2 + RSI(2) leg 1000", [Dd, D2 * 2])):
    res = {}
    for pool in ("MT5", "FT"):
        S = G.pair_series(pool, 1.5, 1.5, GUARD)
        for leg in legs: S = G.add_dip(S, leg, GUARD)
        res[pool] = P.simulate([S] * len(P.MULTS), P.I12, 120)
        if name.startswith("1") and pool == "FT":
            v = pd.Series(G.pair_series(pool, 1.5, 1.5, GUARD)["V"]); days = G.pair_series(pool, 1.5, 1.5, GUARD)["days"]
            for lab, leg in (("RSI2", D2), ("ManualDip", Dd)):
                x = leg.reindex(days).fillna(0.0).V.values; print(f"  FT daily correlation of {lab} leg with the pair: {np.corrcoef(v, x)[0, 1]:+.2f}")
            print(f"  FT daily correlation RSI2 leg vs ManualDip leg: {np.corrcoef(D2.reindex(days).fillna(0.0).V.values, Dd.reindex(days).fillna(0.0).V.values)[0, 1]:+.2f}")
    out[name] = [curve(res, n) for n in (36, 52, 79)]
print("\nMIX P(pass) 30 Nov / 22 Dec / 31 Jan (breach by 31 Jan):")
for name, r in out.items(): print(f"  {name:28s} {r[0][0]:5.1f}% / {r[1][0]:5.1f}% / {r[2][0]:5.1f}%   (breach {r[2][1]:.1f}%)")
b, p = out["0 live: pair + ManualDip 500"], out["1 + RSI(2) leg 500"]
print(f"\ncriteria: 22 Dec {p[1][0] - b[1][0]:+.1f} (need >= +2.0), 30 Nov {p[0][0] - b[0][0]:+.1f} (need >= 0), breach by 31 Jan {p[2][1] - b[2][1]:+.1f} (need <= +0.3)")
open(os.path.join(os.path.dirname(__file__), "RSI2_LEG_OUTPUT.txt"), "w").write(str(out))
