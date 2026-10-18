"""USDJPY London-open breakout re-checked for MT5 broker's zero-spread minutes (diagnostic re-measurement of the registered rule, no new
trial; variants fixed 2026-10-16 18:23 before any number was computed). Rule unchanged: `usdjpy_sens.run(E, lc, 8, 30, 17)` =
08:00-08:30 London box, OCO stops until 11:00, stop at the other side, no target, exit 17:00 London.
  A  raw MT5 M1 bars (ask = bid + bar spread; reproduces USDJPY_SENS +0.146 / +0.108 / +0.114)
  B  zero fix: a minute with spread <= 0 gets the median non-zero spread of the previous calendar month at the same server hour
  C  today's cost: every minute's spread floored at 0.006 (0.6 pip, the 2024-26 session median)
   python -m forex.ea_research.usdjpy_spreadfix"""
import numpy as np
import pandas as pd

from forex.ea_research.breakouts import local_clock
from forex.ea_research.crt import load
from forex.ea_research.presample import tstat
from forex.ea_research.usdjpy_sens import run

END = pd.Timestamp("2026-10-17").timestamp()
PERIODS = (("2022", "2022-01-01", "2023-01-01"), ("2023", "2023-01-01", "2024-01-01"), ("2024", "2024-01-01", "2025-01-01"),
           ("DEV 2022-24", "2022-01-01", "2025-01-01"), ("VAL 2025", "2025-01-01", "2026-01-01"), ("2026", "2026-01-01", "2026-10-17"))


def respread(D, sp):
    E = dict(D)
    for a, b in (("ao", "bo"), ("ah", "bh"), ("al", "bl"), ("ac", "bc")):
        E[a] = D[b] + sp
    E["mh"], E["ml"], E["mc"] = (E["bh"] + E["ah"]) / 2, (E["bl"] + E["al"]) / 2, (E["bc"] + E["ac"]) / 2
    return E


def zero_fix(D):
    sp = D["ao"] - D["bo"]
    t = pd.to_datetime(D["t"], unit="s")
    f = pd.DataFrame({"sp": np.where(sp > 0, sp, np.nan), "mon": t.to_period("M"), "hr": t.hour})
    med = f.groupby(["mon", "hr"]).sp.median().unstack()
    prev = med.shift(1).fillna(med).bfill()                    # previous month, same server hour (causal; first month uses itself)
    fill = prev.stack().reindex(pd.MultiIndex.from_arrays([f.mon, f.hr])).to_numpy()
    out = np.where(sp > 0, sp, fill)
    assert np.isfinite(out).all()
    return out


def main():
    D = load("USDJPY", END)
    lc = local_clock(D["t"], "Europe/London")
    sp = D["ao"] - D["bo"]
    variants = {"A raw": D, "B zero fix": respread(D, zero_fix(D)), "C 0.6 pip floor": respread(D, np.maximum(sp, 0.006))}
    rows = []
    for name, E in variants.items():
        r = run(E, lc, 8, 30, 17)
        r = r[r.day >= "2022-01-01"]
        for p, a, b in PERIODS:
            x = r[(r.day >= a) & (r.day < b)].R
            rows.append(dict(variant=name, period=p, n=len(x), mean_R=x.mean(), t=tstat(x), win=(x > 0).mean()))
    T = pd.DataFrame(rows)
    print(T.pivot(index="period", columns="variant", values="mean_R").reindex([p[0] for p in PERIODS]).round(3).to_string())
    print("\nt by period:")
    print(T.pivot(index="period", columns="variant", values="t").reindex([p[0] for p in PERIODS]).round(2).to_string())
    print("\ntrades by period:")
    print(T.pivot(index="period", columns="variant", values="n").reindex([p[0] for p in PERIODS]).to_string())
    T.to_csv("C:/work/scratch/usdjpy_spreadfix.csv", index=False)


if __name__ == "__main__":
    main()
