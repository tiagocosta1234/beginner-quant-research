"""Diagnostic: rerun today's engines whose stops are close to the entry with the fill-minute fix (brk_hours.hold_fill logic;
for ict2.sim: the fill minute stops / takes profit only if it CLOSES beyond the level).   python -m forex.ea_research.fillfix_diag"""
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

import forex.ea_research.brk_flag as bf
import forex.ea_research.brk_hours as bh
import forex.ea_research.brk_squeeze as bs
import forex.ea_research.ict2 as ict2
from forex.ea_research.ict2 import SYMS

END = pd.Timestamp("2026-10-03").timestamp()
P = {"DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "2026": ("2026-01-01", "2026-10-02")}
_hold, _sim = bh.hold, ict2.sim


def hold_fix(D, k, kend, side, e, R):
    if kend <= k or e == (D["ao"][k] if side > 0 else D["bo"][k]):
        return _hold(D, k, kend, side, e, R)
    if kend <= k + 1:
        return _hold(D, k, kend, side, e, R)
    stop = e - side * R
    if (side > 0 and D["bc"][k] <= stop) or (side < 0 and D["ac"][k] >= stop):
        return -1.0
    return _hold_from(D, k, kend, side, e, R)


def _hold_from(D, k, kend, side, e, R):
    if side > 0:
        hit = np.flatnonzero(D["bl"][k + 1:kend] <= e - R)
        px = min(e - R, D["bo"][k + 1 + hit[0]]) if len(hit) else D["bo"][kend]
        return (px - e) / R
    hit = np.flatnonzero(D["ah"][k + 1:kend] >= e + R)
    px = max(e + R, D["ao"][k + 1 + hit[0]]) if len(hit) else D["ao"][kend]
    return (e - px) / R


def sim_fix(D, k, side, entry, stop, target, kend):
    if kend <= k + 1 or entry == (D["ao"][k] if side > 0 else D["bo"][k]):
        return _sim(D, k, side, entry, stop, target, kend)
    if not ((side > 0 and stop < entry < target) or (side < 0 and target < entry < stop)):
        return None
    risk = abs(entry - stop)
    c = D["bc"][k] if side > 0 else D["ac"][k]
    sp0 = D["ao"][k] - D["bo"][k]
    if side * (c - stop) <= 0:
        return -1.0, -1.0 + sp0 / risk
    if side * (c - target) >= 0:
        net = side * (target - entry) / risk
        return net, net + sp0 / risk
    return _sim(D, k + 1, side, entry, stop, target, kend)


def patch():
    bh.hold = hold_fix
    bs.hold = hold_fix
    bf.sim = sim_fix


def summarize(name, df, col, ctl):
    out = []
    for lab, (a, b) in P.items():
        s = df[(df.day >= a) & (df.day <= b)]
        out.append(f"{lab} {s[col].mean():+.3f} (ctl {s[ctl].mean():+.3f})")
    print(f"{name}: " + " | ".join(out))


def main():
    with ProcessPoolExecutor(8, initializer=patch) as ex:
        hrs = [r for rr in ex.map(bh.market, [(s, END) for s in SYMS]) for r in rr]
        sq = [r for rr in ex.map(bs.market, [(s, END) for s in SYMS]) for r in rr]
        fl = [r for rr in ex.map(bf.market, [(s, END) for s in SYMS]) for r in rr]
    H = pd.DataFrame(hrs, columns=["mkt", "d", "h", "side", "t_entry", "R", "C", "box_sp"]); H["day"] = pd.to_datetime(H.d, unit="s")
    S = pd.DataFrame(sq, columns=["cell", "mkt", "d", "side", "t_entry", "R", "C"]); S["day"] = pd.to_datetime(S.d, unit="s")
    F = pd.DataFrame(fl); F = F[F.day >= "2022-01-01"]
    old_h = pd.read_parquet("data/si_ledgers/BRK_HOURS.parquet"); old_s = pd.read_parquet("data/si_ledgers/BRK_SQUEEZE.parquet"); old_f = pd.read_parquet("data/si_ledgers/BRK_FLAG.parquet")
    H = H[H.day >= "2022-01-01"]; S = S[S.day >= "2022-01-01"]
    summarize("BRK-HOURS all cells, first run ", old_h, "R", "C"); summarize("BRK-HOURS all cells, fill fix  ", H, "R", "C")
    for c in ("Q1", "Q3"):
        summarize(f"BRK-SQUEEZE {c}, first run     ", old_s[old_s.cell == c], "R", "C"); summarize(f"BRK-SQUEEZE {c}, fill fix      ", S[S.cell == c], "R", "C")
    for col, ctl in (("F1", "C1"), ("F2", "C2")):
        summarize(f"BRK-FLAG {col}, first run        ", old_f, col, ctl); summarize(f"BRK-FLAG {col}, fill fix         ", F, col, ctl)
    best = H.assign(c=H.mkt.map(__import__("forex.ea_research.analog", fromlist=["mclass"]).mclass)).groupby(["c", "h"]).apply(lambda g: pd.Series({p: g[(g.day >= a) & (g.day <= b)].R.mean() for p, (a, b) in P.items()}))
    print("BRK-HOURS cells positive in DEV and VAL after the fix:", best[(best.DEV > 0) & (best.VAL > 0)].round(3).to_dict("index"))


if __name__ == "__main__":
    main()
