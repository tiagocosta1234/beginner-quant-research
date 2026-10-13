"""Book variants for the live account (the trader 2026-10-11): A = book as simulated (pair scaled down), B = pair untouched at x1.2 + the 6 others on top,
   with and without the -500 per-stream daily clip (an EA cannot clip a day exactly).   python -m forex.ea_research.book_variants"""
import numpy as np, pandas as pd
from forex.ea_research.eval_cycles_all import S, EIGHT, dev, PAIR, cycles
OTH = EIGHT[2:]
k = 300.0 / dev(S[EIGHT]).std(ddof=1)
def book(clip, pair_full):
    X = S[EIGHT] * k; X = X.clip(lower=-500.0) if clip else X
    f = dev(PAIR).std(ddof=1) / dev(X.sum(axis=1)).std(ddof=1)
    return (PAIR + X[OTH].sum(axis=1) * f) if pair_full else X.sum(axis=1) * f
def eta(p, H=75, start=560.0, paths=20000, seed=5):
    rng = np.random.default_rng(seed); v = p.to_numpy(); n = len(v); idx = np.empty((paths, H), int); idx[:, 0] = rng.integers(0, n, paths)
    jump = rng.random((paths, H)) < 0.2; new = rng.integers(0, n, (paths, H))
    for j in range(1, H): idx[:, j] = np.where(jump[:, j], new[:, j], (idx[:, j - 1] + 1) % n)
    V = np.maximum(v[idx], -2000.0); bal = np.full(paths, start); cnt = bal.copy(); st = np.zeros(paths, np.int8); day = np.full(paths, 999)
    for j in range(H):
        a = st == 0; bal = np.where(a, bal + V[:, j], bal); cnt = np.where(a, cnt + np.minimum(V[:, j], 2000.0), cnt)
        st[a & (bal <= -8000)] = 2; a = st == 0; ps = a & (cnt >= 8000); st[ps] = 1; day[ps] = j + 1
    return [round(100 * ((st == 1) & (day <= h)).mean()) for h in (14, 36, 52)], round(100 * (st == 2).mean(), 1)
for nm, p in (("A clip (as charted)", book(True, False)), ("A no clip", book(False, False)), ("B pair x1.2 + 6 on top, no clip", book(False, True)), ("pair only", PAIR)):
    h = p[p.index >= "2026-01-01"]; C = cycles(h); w = (p.cumsum().cummax() - p.cumsum())
    print(f"{nm:32s} sd {h.std():4.0f} | days < -2000 in 2026: {(h < -2000).sum()} | 2026 evals pass/fail {(C.res=='pass').sum()}/{(C.res=='fail').sum()} | max DD 2022-26 {w.max():,.0f}"
          f" | ETA 2026 regime 30Out/30Nov/22Dez {eta(h)[0]}% breach {eta(h)[1]}% | half edge {eta(h - 0.5 * h.mean())[0]}%")
