"""Descriptive sizing of the registered D2 book with the 1,500 day guard (PREREG_D2_ACCOUNT rules): gross chosen each day from the cushion above the floor.
G = the largest grid size <= m * (equity - 92,000), grid 50/75/100/125/150k; flat FOR GOOD once the cushion is below 2,000 (reported as 'stuck', a parked account).
Cells: pass% / breach% / stuck%. Guarded minute-level series per grid size
(d2_account.run), MT5 2022-25 and 2022-26 pools, 5-day block bootstrap, MT5 broker rules from 97,708.08. Constant sizes for reference.
   python -m forex.ea_research.d2_dynsize"""
import numpy as np
import pandas as pd

from forex.ea_research import d2_account as A
from forex.ea_research import swapfree_drift as S
from forex.ea_research import swapfree_mt5sim as Q

GRID = (50_000, 75_000, 100_000, 125_000, 150_000)
HZ = {**Q.HZ, "31 Dec 27": int(np.busday_count(Q.START, np.datetime64("2028-01-01")))}


def sim(V, Bm, policy, rng, paths=20000):
    H = max(HZ.values()) + 1; n = V.shape[1]; nb = H // 5 + 2
    s0 = rng.integers(0, n - 5, size=(paths, nb)); idx = (s0[:, :, None] + np.arange(5)[None, None, :]).reshape(paths, -1)[:, :H]
    bal = np.full(paths, Q.START_BAL); st = np.zeros(paths, np.int8); day = np.full(paths, -1)
    for j in range(H):
        cush = bal - 92_000
        if isinstance(policy, int): g = np.full(paths, policy)
        else:
            m = policy; want = m * cush
            g = np.full(paths, -1)
            for k, G in enumerate(GRID):
                g = np.where(want >= G, k, g)
            g = np.where(cush < 2000, -1, np.where(g < 0, 0, g))
            stk = (st == 0) & (cush < 2000); st[stk], day[stk] = 3, j   # flat for good below 94,000: the account is parked (absorbing)
        v = np.where(g >= 0, V[np.clip(g, 0, None), idx[:, j]], 0.0); b = np.where(g >= 0, Bm[np.clip(g, 0, None), idx[:, j]], 0.0)
        act = st == 0
        br = act & ((b <= -2500) | (bal + b <= 92_000)); st[br], day[br] = 2, j
        act = st == 0
        bal = np.where(act, bal + np.minimum(v, 2000.0), bal)
        ps = act & (bal >= 108_000); st[ps], day[ps] = 1, j
    return st, day


def main():
    DE, DH = S.build("MT5"), S.build("HD"); C = S.spliced_closes(DE, DH); cache = A.day_cache(); rng = np.random.default_rng(1510264)
    ser = {}
    for G in GRID:
        ser[G] = pd.concat([A.run(cache, C, G, 1500, "2022-01-03", "2024-12-31"), A.run(cache, C, G, 1500, "2025-01-01", "2025-12-31"), A.run(cache, C, G, 1500, "2026-01-01", "2026-10-02")])
    rows = []
    for nm, end in (("MT5 2022-25", "2025-12-31"), ("MT5 2022-26", "2026-10-02")):
        V = np.vstack([ser[G].V[:end].to_numpy() for G in GRID]); B = np.vstack([ser[G].B[:end].to_numpy() for G in GRID])
        for pol in [1, 2, 4] + [10.0, 15.0, 20.0, 26.0]:
            st, day = sim(V, B, pol, rng)
            lab = f"constant {GRID[pol]/1000:.0f}k" if isinstance(pol, int) else f"cushion x{pol:.0f}"
            cells = {k: (100 * np.mean((st == 1) & (day < h)), 100 * np.mean((st == 2) & (day < h))) for k, h in HZ.items()}
            stuck = {k: 100 * np.mean((st == 3) & (day < h)) for k, h in HZ.items()}
            print(f"{nm} {lab:14s}: " + " | ".join(f"{k} {p:.1f}/{b:.1f}/{stuck[k]:.1f}" for k, (p, b) in cells.items()), flush=True)
            rows.append(dict(pool=nm, policy=lab, **{f"pass {k}": p for k, (p, b) in cells.items()}, **{f"breach {k}": b for k, (p, b) in cells.items()}, **{f"stuck {k}": v for k, v in stuck.items()}))
    pd.DataFrame(rows).to_csv("data/si_ledgers/D2_DYNSIZE.csv", index=False)


if __name__ == "__main__":
    main()
