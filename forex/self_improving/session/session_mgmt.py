"""Position management ideas (PREREG_MGMT.md). python -m forex.self_improving.session.session_mgmt"""
import itertools, os
import numpy as np, pandas as pd
from forex.self_improving.session import session_lab as S, session_passrate as PR

TM, BC, SP = S.bars; DAY = TM // 86400


def adr_table():
    u, st = np.unique(DAY, return_index=True); en = np.r_[st[1:], len(TM)]; rng = np.array([BC[s:e].max() - BC[s:e].min() for s, e in zip(st, en)])
    adr = np.array([rng[max(0, k - 20):k].mean() if k >= 5 else np.nan for k in range(len(u))]); return {int(d): adr[k] for k, d in enumerate(u)}


ADR = adr_table()


def runner(tr, days_ahead):
    t = {k: np.array(v, copy=True) for k, v in tr.items()}; n = len(t["in_s"])
    for j in range(n):
        if t["pl"][j] <= 0: continue
        o = float(t["out_s"][j]); d = int(o // 86400); end_t = (d + days_ahead) * 86400 + 22 * 3600
        if o >= end_t - 60: continue
        i0 = int(np.searchsorted(TM, o)); i1 = min(int(np.searchsorted(TM, end_t)), len(TM) - 1)
        if i1 - i0 < 2: continue
        sd = t["side"][j]; ent = t["entry"][j]; mark = BC[i0:i1 + 1] if sd > 0 else BC[i0:i1 + 1] + SP[i0:i1 + 1]; bad = np.nonzero(sd * (mark - ent) <= 0)[0]; k = int(bad[0]) if len(bad) else len(mark) - 1
        t["out_s"][j] = TM[i0 + k]; t["pl"][j] = sd * (mark[k] - ent) * t["q"][j]; t["exit"][j] = mark[k]
    return t


def addons(tr, step, ratio):
    n = len(tr["in_s"]); rows = []
    for j in range(n):
        d = int(tr["in_s"][j] // 86400); adr = ADR.get(d)
        if adr is None or np.isnan(adr): continue
        sd = tr["side"][j]; i0 = int(np.searchsorted(TM, tr["in_s"][j])); i1 = int(np.searchsorted(TM, tr["out_s"][j]))
        if i1 - i0 < 3: continue
        mark = BC[i0:i1] if sd > 0 else BC[i0:i1] + SP[i0:i1]; hit = np.nonzero(sd * (mark - tr["entry"][j]) >= step * adr)[0]
        if not len(hit): continue
        k = i0 + int(hit[0]); ent = BC[k] + SP[k] if sd > 0 else BC[k]; ex = tr["exit"][j]; q = tr["q"][j] * ratio
        rows.append((TM[k], tr["out_s"][j], sd, ent, q, sd * (ex - ent) * q, ex))
    if not rows: return tr
    out = {k_: np.array(v, copy=True) for k_, v in tr.items()}
    for key, c in (("in_s", 0), ("out_s", 1), ("side", 2), ("entry", 3), ("q", 4), ("pl", 5), ("exit", 6)): out[key] = np.concatenate([out[key], np.array([r[c] for r in rows], dtype=float)])
    for key in tr:
        if key not in ("in_s", "out_s", "side", "entry", "q", "pl", "exit"): out[key] = np.concatenate([out[key], np.zeros(len(rows), dtype=np.asarray(tr[key]).dtype)]) if np.asarray(tr[key]).ndim == 1 else tr[key]
    o = np.argsort(out["in_s"], kind="stable"); return {k_: v[o] for k_, v in out.items()}


def variant_tr(base, mode, add):
    tr, lo, hi = base
    if mode: tr = runner(tr, 0 if mode == "same-day" else 1)
    if add: tr = addons(tr, *add)
    return tr, lo, hi


def m(df):
    st, day = PR.boot(df, paths=8000); up = 100 * (df.res == 1).mean(); dn = 100 * (df.res == -1).mean()
    return dict(up=up, down=dn, unres=100 * (df.res == 0).mean(), ratio=100 * up / max(up + dn, 1e-9), p44=100 * np.mean((st == 1) & (day < 44)), p120=100 * np.mean((st == 1) & (day < 120)), breach=100 * np.mean(st == 2), med=float(np.median(day[st == 1] + 1)) if (st == 1).any() else np.nan)


def main():
    TRN = S.load("FT", "2022-01-01", "2024-12-31"); MT5 = S.load("MT5"); bases = {"SAFE": (1500.0, 1.5, 0.0, 0.0, 0.0), "D": (1500.0, 3.0, 1.0, 0.0, 3.0)}
    grid = list(itertools.product((0.0, 0.5, 1.0, 2.0), (None, "same-day", "two-day"), (None, (0.10, 0.5), (0.10, 1.0), (0.20, 0.5), (0.20, 1.0)))); final = []
    for bn, (L, m0, k, r, h) in bases.items():
        S.BOOST = 0.0; b = m(S.run(*TRN, L, m0, k, r, h)); print(bn, "train base", {x: round(float(v), 1) for x, v in b.items()}, flush=True); rows = []; cache = {}
        for bo, mode, add in grid:
            key = (mode, add)
            if key not in cache: cache[key] = variant_tr(TRN, mode, add)
            S.BOOST = bo; o = m(S.run(*cache[key], L, m0, k, r, h)); rows.append(dict(boost=bo, mode=str(mode), add=str(add), **o))
        S.BOOST = 0.0; d = pd.DataFrame(rows); d.to_csv(f"D:/finance/si_ledgers/SESSION_mgmt_train_{bn}.csv", index=False)
        ok = d[(d.breach <= 10) & (d.ratio >= b["ratio"])].sort_values("up", ascending=False).head(3); print(bn, "admissible", int(((d.breach <= 10) & (d.ratio >= b["ratio"])).sum()), "of", len(d)); print(ok.round(1).to_string(index=False), flush=True)
        S.BOOST = 0.0; final.append(dict(base=bn, variant="BASE", **m(S.run(*MT5, L, m0, k, r, h))))
        for t in ok.itertuples():
            mode = None if t.mode == "None" else t.mode; add = None if t.add == "None" else eval(t.add); S.BOOST = t.boost
            final.append(dict(base=bn, variant=f"boost {t.boost} runner {t.mode} addon {t.add}", **m(S.run(*variant_tr(MT5, mode, add), L, m0, k, r, h)))); S.BOOST = 0.0
    o = pd.DataFrame(final); o.to_csv("D:/finance/si_ledgers/SESSION_mgmt_test.csv", index=False); print(o.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
