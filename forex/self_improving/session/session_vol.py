"""Volatility-aware sizing (PREREG_VOL.md). python -m forex.self_improving.session.session_vol"""
import itertools, sys
import numpy as np, pandas as pd
from forex.self_improving.session import session_lab as S, session_passrate as PR

TM, BC, SP = S.bars; DAY = TM // 86400; HOUR = (TM % 86400) // 3600


def build_tables(train_lo, train_hi):
    u, st = np.unique(DAY, return_index=True); en = np.r_[st[1:], len(TM)]
    rng = np.array([BC[s:e].max() - BC[s:e].min() for s, e in zip(st, en)]); idx = {int(d): k for k, d in enumerate(u)}
    adr20 = np.full(len(u), np.nan); adr120 = np.full(len(u), np.nan)
    for k in range(len(u)): adr20[k] = rng[max(0, k - 20):k].mean() if k >= 5 else np.nan; adr120[k] = rng[max(0, k - 120):k].mean() if k >= 30 else np.nan
    mv = np.abs(np.diff(BC, prepend=BC[0])); ok = (np.diff(TM, prepend=TM[0]) == 60) & (DAY >= train_lo) & (DAY <= train_hi); hv = np.array([mv[ok & (HOUR == h)].mean() if (ok & (HOUR == h)).any() else np.nan for h in range(24)])
    hv = hv / np.nanmean(hv); return u, st, en, rng, idx, adr20, adr120, hv, mv


def features(tr, tabs):
    u, st, en, rng, idx, adr20, adr120, hv, mv = tabs; n = len(tr["in_s"]); F = np.ones((n, 5)); cs = np.cumsum(mv)
    for j in range(n):
        t = tr["in_s"][j]; d = int(t // 86400); k = idx.get(d)
        if k is None or k < 31 or np.isnan(adr120[k]): continue
        i = int(np.searchsorted(TM, t)); h = int((t % 86400) // 3600); s0 = st[k]
        F[j, 0] = adr20[k] / adr120[k]; F[j, 1] = rng[k - 1] / adr20[k]; F[j, 2] = hv[h] if not np.isnan(hv[h]) else 1.0
        rv = cs[i] - cs[max(i - 60, s0)]; exp_ = max(60 * mv[s0:i + 1].mean() * (hv[h] if not np.isnan(hv[h]) else 1.0), 1e-6) if i > s0 + 5 else np.nan; F[j, 3] = rv / exp_ if exp_ == exp_ else 1.0
        sofar = BC[s0:i + 1].max() - BC[s0:i + 1].min() if i > s0 else 0.0; F[j, 4] = np.clip(1.5 - sofar / adr20[k], 0.3, 2.0)
    return np.clip(np.nan_to_num(F, nan=1.0), 0.05, 20.0)


def volf(F, a, a5): return np.clip(F[:, 0] ** a[0] * F[:, 1] ** a[1] * F[:, 2] ** a[2] * F[:, 3] ** a[3] * F[:, 4] ** a5, 0.4, 2.5)


def m(df, L):
    st, day = PR.boot(df, paths=8000); up = 100 * (df.res == 1).mean(); dn = 100 * (df.res == -1).mean()
    return dict(up=up, down=dn, unres=100 * (df.res == 0).mean(), ratio=100 * up / max(up + dn, 1e-9), p44=100 * np.mean((st == 1) & (day < 44)), p120=100 * np.mean((st == 1) & (day < 120)), breach=100 * np.mean(st == 2), med=float(np.median(day[st == 1] + 1)) if (st == 1).any() else np.nan)


def main():
    TRN = S.load("FT", "2022-01-01", "2024-12-31"); tabs = build_tables(TRN[1], TRN[2]); FT = features(TRN[0], tabs)
    MT5 = S.load("MT5"); FE = features(MT5[0], tabs)
    bases = {"SAFE": (1500.0, 1.5, 0.0, 0.0, 0.0), "D": (1500.0, 3.0, 1.0, 0.0, 3.0)}; grid = [(a, a5) for a in itertools.product((-1.0, -0.5, 0.0, 0.5, 1.0), repeat=4) for a5 in (0.0, 1.0)]
    final = []
    for bn, (L, m0, k, r, h) in bases.items():
        S.VOLF = None; b = m(S.run(*TRN, L, m0, k, r, h), L); print(bn, "train base", {x: round(v, 1) for x, v in b.items()}, flush=True); rows = []
        for a, a5 in grid:
            S.VOLF = volf(FT, a, a5); o = m(S.run(*TRN, L, m0, k, r, h), L); rows.append(dict(a=a, a5=a5, **o))
        S.VOLF = None; d = pd.DataFrame(rows); d.to_csv(f"data/si_ledgers/SESSION_vol_train_{bn}.csv", index=False)
        ok = d[(d.breach <= 10) & (d.ratio >= b["ratio"])].sort_values("up", ascending=False).head(3); print(bn, "admissible", int(((d.breach <= 10) & (d.ratio >= b["ratio"])).sum()), "of", len(d)); print(ok.round(1).to_string(index=False), flush=True)
        S.VOLF = None; e0 = m(S.run(*MT5, L, m0, k, r, h), L); final.append(dict(base=bn, variant="BASE", **e0))
        for t in ok.itertuples():
            S.VOLF = volf(FE, t.a, t.a5); final.append(dict(base=bn, variant=f"a={t.a} a5={t.a5}", **m(S.run(*MT5, L, m0, k, r, h), L)))
        S.VOLF = None
    o = pd.DataFrame(final); o.to_csv("data/si_ledgers/SESSION_vol_test.csv", index=False); print(o.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
