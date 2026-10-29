"""Sensitivity map of the USDJPY London breakout (diagnostic, not a test): open 07:00 / 08:00 / 09:00 London x box 15 / 30 / 60 min x exit
15:00 / 17:00 / 20:00 London, orders for 150 min after the box, stop at the other side, no target. Data: HistData 2020-21 (out of sample for
the 08:00 / 30 / 17:00 rule) and MT5 2022-26 (M1 bid/ask).   python -m forex.ea_research.usdjpy_sens"""
import itertools

import numpy as np
import pandas as pd

import forex.ea_research.presample as ps
from forex.ea_research.brk_exits import exits
from forex.ea_research.breakouts import local_clock
from forex.ea_research.crt import load

H, M = 3600, 60
GRID = list(itertools.product((7, 8, 9), (15, 30, 60), (15, 17, 20)))


def run(D, lc, op_h, box_m, ex_h):
    out = []
    for d in np.unique(lc // 86400):
        base = d * 86400
        i0, i1 = np.searchsorted(lc, base + op_h * H), np.searchsorted(lc, base + op_h * H + box_m * M)
        w1, xe = np.searchsorted(lc, base + op_h * H + box_m * M + 150 * M), np.searchsorted(lc, base + ex_h * H)
        if xe >= len(lc) or i1 - i0 < box_m * 0.6 or lc[i0] // 86400 != d or w1 <= i1 + 30 or (D["t"][min(xe, len(lc) - 1)] % 86400) // H in (23, 0):
            continue
        Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
        up = np.flatnonzero(D["ah"][i1:w1] >= Hb)
        dn = np.flatnonzero(D["bl"][i1:w1] <= Lb)
        ku = i1 + up[0] if len(up) else None
        kd = i1 + dn[0] if len(dn) else None
        if (ku is None and kd is None) or (ku is not None and ku == kd):
            continue
        side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
        k = ku if side > 0 else kd
        e = max(Hb, D["ao"][k]) if side > 0 else min(Lb, D["bo"][k])
        R = abs(e - (Lb if side > 0 else Hb))
        if k >= xe or not (R > 0 and R >= 2 * (D["ao"][k] - D["bo"][k])):
            continue
        x = exits(D, k, xe, side, e, R)
        if x:
            out.append((pd.Timestamp(base, unit="s"), x[3]))
    return pd.DataFrame(out, columns=["day", "R"])


def main():
    fj = ps.mt5_floor("USDJPY", "Europe/London", 8, 17)
    J = ps.load_duka("USDJPY", "Europe/London", fj)
    E = load("USDJPY", pd.Timestamp("2026-10-03").timestamp())
    E["t"] = E["t"]
    lcE = local_clock(E["t"], "Europe/London")
    rows = []
    for op_h, box_m, ex_h in GRID:
        a = run(J, J["lc"], op_h, box_m, ex_h)
        b = run(E, lcE, op_h, box_m, ex_h)
        b = b[b.day >= "2022-01-01"]
        rows.append(dict(open=f"{op_h:02d}:00", box=box_m, exit=f"{ex_h}:00", R_2020_21=a.R.mean(), R_2022_24=b[b.day < "2025-01-01"].R.mean(),
                         R_2025=b[(b.day >= "2025-01-01") & (b.day < "2026-01-01")].R.mean(), R_2026=b[b.day >= "2026-01-01"].R.mean(), n_all=len(a) + len(b)))
    T = pd.DataFrame(rows)
    T["all_positive"] = (T[["R_2020_21", "R_2022_24", "R_2025", "R_2026"]] > 0).all(axis=1)
    T.to_csv("data/si_ledgers/USDJPY_SENS.csv", index=False)
    print(T.round(3).to_string(index=False))
    print(f"\ncells positive in all four periods: {int(T.all_positive.sum())} of {len(T)}; mean over the grid by period: " + ", ".join(f"{c} {T[c].mean():+.3f}" for c in ("R_2020_21", "R_2022_24", "R_2025", "R_2026")))


if __name__ == "__main__":
    main()
