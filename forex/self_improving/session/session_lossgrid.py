"""Which daily loss lock L is best (1,000 / 1,500 / 2,000 / 2,500) with the +2,000 profit lock? Per L: best config on FT 2022-24 (max P(pass<=44bd), breach <= 10%; if none, min breach), then one run on MT5 12m and FT 2025-26. python -m forex.self_improving.session.session_lossgrid"""
import itertools
import numpy as np, pandas as pd
from forex.self_improving.session import session_lab as S, session_passrate as PR


def m(df):
    st, day = PR.boot(df); return dict(p44=100 * np.mean((st == 1) & (day < 44)), p120=100 * np.mean((st == 1) & (day < 120)), breach=100 * np.mean(st == 2), med=float(np.median(day[st == 1] + 1)) if (st == 1).any() else np.nan, up=100 * (df.res == 1).mean(), down=100 * (df.res == -1).mean(), unres=100 * (df.res == 0).mean(), worst=df.low.min())


def main():
    TR = S.load("FT", "2022-01-01", "2024-12-31"); T = {"MT5 12m": S.load("MT5"), "FT 2025-26": S.load("FT", "2025-01-01", "2026-09-30")}; rows = []
    for L in (1000.0, 1500.0, 2000.0, 2500.0):
        g = []
        for m0, k, r, h in itertools.product((1.0, 1.5, 2.0, 3.0, 4.0), (0.0, 1.0, 3.0), (0.0, 1.0), (0.0, 3.0)):
            g.append((m0, k, r, h, m(S.run(*TR, L, m0, k, r, h))))
        adm = [x for x in g if x[4]["breach"] <= 10]; pick = max(adm, key=lambda x: x[4]["p44"]) if adm else min(g, key=lambda x: x[4]["breach"]); m0, k, r, h, tm = pick
        for nm, TT in T.items():
            o = m(S.run(*TT, L, m0, k, r, h)); rows.append(dict(L=L, cfg=f"m0 {m0} k {k:.0f} r {r:.0f} h {h:.0f}", admissible_train=bool(adm), pool=nm, **o))
    o = pd.DataFrame(rows); o.to_csv("D:/finance/si_ledgers/SESSION_lossgrid.csv", index=False); print(o.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
