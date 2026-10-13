"""Profit lock at +2,500 (the trader 2026-10-13). The MT5 broker still counts at most 2,000 a day (COUNTCAP). Grid on FT 2022-24 (train), top 5 by P(pass<=44bd) with breach<=10%, then one run on the tests. python -m forex.self_improving.session.session_up2500"""
import itertools
import numpy as np, pandas as pd
from forex.self_improving.session import session_lab as S, session_passrate as PR

S.UP = 2500.0


def m(df):
    st, day = PR.boot(df); return 100 * np.mean((st == 1) & (day < 44)), 100 * np.mean((st == 1) & (day < 120)), 100 * np.mean(st == 2)


def main():
    TR = S.load("FT", "2022-01-01", "2024-12-31"); rows = []
    for L, m0, k, r, h in itertools.product((1000.0, 1500.0, 2000.0), (2.0, 3.0, 4.0), (0.0, 1.0, 3.0), (0.0, 1.0), (0.0, 3.0)):
        df = S.run(*TR, L, m0, k, r, h); p44, p120, br = m(df); rows.append(dict(L=L, m0=m0, k=k, r=r, hstop=h, up=100 * (df.res == 1).mean(), down=100 * (df.res == -1).mean(), p44=p44, p120=p120, breach=br))
    d = pd.DataFrame(rows); top = d[d.breach <= 10].sort_values("p44", ascending=False).head(5); print("train top:"); print(top.round(1).to_string(index=False))
    cfg = [(1500.0, 3.0, 1.0, 0.0, 3.0, "D unchanged")] + [(t.L, t.m0, t.k, t.r, t.hstop, "pick") for t in top.itertuples()]; out = []
    for nm, T in (("MT5 12m", S.load("MT5")), ("FT 2025-26", S.load("FT", "2025-01-01", "2026-09-30"))):
        for L, m0, k, r, h, tag in cfg:
            df = S.run(*T, L, m0, k, r, h); p44, p120, br = m(df); out.append(dict(pool=nm, tag=tag, L=L, m0=m0, k=k, r=r, hstop=h, up=100 * (df.res == 1).mean(), down=100 * (df.res == -1).mean(), unres=100 * (df.res == 0).mean(), p44=p44, p120=p120, breach=br, worst=df.low.min()))
    o = pd.DataFrame(out); o.to_csv("D:/finance/si_ledgers/SESSION_up2500_test.csv", index=False); print(o.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
