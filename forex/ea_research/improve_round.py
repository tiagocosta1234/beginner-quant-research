"""IM1 (all legs together) and IM2 (performance throttle), PREREG_IMPROVE.md.   python -m forex.ea_research.improve_round"""
import os
os.environ["DA_Z"] = "1.5"; os.environ["NQ3_FLOOR"] = "1.67"
import numpy as np, pandas as pd
from forex.ea_research import combo_grid as G, pass70 as P, dip_addon as DA, fincept_mt5_verify as V, nq3 as N
from forex.ea_research.event_macro import server_s

cal = pd.read_csv("D:/finance/data_macro/event_calendar.csv"); G.EV = np.array(sorted(server_s(r.date, 8, 30) for r in cal.itertuples() if r.kind == "CPI"))
DA.RISK = 500.0; Tk, bb = DA.trades(); Tk, Dd = DA.day_arrays(Tk, bb); Dd = Dd * 0.75
GUARD, RISK, KSTOP = 1500.0, 500.0, 3.0


def rsi2_leg():
    rows, bars = [], {}
    for m in ("SP", "NSDQ", "DOW"):
        d = DA.load(m); bars[m] = d; s = d[d.hm == 1559].drop_duplicates("date").set_index("date"); b, a, t = s.bo, s.ao, s.t; r2 = V.rsi(b); s200, s5 = b.rolling(200).mean(), b.rolling(5).mean(); sd = b.pct_change().rolling(60, min_periods=40).std(); i = 200
        while i < len(b) - 1:
            if r2.iat[i] < 10 and b.iat[i] > s200.iat[i] and np.isfinite(sd.iat[i]):
                e = i; j = i + 1
                while j < len(b) - 1 and not (b.iat[j] > s5.iat[j] or r2.iat[j] > 70 or j - e >= 5): j += 1
                rows.append(dict(mkt=m, date=b.index[e], t_in=int(t.iat[e]), t_out=int(t.iat[j]), e=float(a.iat[e]) * (1 + DA.SLIP), sd=float(sd.iat[i]))); i = j + 1
            else: i += 1
    T = pd.DataFrame(rows); T["n"] = T.groupby("date").mkt.transform("count"); T["q"] = np.minimum(RISK / T.n / (KSTOP * T.sd), DA.CAP) / T.e; T["stop"] = T.e * (1 - KSTOP * T.sd); T, D = DA.day_arrays(T, bars); return D * 0.75


def s3_leg(nq=0.2, slip=2.0):
    cx = N.Ctx(); N.SLIP = slip; T3 = pd.DataFrame(N.s3(cx)); return N.daily_series(T3, N.PT * nq)


def curve(res, n, c): return 50 * sum(np.mean((res[p][0] == c) & (res[p][1] < n)) for p in res)


def replay(S, H):
    V_, B, Hi = (np.asarray(S[k], float) for k in ("V", "B", "Hi")); out = {"pass": 0, "breach": 0, "open": 0}
    for i in range(40, len(V_) - H):
        cnt = bal = 0.0; r = "open"
        for j in range(i, i + H):
            if B[j] <= -2500 or bal + B[j] <= -8000: r = "breach"; break
            if cnt + min(Hi[j], 2000.0) >= 8100: r = "pass"; break
            cnt += min(V_[j], 2000.0); bal += V_[j]
            if cnt >= 8000: r = "pass"; break
        out[r] += 1
    t = sum(out.values()); return 100 * out["pass"] / t, 100 * out["breach"] / t


if __name__ == "__main__":
    P.C0 = 0.0; Dr = rsi2_leg(); D3 = s3_leg(); lines = ["IM1: legs together (fresh account, MIX; pass within 22 / 44 / 60 business days | breach by 60)"]
    cfgs = {"A installed": [Dd], "B + RSI(2) leg": [Dd, Dr], "C + strategy 3 (0.2 NQ, 2 pt slippage)": [Dd, D3], "D + RSI(2) + strategy 3": [Dd, Dr, D3], "E + both + ManualDip x2": [Dd * 2, Dr, D3]}; base44 = None
    for name, legs in cfgs.items():
        res = {}
        for pool in ("MT5", "FT"):
            S = G.pair_series(pool, 1.5, 1.5, GUARD)
            for leg in legs: S = G.add_dip(S, leg, GUARD)
            res[pool] = P.simulate([S] * len(P.MULTS), P.I12, 90)
        p22, p44, p60, b60 = curve(res, 22, 1), curve(res, 44, 1), curve(res, 60, 1), curve(res, 60, 2); base44 = p44 if base44 is None else base44; base_b = b60 if name.startswith("A") else base_b if "base_b" in dir() else b60
        lines.append(f"  {name:40s} {p22:5.1f}% / {p44:5.1f}% / {p60:5.1f}% | breach {b60:4.1f}%   (vs A at 44 bd: {p44 - base44:+.1f})")
    lines.append("\nIM2: performance throttle (empirical replay, fresh account; pass / breach within 22 and 44 business days)")
    for pool in ("FT", "MT5"):
        s15 = G.add_dip(G.pair_series(pool, 1.5, 1.5, GUARD), Dd, GUARD); s10 = G.add_dip(G.pair_series(pool, 1.0, 1.0, GUARD), Dd, GUARD); s20 = G.add_dip(G.pair_series(pool, 2.0, 2.0, GUARD), Dd, GUARD)
        V15 = np.asarray(s15["V"], float); trail = np.array([V15[max(0, i - 40):i].sum() if i >= 40 else np.nan for i in range(len(V15))]); on = trail > 0
        mk = lambda hi, lo: dict((k, np.where(on, np.asarray(hi[k], float), np.asarray(lo[k], float))) for k in ("V", "B", "Hi"))
        for name, S in (("unthrottled x1.5", s15), ("T1: x1.5 when ON, x1.0 when OFF", mk(s15, s10)), ("T2: x2.0 when ON, x1.0 when OFF", mk(s20, s10))):
            r22, r44 = replay(S, 22), replay(S, 44); lines.append(f"  {pool} pool | {name:34s} | 22 bd pass {r22[0]:5.1f}% breach {r22[1]:4.1f}% | 44 bd pass {r44[0]:5.1f}% breach {r44[1]:4.1f}%")
    txt = "\n".join(lines); print(txt); open(os.path.join(os.path.dirname(__file__), "IMPROVE_ROUND_OUTPUT.txt"), "w").write(txt)
