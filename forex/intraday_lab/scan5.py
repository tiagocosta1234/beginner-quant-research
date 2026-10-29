"""Iteration 5 (pre-registered in lab/PREREG.md): gold long AND short fades at 15 minutes, holds 4 / 8 / 24 hours, with a same-sign unconditional control.   python -m forex.intraday_lab.scan5"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from forex.intraday_lab.lab import ALL, Bars, commission_price

OUT = Path(r"data\scratch\lab")
TF = 15; HS = (16, 32, 96)


def run(sym):
    b = Bars(sym, TF); atr = b.atr(14); s = pd.Series(b.mid)
    f = {f"ret{k}": ((s - s.shift(k)) / pd.Series(atr)).values for k in (1, 3, 12)}
    ph = {p: b.slice_idx(p) for p in ("dev", "val", "hold")}
    comm = commission_price(sym, float(np.nanmedian(b.mid))); cost = ((b.ao - b.bo) + comm) / atr
    rows = []
    for h in HS:
        fwd = np.full(b.n, np.nan); ok = np.arange(b.n - h); fwd[ok] = (b.mid[ok + h] - b.mid[ok]) / atr[ok]; fwd[ok[(b.t[ok + h] - b.t[ok]) > h * TF * 60 * 3]] = np.nan
        for name, v in f.items():
            lo, hi = np.nanpercentile(v[ph["dev"]], [10, 90])
            for tail, mask, sgn in (("low->long", v <= lo, 1), ("high->short", v >= hi, -1)):
                for p, ix in ph.items():
                    base = ix[np.isfinite(fwd[ix])][::h]; cond = ix[mask[ix] & np.isfinite(fwd[ix])][::h]
                    c = sgn * fwd[cond]; u = sgn * fwd[base]
                    rows.append(dict(sym=sym, feat=name, h=h, tail=tail, phase=p, n=len(cond), cond=float(c.mean()), un=float(u.mean()), excess=float(c.mean() - u.mean()),
                                     se=float(np.sqrt(c.var(ddof=1) / len(c) + u.var(ddof=1) / len(u))), net=float(c.mean() - np.nanmean(cost[cond])), cost=float(np.nanmean(cost[cond]))))
    return rows


def main():
    D = pd.DataFrame([r for s in ALL for r in run(s)]); D["t"] = D.excess / D.se; D.to_csv(OUT / "scan5_raw.csv", index=False)
    g = D[D.sym == "XAUUSD"].pivot_table(index=["feat", "h", "tail"], columns="phase", values=["excess", "t", "net", "cond", "un"]); g.columns = [f"{a}_{b}" for a, b in g.columns]; g = g.reset_index()
    print("K =", len(g))
    hit = g[(g.t_dev >= 3) & (g.net_dev > 0) & (g.t_val >= 2) & (g.net_val > 0)]
    cols = ["feat", "h", "tail", "cond_dev", "un_dev", "excess_dev", "t_dev", "net_dev", "excess_val", "t_val", "net_val", "excess_hold", "t_hold", "net_hold"]
    print("PRE-REGISTERED HITS:", len(hit)); print(hit[cols].round(3).to_string(index=False) if len(hit) else "none")
    print("\nXAUUSD all tests by dev t:"); print(g.sort_values("t_dev", ascending=False)[cols].round(3).to_string(index=False))
    o = D[D.sym != "XAUUSD"].groupby(["feat", "h", "tail", "phase"]).apply(lambda x: pd.Series(dict(excess=np.average(x.excess, weights=x.n), t=(x.excess * x.n).sum() / np.sqrt(((x.se * x.n) ** 2).sum()), pos=int((x.excess > 0).sum()))), include_groups=False).reset_index()
    p = o.pivot_table(index=["feat", "h", "tail"], columns="phase", values=["excess", "t", "pos"]); p.columns = [f"{a}_{b}" for a, b in p.columns]
    print("\nOther 10 symbols pooled (control, same rule): best by dev t"); print(p.sort_values("t_dev", ascending=False).head(6).round(3).to_string())


if __name__ == "__main__":
    main()
