"""Round 2 (see PREREG_SESSION2.md). python -m forex.self_improving.session.session_round2"""
import itertools, os
import numpy as np, pandas as pd
from forex.self_improving.session import session_lab as S, session_passrate as PR

PROT = {"p": 1.0}; _orig = S.scale_for


def scale2(P, hleft, Lc, m0, k, r, hstop):
    s = _orig(P, hleft, Lc, m0, k, r, hstop)
    if P >= 1000.0: s *= PROT["p"]
    return float(min(s, S.MMAX))


S.scale_for = scale2


def metrics(df):
    st, day = PR.boot(df); return 100 * np.mean((st == 1) & (day < 44)), 100 * np.mean(st == 2), 100 * np.mean((st == 1) & (day < 120))


def main():
    out = "data/si_ledgers/SESSION_round2_train.csv"
    TR = S.load("FT", "2022-01-01", "2024-12-31"); rows = []
    for Lc, m0, k, r, h, mm, p in itertools.product((750.0, 1000.0, 1500.0, 2000.0), (2.0, 3.0, 4.0, 6.0), (0.0, 1.0, 3.0), (0.0, 1.0), (0.0, 3.0), (6.0, 10.0), (1.0, 0.5)):
        S.MMAX = mm; PROT["p"] = p; df = S.run(*TR, Lc, m0, k, r, h); p44, br, p120 = metrics(df)
        rows.append(dict(L=Lc, m0=m0, k=k, r=r, hstop=h, mmax=mm, prot=p, up=100 * (df.res == 1).mean(), down=100 * (df.res == -1).mean(), p44=p44, p120=p120, breach=br))
    d = pd.DataFrame(rows); d.to_csv(out, index=False); print(len(d), "configs; admissible", int((d.breach <= 10).sum()))
    top = d[d.breach <= 10].sort_values("p44", ascending=False).head(5); print(top.round(1).to_string(index=False))
    tests = [(1500.0, 3.0, 1.0, 0.0, 3.0, 6.0, 1.0, "D (reference)")] + [(t.L, t.m0, t.k, t.r, t.hstop, t.mmax, t.prot, "round2 pick") for t in top.itertuples()]
    res = []
    for nm, T in (("MT5 12m", S.load("MT5")), ("FT 2025-26", S.load("FT", "2025-01-01", "2026-09-30"))):
        for L, m0, k, r, h, mm, p, tag in tests:
            S.MMAX = mm; PROT["p"] = p; df = S.run(*T, L, m0, k, r, h); p44, br, p120 = metrics(df)
            res.append(dict(pool=nm, tag=tag, L=L, m0=m0, k=k, r=r, hstop=h, mmax=mm, prot=p, up=100 * (df.res == 1).mean(), down=100 * (df.res == -1).mean(), unres=100 * (df.res == 0).mean(), p44=p44, p120=p120, breach=br))
    o = pd.DataFrame(res); o.to_csv("data/si_ledgers/SESSION_round2_test.csv", index=False); print(o.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
