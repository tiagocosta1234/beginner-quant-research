"""No-deadline view of the EA sets (the trader: "whats the smartest way to apply the EAs found so far?").

For a set of EAs (EA_IDS, comma separated ids; default the five) summed on one minute clock per year exactly as ea_combo_all.py does, a test is started on EVERY weekday 2022-2026 and simply runs until it passes or
breaches or the data ends (MT5 broker's tests have no time limit; here that is up to 4.75 years). Reported per scale c and rule set: share of starts that pass / breach / are still open, median calendar days to a
1-Step pass, and the same for starts from 2024 on (the gold-rally regime) and for starts in 2022-2023. 2-Step = both phases (+10% then +5%, static $90K floor, 5% daily loss, 4 trading days each).
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from mt5broker.ea_batch import ea_combo_all as CA, ea_curves as EC, floating

END = pd.Timestamp("2026-09-30")
CS = tuple(float(x) for x in os.environ.get("EA_CS", "0.3,0.4,0.5,0.6,0.8,1.0").split(","))


def main():
    s = pd.read_csv(EC.SUMMARY, dtype={"id": str})
    top = s[s.rankable_e == True].head(5)
    ids = os.environ.get("EA_IDS")
    if ids:
        top = top[top.id.isin(ids.split(","))]
    st26 = None
    Uall, Eall, Rall, offset = [], [], [], 0.0
    for y in CA.YEARS:
        fr = CA.year_frames(top, st26, y)
        if fr is None:
            continue
        U, E, R, used, nets = fr
        Uall.append(U); Eall.append(E + offset); Rall.append(R + offset); offset += R[-1]
    U = pd.DatetimeIndex(np.concatenate([u.values for u in Uall])); E1 = np.concatenate(Eall); R1 = np.concatenate(Rall)
    day = U.values.astype("datetime64[D]")
    start = np.flatnonzero(np.r_[True, day[1:] != day[:-1]]); days = pd.DatetimeIndex(day[start])
    before = np.where(start > 0, R1[np.maximum(start - 1, 0)], 0.0)
    v1 = np.add.reduceat(np.diff(R1, prepend=0.0), start)
    m1 = np.minimum(np.minimum.reduceat(E1, start) - before, v1)
    bd = pd.bdate_range(days.min(), END)
    V1 = pd.Series(v1, index=days).reindex(bd).fillna(0.0); M1 = pd.Series(m1, index=days).reindex(bd).fillna(0.0)
    ent = set(days[np.abs(v1) > 0])
    starts = [i for i in range(0, len(bd) - 60, 2)]
    for c in CS:
        pnl, mm = (V1 * c).to_dict(), (M1 * c).to_dict()
        r1, r2 = [], []
        for i in starts:
            dl = list(bd[i:])
            o, d = floating.replay_1step_eq(pnl, mm, dl)
            r1.append((bd[i], o, d))
            r2.append((bd[i], floating.replay_2step_eq(pnl, mm, ent, dl)))
        def share(rows, lab, sel=lambda t: True):
            rr = [r for r in rows if sel(r[0])]
            return np.mean([r[1] == lab for r in rr]) if rr else float("nan")
        def med(rows, sel=lambda t: True):
            x = [r[2] for r in rows if sel(r[0]) and r[1] == "pass"]
            return float(np.median(x)) if x else float("nan")
        segs = (("all starts", lambda t: True), ("2022-23 starts", lambda t: t.year <= 2023), ("2024+ starts", lambda t: t.year >= 2024))
        out = [f"c={c:.1f}"]
        for name, sel in segs:
            out.append(f"{name}: 1-Step pass {share(r1, 'pass', sel):.0%} breach {share(r1, 'breach', sel):.0%} open {share(r1, 'open', sel):.0%} (median {med(r1, sel):.0f}d) | 2-Step pass {share(r2, 'pass', sel):.0%} breach {share(r2, 'breach', sel):.0%}")
        print(" || ".join(out), flush=True)


if __name__ == "__main__":
    main()
