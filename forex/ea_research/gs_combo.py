"""What a candidate Market EA would add to the live pair (the trader 2026-10-09: "numeros extremamente realistas"): daily correlation with the pair and the block-bootstrap P(pass) of the pair + the EA at several risk multiples, with haircuts on the EA's edge.
   python -m forex.ea_research.gs_combo [eid] [pnl_scale]
Series: the EA's closed trades from the two real-tick windows (2025Q4 + 2026 = the last 12 months, MT5 broker data) summed by server day; the pair = clean_boot_lib series MT5 broker x1.2 (SDB 0.14 + XAU5 0.05, loss cap 2,000, no lock). Same days only (aligned bootstrap, mean block 5).
Combined day = pair + f x EA; in-day low = pair low + f x min(EA day, 0) (conservative: the two worst moments coincide); the guard flattens at -2,000 (day result floored at -2,000, in-day low floored at -2,100); MT5 broker counted profit min(day, 2,000). f = 1 is the EA's DEFAULT sizing (1% risk per trade for GoldenShot, lot ~0.5 on 100,000).
Haircut h: the EA's daily results are shifted down by (1 - h) x their mean (h = 1 history as it was, 0.5 half the edge, 0 no edge)."""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from forex.ea_batch import mt5data_run as ER
from forex.ea_research import clean_boot_lib as L
from forex.ea_research.clean_boot_lib import _ARGS
from forex.ea_research import clean_bootstrap as BS

A, CAPD, TARGET = BS.A, BS.CAPD, BS.TARGET


def ea_daily(eid: str, scale: float = 1.0) -> dict:
    parts = []
    for y in ("2025Q4", "2026"):
        d = pd.read_csv(ER.OUT / f"results_{y}" / f"{eid}.csv"); d["time"] = pd.to_datetime(d.time, format="%Y.%m.%d %H:%M:%S"); parts.append(d)
    D = pd.concat(parts); o = D[D.direction == "out"].copy(); o["net"] = (o.profit + o.commission + o.swap) * scale; o["day"] = (o.time - pd.Timestamp("1970-01-01")) // pd.Timedelta(days=1)
    return o.groupby("day").net.sum().to_dict()


def estimate(Vp, Bp, Vg, f, h, w_paths=6000, H=BS.H22):
    mean_g = Vg.mean(); Vg_h = Vg - (1 - h) * mean_g
    V = np.maximum(Vp + f * Vg_h, -CAPD); B = np.maximum(Bp + f * np.minimum(Vg_h, 0.0), -2100.0); n = len(V); idx = BS.stationary_idx(n, w_paths, H); cnt = np.full(w_paths, BS.C0); st = np.zeros(w_paths, np.int8); day = np.full(w_paths, -1)
    for j in range(H):
        v, b = V[idx[:, j]], B[idx[:, j]]; act = st == 0; br = act & ((b <= -0.025 * A) | (A + cnt + b <= 0.92 * A)); st = np.where(br, 2, st); day = np.where(br, j, day); act = st == 0
        cnt = np.where(act, cnt + np.where(v > 0, np.minimum(v, CAPD), v), cnt); ps = act & (cnt >= TARGET); st = np.where(ps, 1, st); day = np.where(ps, j, day)
    return np.mean((st == 1) & (day < BS.H30)), np.mean((st == 1) & (day < H)), np.mean(st == 2), (np.median(day[st == 1]) + 1 if (st == 1).any() else float("nan"))


def main():
    eid = _ARGS[0] if len(_ARGS) > 0 else "mkt_goldenshot_M15"; scale = float(_ARGS[1]) if len(_ARGS) > 1 else 1.0
    s = L.series("MT5", 1.2); days = s["days"].tolist(); Vp, Bp = s["V"], s["B"]; g = ea_daily(eid, scale); Vg = np.array([g.get(d, 0.0) for d in days])
    print(f"{eid}: {len(g)} days with trades of {len(days)}; EA mean/day {Vg.mean():+.0f} USD, worst day {Vg.min():+.0f}, best {Vg.max():+.0f}; pair mean/day {Vp.mean():+.0f}")
    print(f"daily correlation with the pair: {np.corrcoef(Vp, Vg)[0, 1]:+.3f}; both lose the same day: {int(((Vp < -300) & (Vg < -300)).sum())} of {int((Vg < -300).sum())} EA losing days")
    base = estimate(Vp, Bp, Vg, 0.0, 1.0); print(f"\npair alone (plan A x1.2, no lock): by 30 Nov {100*base[0]:.1f}% | by 22 Dec {100*base[1]:.1f}% | breach {100*base[2]:.1f}% | median day {base[3]:.0f}")
    for h in (1.0, 0.5, 0.0):
        print(f"\n-- EA edge kept h = {h}")
        for f in (0.5, 1.0, 1.5, 2.0):
            m = estimate(Vp, Bp, Vg, f, h); print(f"   f = {f}: by 30 Nov {100*m[0]:5.1f}% | by 22 Dec {100*m[1]:5.1f}% | breach {100*m[2]:4.1f}% | median pass day {m[3]:4.0f}")


if __name__ == "__main__":
    main()
