"""Iteration 6 (pre-registered in lab/PREREG.md): with-trend pullback on 5-minute bars (the structure found in the pair's EA entries), gold plus the 10 other symbols as the multi-symbol test.   python -m forex.intraday_lab.scan6"""
from __future__ import annotations

from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

from forex.intraday_lab.lab import ALL, Bars, commission_price

OUT = Path(r"data\scratch\lab")
TF = 5; HS = (48, 96, 288); AS = (5, 10); PULL = {"P1": 0.0, "P2": 0.5}


def thin(ix, h):
    out = []; last = -10**9
    for i in ix:
        if i - last >= h:
            out.append(i); last = i
    return np.array(out, dtype=np.int64)


def one(sym):
    b = Bars(sym, TF); atr = b.atr(14); s = pd.Series(b.mid)
    r = lambda k: ((s - s.shift(k)) / pd.Series(atr)).values
    r96, r48, r3 = r(96), r(48), r(3)
    hh = pd.Series(b.bh).rolling(96).max(); ll = pd.Series(b.bl).rolling(96).min(); pos = ((s - ll) / (hh - ll)).values
    ph = {p: b.slice_idx(p) for p in ("dev", "val", "hold")}; comm = commission_price(sym, float(np.nanmedian(b.mid))); cost = ((b.ao - b.bo) + comm) / atr
    rows = []
    for h in HS:
        fwd = np.full(b.n, np.nan); ok = np.arange(b.n - h); fwd[ok] = (b.mid[ok + h] - b.mid[ok]) / atr[ok]; fwd[ok[(b.t[ok + h] - b.t[ok]) > h * TF * 60 * 3]] = np.nan
        for A in AS:
            lt = (r96 >= A) & (r48 > 0) & (pos > 0.5); st = (r96 <= -A) & (r48 < 0) & (pos < 0.5)
            for pn, pv in list(PULL.items()) + [("none", None)]:
                if pv is None:
                    cl, cs = lt, st
                else:
                    cl, cs = lt & (r3 < -pv), st & (r3 > pv)
                sign = np.where(cl, 1.0, np.where(cs, -1.0, 0.0))
                for p, ix in ph.items():
                    m = ix[(sign[ix] != 0) & np.isfinite(fwd[ix])]
                    sel = thin(m, h)
                    if len(sel) < 5:
                        rows.append(dict(sym=sym, h=h, A=A, pull=pn, phase=p, n=len(sel), sig=np.nan, sd=np.nan, drift=np.nan, cost=np.nan, longs=0)); continue
                    sg = sign[sel] * fwd[sel]
                    allb = ix[np.isfinite(fwd[ix])][::h]
                    drift = float(np.mean(np.where(sign[sel] > 0, 1, -1) * 0 + sign[sel] * np.mean(fwd[allb])))     # signed unconditional drift for the same mix of sides
                    rows.append(dict(sym=sym, h=h, A=A, pull=pn, phase=p, n=len(sel), sig=float(sg.mean()), sd=float(sg.std(ddof=1)), drift=drift, cost=float(np.nanmean(cost[sel])), longs=int((sign[sel] > 0).sum())))
    return rows


def main():
    with Pool(4) as p:
        D = pd.DataFrame([r for x in p.map(one, list(ALL)) for r in x])
    D.to_csv(OUT / "scan6_raw.csv", index=False)
    D["excess"] = D.sig - D.drift; D["net"] = D.sig - D.cost; D["se"] = D.sd / np.sqrt(D.n)
    g = D[(D.sym == "XAUUSD") & (D.pull != "none")].pivot_table(index=["h", "A", "pull"], columns="phase", values=["n", "sig", "drift", "excess", "net", "se"])
    g.columns = [f"{a}_{b}" for a, b in g.columns]; g = g.reset_index()
    for p in ("dev", "val", "hold"):
        g[f"t_{p}"] = g[f"excess_{p}"] / g[f"se_{p}"]
    print("K =", len(g))
    hit = g[(g.t_val >= 2.9) & (g.net_val > 0)]
    cols = ["h", "A", "pull", "n_dev", "sig_dev", "excess_dev", "t_dev", "n_val", "sig_val", "excess_val", "t_val", "net_val", "n_hold", "sig_hold", "excess_hold", "t_hold", "net_hold"]
    print("GOLD pre-registered HITS (VAL t >= 2.9 and net > 0):", len(hit)); print(hit[cols].round(3).to_string(index=False) if len(hit) else "none")
    print("\nGOLD all 12 tests:"); print(g[cols].round(3).to_string(index=False))
    t = D[(D.sym == "XAUUSD") & (D.pull == "none")].pivot_table(index=["h", "A"], columns="phase", values=["n", "sig", "net"]); t.columns = [f"{a}_{b}" for a, b in t.columns]
    print("\nGOLD control: trend only (no pullback):"); print(t.round(3).to_string())
    o = D[(D.sym != "XAUUSD") & (D.pull != "none") & (D.n >= 30)]
    rows = []
    for (h, A, pn, p), x in o.groupby(["h", "A", "pull", "phase"]):
        N = x.n.sum(); sig = (x.n * x.sig).sum() / N; se = np.sqrt(((x.sd * np.sqrt(x.n)) ** 2).sum()) / N
        rows.append(dict(h=h, A=A, pull=pn, phase=p, n=int(N), pooled_sig=sig, t=sig / se, pos=int((x.sig > 0).sum()), syms=len(x), net=(x.n * x.net).sum() / N))
    O = pd.DataFrame(rows).pivot_table(index=["h", "A", "pull"], columns="phase", values=["n", "pooled_sig", "t", "pos", "net"]); O.columns = [f"{a}_{b}" for a, b in O.columns]
    print("\nOTHER 10 SYMBOLS pooled (signed forward return, ATR units), by phase:"); print(O[["pooled_sig_dev", "t_dev", "pos_dev", "pooled_sig_val", "t_val", "pos_val", "net_val", "pooled_sig_hold", "t_hold", "pos_hold", "net_hold"]].round(3).to_string())
    print("\nPer symbol (h=96, A=5, P1) VAL / HOLD signed mean and n:")
    q = D[(D.h == 96) & (D.A == 5) & (D.pull == "P1") & D.phase.isin(["val", "hold"])].pivot_table(index="sym", columns="phase", values=["sig", "n"]); print(q.round(3).to_string())


if __name__ == "__main__":
    main()
