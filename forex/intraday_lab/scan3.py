"""Iteration 3 (pre-registered in lab/PREREG.md): index dip-buy with an unconditional-long control.   python -m forex.intraday_lab.scan3"""
from __future__ import annotations

from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

from forex.intraday_lab.lab import Bars, commission_price

OUT = Path(r"D:\finance\scratch\lab")
SYMS = ("US100.cash", "US30.cash", "US500.cash", "GER40.cash", "XAUUSD")
HS = {5: (12, 24, 48), 15: (4, 8, 16)}


def one(args):
    sym, tf = args
    b = Bars(sym, tf); atr = b.atr(14); s = pd.Series(b.mid)
    f = {f"ret{k}": ((s - s.shift(k)) / pd.Series(atr)).values for k in (1, 3, 12)}
    hh = pd.Series(b.bh).rolling(96).max(); ll = pd.Series(b.bl).rolling(96).min(); f["rngpos"] = ((s - ll) / (hh - ll)).values
    ph = {p: b.slice_idx(p) for p in ("dev", "val", "hold")}
    comm = commission_price(sym, float(np.nanmedian(b.mid)))
    rows = []
    for h in HS[tf]:
        fwd = np.full(b.n, np.nan); ok = np.arange(b.n - h)
        fwd[ok] = (b.mid[ok + h] - b.mid[ok]) / atr[ok]; fwd[ok[(b.t[ok + h] - b.t[ok]) > h * tf * 60 * 3]] = np.nan
        cost = ((b.ao - b.bo) + comm) / atr
        for name, v in f.items():
            thr = np.nanpercentile(v[ph["dev"]], 10)
            for p, ix in ph.items():
                base = ix[np.isfinite(fwd[ix])][::h]; cond = ix[(v[ix] <= thr) & np.isfinite(fwd[ix])][::h]
                rows.append(dict(sym=sym, tf=tf, feat=name, h=h, phase=p, n=len(cond), cond=float(np.mean(fwd[cond])), cond_sd=float(np.std(fwd[cond], ddof=1)), un=float(np.mean(fwd[base])), un_sd=float(np.std(fwd[base], ddof=1)), nb=len(base), cost=float(np.nanmean(cost[cond]))))
    return rows


def main():
    with Pool(4) as p:
        res = p.map(one, [(s, tf) for tf in (5, 15) for s in SYMS])
    d = pd.DataFrame([r for x in res for r in x]); d.to_csv(OUT / "scan3_raw.csv", index=False)
    d["excess"] = d.cond - d.un; d["se"] = np.sqrt(d.cond_sd ** 2 / d.n + d.un_sd ** 2 / d.nb); d["net"] = d.cond - d.cost
    out = []
    for (tf, feat, h), g in d[d.sym != "XAUUSD"].groupby(["tf", "feat", "h"]):
        row = dict(tf=tf, feat=feat, h=h)
        for p in ("dev", "val", "hold"):
            x = g[g.phase == p]; N = x.n.sum()
            ex = (x.n * x.excess).sum() / N; se = np.sqrt(((x.n * x.se) ** 2).sum()) / N
            net = (x.n * x.net).sum() / N; nse = np.sqrt(((x.n * x.cond_sd / np.sqrt(x.n)) ** 2).sum()) / N
            row.update({f"{p}_excess": ex, f"{p}_t": ex / se, f"{p}_net": net, f"{p}_net_t": net / nse, f"{p}_pos": int((x.excess > 0).sum()), f"{p}_n": int(N)})
        out.append(row)
    R = pd.DataFrame(out); R.to_csv(OUT / "scan3_summary.csv", index=False)
    print("tests K =", len(R))
    hit = R[(R.dev_t >= 3) & (R.dev_net > 0) & (R.val_t >= 2) & (R.val_net > 0) & (R.dev_pos >= 3) & (R.val_pos >= 3)]
    print("PRE-REGISTERED HITS (dev + val):", len(hit))
    cols = ["tf", "feat", "h", "dev_excess", "dev_t", "dev_net", "val_excess", "val_t", "val_net", "dev_pos", "val_pos", "hold_excess", "hold_t", "hold_net", "hold_net_t", "hold_pos"]
    print(hit[cols].round(3).to_string(index=False) if len(hit) else "none")
    print("\nAll tests, sorted by dev t:"); print(R.sort_values("dev_t", ascending=False)[cols].round(3).to_string(index=False))
    x = d[(d.sym == "XAUUSD")].assign(excess=lambda z: z.cond - z.un)
    print("\nXAUUSD check (net = cond - cost) by feat/h on dev/val/hold:")
    print(x.pivot_table(index=["tf", "feat", "h"], columns="phase", values="net").round(3).to_string())


if __name__ == "__main__":
    main()
