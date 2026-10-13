"""Iteration 14 (pre-registered in lab/PREREG.md): the Stochastic Daily Breakout port on all symbols (ATR-scaled stop / target) and the gold original in R units.   python -m forex.intraday_lab.iter14_sdb"""
from __future__ import annotations

from multiprocessing import Pool

import numpy as np
import pandas as pd

from forex.intraday_lab import sdb
from forex.intraday_lab.lab import ALL

KS = (0.5, 0.75, 1.0, 1.5)


def phase(y):
    return "dev" if y <= 2023 else ("val" if y == 2024 else "hold")


def one(sym):
    m1 = sdb.load_m1(sym); rows = []
    for k in KS:
        T = sdb.simulate(sym, m1, atr_stop=k)
        if len(T):
            T["phase"] = T.year.map(phase)
            for ph, x in T.groupby("phase"):
                rows.append(dict(sym=sym, k=k, phase=ph, n=len(x), mean=x.R.mean(), sd=x.R.std(ddof=1) if len(x) > 2 else np.nan, win=(x.R > 0).mean()))
    if sym == "XAUUSD":
        T = sdb.simulate(sym, m1); T["phase"] = T.year.map(phase); T.to_csv(r"D:\finance\scratch\lab\iter14_gold_original.csv", index=False)
    return rows


def main():
    with Pool(4) as p:
        D = pd.DataFrame([r for x in p.map(one, list(ALL)) for r in x])
    D.to_csv(r"D:\finance\scratch\lab\iter14_raw.csv", index=False)
    print("TEST A: per symbol mean R (n) by k and phase")
    P = D.pivot_table(index=["k", "sym"], columns="phase", values=["mean", "n"]); P.columns = [f"{a}_{b}" for a, b in P.columns]; print(P.round(3).to_string())
    o = D[(D.sym != "XAUUSD") & (D.n >= 20)]; out = []
    for (k, ph), x in o.groupby(["k", "phase"]):
        N = x.n.sum(); m = (x.n * x["mean"]).sum() / N; se = np.sqrt((((x.sd / np.sqrt(x.n)) * x.n) ** 2).sum()) / N
        out.append(dict(k=k, phase=ph, n=int(N), pooled=m, t=m / se, pos=int((x["mean"] > 0).sum()), syms=len(x)))
    Q = pd.DataFrame(out).pivot_table(index="k", columns="phase", values=["n", "pooled", "t", "pos", "syms"]); Q.columns = [f"{a}_{b}" for a, b in Q.columns]; Q = Q.reset_index()
    print("\nPOOLED over the 10 non-gold symbols:"); print(Q.round(3).to_string(index=False))
    hit = Q[(Q.pooled_dev > 0) & (Q.pooled_val > 0) & (Q.t_val >= 2.5) & (Q.pos_dev >= 7) & (Q.pos_val >= 7)]
    print("\nPRE-REGISTERED MULTI-SYMBOL HITS:", len(hit)); print(hit.round(3).to_string(index=False) if len(hit) else "none")
    g = pd.read_csv(r"D:\finance\scratch\lab\iter14_gold_original.csv")
    print("\nTEST B: gold original (1.9%) in R units")
    print(g.groupby("year").agg(n=("R", "size"), meanR=("R", "mean"), win=("R", lambda x: (x > 0).mean()), long=("side", lambda x: (x > 0).mean())).round(3).to_string())
    print(g.groupby("phase").agg(n=("R", "size"), meanR=("R", "mean"), t=("R", lambda x: x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))).round(3).to_string())
    print(g.groupby("side").agg(n=("R", "size"), meanR=("R", "mean")).round(3).to_string())


if __name__ == "__main__":
    main()
