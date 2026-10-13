"""Iteration 13 (pre-registered in lab/PREREG.md): reaction to the 8:30 ET (server 15:30) US data-release slot, all weekdays, FX6 / XAUUSD / IDX4.   python -m forex.intraday_lab.iter13_release"""
from __future__ import annotations

import numpy as np
import pandas as pd

from forex.intraday_lab.iter11_sessions import daily_atr
from forex.intraday_lab.lab import FX, Bars, commission_price

CLASSES = {"FX6": FX, "XAU": ("XAUUSD",), "IDX4": ("US100.cash", "US30.cash", "US500.cash", "GER40.cash")}
OPEN = 15 * 60 + 30; WS = (5, 15); HS = (30, 60, 120)


def sym_trades(sym):
    b = Bars(sym, 5); atr = daily_atr(sym); rows = []
    for dd in np.unique(b.day):
        dow = (dd + 4) % 7
        if dow > 4:
            continue
        a = atr.get(pd.Timestamp(dd * 86400, unit="s"), np.nan)
        t0 = dd * 86400 + OPEN * 60; i0 = int(np.searchsorted(b.t, t0))
        if not np.isfinite(a) or i0 >= b.n or b.t[i0] != t0:
            continue
        for W in WS:
            iw = int(np.searchsorted(b.t, t0 + W * 60))
            if iw >= b.n or b.t[iw] != t0 + W * 60:
                continue
            drive = (b.mid[iw] - b.mid[i0]) / a
            for H in HS:
                ie = int(np.searchsorted(b.t, t0 + (W + H) * 60))
                if ie >= b.n or b.t[ie] != t0 + (W + H) * 60:
                    continue
                rows.append(dict(sym=sym, day=dd, dow=dow, W=W, H=H, drive=drive, fwd=(b.mid[ie] - b.mid[iw]) / a, cost=((b.ao[iw] - b.bo[iw]) + commission_price(sym, float(b.mid[iw]))) / a, year=int(b.year[iw])))
    return pd.DataFrame(rows)


def main():
    out = []
    for cls, syms in CLASSES.items():
        T = pd.concat([sym_trades(s) for s in syms])
        for hyp, sg in (("mom", 1), ("fade", -1)):
            T["sig"] = np.sign(T.drive) * sg * T.fwd; T["net"] = T.sig - T.cost
            D = T.groupby(["day", "W", "H"]).agg(sig=("sig", "mean"), net=("net", "mean"), year=("year", "first"), dow=("dow", "first")).reset_index()
            D["phase"] = np.where(D.year <= 2023, "dev", np.where(D.year == 2024, "val", "hold"))
            for (W, H, ph), x in D.groupby(["W", "H", "phase"]):
                out.append(dict(cls=cls, hyp=hyp, W=W, H=H, phase=ph, n=len(x), sig=x.sig.mean(), net=x.net.mean(), t=x.net.mean() / (x.net.std(ddof=1) / np.sqrt(len(x))) if len(x) > 3 else np.nan, cost=(x.sig - x.net).mean()))
    R = pd.DataFrame(out); R.to_csv(r"D:\finance\scratch\lab\iter13_raw.csv", index=False)
    P = R.pivot_table(index=["cls", "hyp", "W", "H"], columns="phase", values=["n", "sig", "net", "t", "cost"]); P.columns = [f"{a}_{b}" for a, b in P.columns]; P = P.reset_index()
    print("K =", len(P))
    hit = P[(P.net_dev > 0) & (P.t_dev >= 3.6) & (P.net_val > 0) & (P.t_val >= 2)]
    cols = ["cls", "hyp", "W", "H", "n_dev", "net_dev", "t_dev", "n_val", "net_val", "t_val", "net_hold", "t_hold", "cost_dev"]
    print("PRE-REGISTERED HITS:", len(hit)); print(hit[cols].round(4).to_string(index=False) if len(hit) else "none")
    print("\nTop 8 by DEV t (learning only):"); print(P.sort_values("t_dev", ascending=False)[cols].head(8).round(4).to_string(index=False))
    print("\nshare of cells with DEV net > 0 by class / hypothesis:"); print(P.groupby(["cls", "hyp"]).apply(lambda x: (x.net_dev > 0).mean(), include_groups=False).round(2).to_string())


if __name__ == "__main__":
    main()
