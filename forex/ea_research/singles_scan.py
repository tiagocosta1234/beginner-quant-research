"""Does any SINGLE strategy, scaled up in risk, pass a fresh MT5 broker account in about 30 days? (the trader 2026-10-12: "(original wording omitted)")
Each strategy alone (ManualSDB, XAUUSD 5-minute, the pair, ManualDip, US RSI(2) dips) at several size multipliers, guard day stop 1,500, CPI news-flat, pass70 rules, FRESH account (0 counted),
MIX = 50/50 of the MT5 12-month and FT 2022-26 pools. Reports P(pass) within 22 and 30 business days and the breach rate; best size per strategy.   python -m forex.ea_research.singles_scan"""
import os
os.environ["DA_Z"] = "1.5"
import numpy as np, pandas as pd
from forex.ea_research import combo_grid as G, pass70 as P, dip_addon as DA, fincept_mt5_verify as V
from forex.ea_research.event_macro import server_s

cal = pd.read_csv("D:/finance/data_macro/event_calendar.csv"); G.EV = np.array(sorted(server_s(r.date, 8, 30) for r in cal.itertuples() if r.kind == "CPI"))
P.C0 = 0.0; GUARD = 1500.0; RISK = 500.0; KSTOP = 3.0


def rsi2_leg():
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
    T = pd.DataFrame(rows); T["n"] = T.groupby("date").mkt.transform("count"); T["q"] = np.minimum(RISK / T.n / (KSTOP * T.sd), DA.CAP) / T.e; T["stop"] = T.e * (1 - KSTOP * T.sd)
    T, D = DA.day_arrays(T, bars); return D * 0.75


DA.RISK = RISK; T, bb = DA.trades(); T, Dd = DA.day_arrays(T, bb); Dd = Dd * 0.75; D2 = rsi2_leg()


def evaluate(make):
    res = {pool: P.simulate([make(pool)] * len(P.MULTS), P.I12, 90) for pool in ("MT5", "FT")}
    f = lambda n, code: 50 * sum(np.mean((res[p][0] == code) & (res[p][1] < n)) for p in res)
    return f(22, 1), f(30, 1), f(30, 2), f(44, 1), f(44, 2)


zero = lambda pool: G.pair_series(pool, 0, 0, GUARD)
rows = []
for k in (1.5, 2.5, 3.5, 5.0):
    rows.append(("ManualSDB alone", f"x{k}", *evaluate(lambda pool, k=k: G.pair_series(pool, k, 0, GUARD))))
    rows.append(("XAU5 alone", f"x{k}", *evaluate(lambda pool, k=k: G.pair_series(pool, 0, k, GUARD))))
    rows.append(("pair SDB+XAU5", f"x{k}", *evaluate(lambda pool, k=k: G.pair_series(pool, k, k, GUARD))))
for k in (1, 2, 4, 8):
    rows.append(("ManualDip alone", f"day risk {int(RISK * k)}", *evaluate(lambda pool, k=k: G.add_dip(zero(pool), Dd * k, GUARD))))
    rows.append(("US RSI(2) alone", f"day risk {int(RISK * k)}", *evaluate(lambda pool, k=k: G.add_dip(zero(pool), D2 * k, GUARD))))
R = pd.DataFrame(rows, columns=["strategy", "size", "pass22", "pass30", "breach30", "pass44", "breach44"])
print("FRESH account, MIX of the two pools, guard 1,500 (percent):"); print(R.round(1).to_string(index=False))
best = R.loc[R.groupby("strategy").pass22.idxmax()]; print("\nbest size per strategy by P(pass in 22 business days):"); print(best.round(1).to_string(index=False))
open(os.path.join(os.path.dirname(__file__), "SINGLES_SCAN_OUTPUT.txt"), "w").write(R.round(1).to_string(index=False))
