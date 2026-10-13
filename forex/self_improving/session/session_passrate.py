"""Pass rate of a session-system config by stationary block bootstrap (mean block 5 days) of the system's own daily results (day PnL, day low), fresh MT5 broker account:
counted day profit capped at 2,000, pass at +8,000 counted, breach at day low <= -2,500 or cumulative <= -8,000. Horizons in business days. python -m forex.self_improving.session.session_passrate"""
import numpy as np, pandas as pd
from forex.self_improving.session import session_lab as S

rng = np.random.default_rng(20261013)


def boot(df, H=250, paths=20000, blk=5.0):
    p = df.pnl.values; lo = df.low.values; n = len(p); idx = np.empty((paths, H), int); idx[:, 0] = rng.integers(0, n, paths)
    for j in range(1, H):
        new = rng.random(paths) < 1 / blk; idx[:, j] = np.where(new, rng.integers(0, n, paths), (idx[:, j - 1] + 1) % n)
    cum = np.zeros(paths); st = np.zeros(paths, int); day = np.full(paths, -1)
    for j in range(H):
        act = st == 0; pj = p[idx[:, j]]; lj = lo[idx[:, j]]
        br = act & (lj <= -S.DAYLIM); st[br] = 2; day[br] = j; act = st == 0
        cum = np.where(act, cum + np.where(pj > 0, np.minimum(pj, S.COUNTCAP), pj), cum)
        ps = act & (cum >= 8000); st[ps] = 1; day[ps] = j; br2 = act & ~ps & (cum <= -8000); st[br2] = 2; day[br2] = j
    return st, day


def line(name, df):
    st, day = boot(df); out = {f"pass<={h}bd": 100 * np.mean((st == 1) & (day < h)) for h in (22, 44, 66, 120, 250)}
    ps = (st == 1); return name, out, 100 * np.mean(st == 2), 100 * np.mean(st == 0), float(np.median(day[ps] + 1)) if ps.any() else float("nan")


def main():
    cfgs = (("A exploratory L1000 m4 r1", 1000.0, 4.0, 0.0, 1.0, 0.0), ("B its constant-size baseline", 1000.0, 4.0, 0.0, 0.0, 0.0), ("C prereg pick L1500 x1 r1 h3", 1500.0, 1.0, 0.0, 1.0, 3.0), ("D L1500 x3 k1 r0 h3", 1500.0, 3.0, 1.0, 0.0, 3.0))
    pools = {"MT5 12m": S.load("MT5"), "FT 2025-26": S.load("FT", "2025-01-01", "2026-09-30"), "FT 2022-24 (train)": S.load("FT", "2022-01-01", "2024-12-31")}
    for nm, TR in pools.items():
        print("==", nm)
        for tag, L, m0, k, r, h in cfgs:
            df = S.run(*TR, L, m0, k, r, h); n, o, b, op, md = line(tag, df)
            print(f"{n:32s} " + " ".join(f"{kk} {v:5.1f}%" for kk, v in o.items()) + f" | breach {b:.1f}% open {op:.1f}% | median pass day {md:.0f}", flush=True)


if __name__ == "__main__":
    main()
