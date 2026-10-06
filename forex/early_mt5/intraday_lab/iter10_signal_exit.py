"""Iteration 10 (pre-registered in lab/PREREG.md): TP5 entries with signal exits (mean-cross or short-term recovery), wide safety stop.   python -m mt5broker.intraday_lab.iter10_signal_exit"""
from __future__ import annotations

from itertools import product
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.intraday_lab.lab import ALL, Bars, run, stats

OUT = Path(r"D:\finance\scratch\lab")


def next_true(cond, idx, cap):
    """For each signal index, bars until the first later bar where cond is true (capped)."""
    t = np.flatnonzero(cond); out = np.full(len(idx), cap)
    j = np.searchsorted(t, idx + 1)
    ok = j < len(t); out[ok] = np.minimum(cap, t[j[ok]] - idx[ok] + 0)
    return np.maximum(out, 2)


def one(sym):
    b = Bars(sym, 5); atr = b.atr(14); s = pd.Series(b.mid)
    r = lambda k: ((s - s.shift(k)) / pd.Series(atr)).values
    r96, r48, r3 = r(96), r(48), r(3)
    hh = pd.Series(b.bh).rolling(96).max(); ll = pd.Series(b.bl).rolling(96).min(); pos = ((s - ll) / (hh - ll)).values
    z = ((s - s.rolling(20).mean()) / s.rolling(20).std()).values
    masks = {p: np.zeros(b.n, bool) for p in ("dev", "val", "hold")}
    for p in masks:
        masks[p][b.slice_idx(p)] = True
    asia = (b.hour >= 1) & (b.hour < 5); rows = []
    for A, ex, stopm, sess in product((5, 10), ("E1", "E2"), (6, 10), ("all", "asia")):
        cl = (r96 >= A) & (r48 > 0) & (pos > 0.5) & (r3 < -0.5); cs = (r96 <= -A) & (r48 < 0) & (pos < 0.5) & (r3 > 0.5)
        if sess == "asia":
            cl &= asia; cs &= asia
        il = np.flatnonzero(cl); is_ = np.flatnonzero(cs)
        xl = (z >= 0) if ex == "E1" else (r3 >= 0.5); xs = (z <= 0) if ex == "E1" else (r3 <= -0.5)
        mbl = next_true(xl, il, 288); mbs = next_true(xs, is_, 288)
        idx = np.r_[il, is_]; d = np.r_[np.ones(len(il), int), -np.ones(len(is_), int)]; mb = np.r_[mbl, mbs]; o = np.argsort(idx); idx, d, mb = idx[o], d[o], mb[o]
        stop = stopm * atr[idx]
        for p, m in masks.items():
            R, ent, ext, yrs, cst = run(b, idx, d, stop, 1000.0, mb, 0.0, m)
            R = R * stopm                                     # R -> ATR units
            c = cst * stopm
            rows.append(dict(sym=sym, A=A, exit=ex, stop=stopm, sess=sess, phase=p, **stats(R, yrs, c)))
    return rows


def main():
    with Pool(4) as p:
        D = pd.DataFrame([r for x in p.map(one, list(ALL)) for r in x])
    D.to_csv(OUT / "iter10_raw.csv", index=False)
    key = ["A", "exit", "stop", "sess"]
    g = D[D.sym == "XAUUSD"].pivot_table(index=key, columns="phase", values=["n", "mean", "t", "pf", "cost"]); g.columns = [f"{a}_{b}" for a, b in g.columns]; g = g.reset_index()
    print("K =", len(g))
    hit = g[(g.t_val >= 2.8) & (g.mean_val > 0) & (g.mean_dev >= 0)]
    cols = key + ["n_dev", "mean_dev", "t_dev", "n_val", "mean_val", "t_val", "pf_val", "n_hold", "mean_hold", "t_hold", "pf_hold", "cost_val"]
    print("GOLD HITS:", len(hit)); print(hit[cols].round(3).to_string(index=False) if len(hit) else "none")
    print("\nGOLD top 8 by VAL t:"); print(g.sort_values("t_val", ascending=False)[cols].head(8).round(3).to_string(index=False))
    o = D[(D.sym != "XAUUSD") & (D.n >= 30)]; rows = []
    for k, x in o.groupby(key + ["phase"]):
        N = x.n.sum(); m = (x.n * x["mean"]).sum() / N; se = np.sqrt((((x["mean"] / x.t).abs().fillna(0) * x.n) ** 2).sum()) / N
        rows.append(dict(zip(key + ["phase"], k), pooled=m, t=m / se if se > 0 else np.nan, pos=int((x["mean"] > 0).sum())))
    O = pd.DataFrame(rows).pivot_table(index=key, columns="phase", values=["pooled", "t", "pos"]); O.columns = [f"{a}_{b}" for a, b in O.columns]
    multi = O[(O.t_val >= 2) & (O.pos_val >= 7)]
    print("\nMULTI-SYMBOL cells (VAL pooled t >= 2 and >= 7 of 10 positive):", len(multi)); print(multi.round(3).to_string() if len(multi) else "none")
    print("\nOther 10 symbols best 5 by VAL pooled t:"); print(O.sort_values("t_val", ascending=False).head(5).round(3).to_string())
    print("\nmedian mean (ATR units, VAL) over cells with n > 50:", round(D[(D.phase == 'val') & (D.n > 50)]['mean'].median(), 3), "| median cost (ATR units):", round(D[(D.phase == 'val') & (D.n > 50)].cost.median(), 3))


if __name__ == "__main__":
    main()
