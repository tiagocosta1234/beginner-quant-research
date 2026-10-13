"""Iteration 11 (pre-registered in lab/PREREG.md): cash-open drive on the indices with holds of hours, normalised by the daily range.   python -m forex.intraday_lab.iter11_sessions"""
from __future__ import annotations

from itertools import product

import numpy as np
import pandas as pd

from forex.intraday_lab.lab import Bars

GROUPS = {"US": (("US100.cash", "US30.cash", "US500.cash"), 16 * 60 + 30), "EU": (("GER40.cash",), 10 * 60)}
WS = (15, 30, 60); HS = (120, 240, 360)


def daily_atr(sym):
    m = pd.read_parquet(f"forex/data/{sym}_M1_ticks_full.parquet", columns=["time", "high", "low"]); idx = pd.to_datetime(m.time, unit="s")
    h = pd.Series(m.high.values, index=idx).resample("1D").max(); l = pd.Series(m.low.values, index=idx).resample("1D").min()
    return (h - l).dropna().rolling(20).mean().shift(1)


def sym_trades(sym, open_min):
    b = Bars(sym, 5); atr = daily_atr(sym); rows = []
    for dd in np.unique(b.day):
        a = atr.get(pd.Timestamp(dd * 86400, unit="s"), np.nan)
        if not np.isfinite(a):
            continue
        t0 = dd * 86400 + open_min * 60; i0 = int(np.searchsorted(b.t, t0))
        if i0 >= b.n or b.t[i0] != t0:
            continue
        for W in WS:
            iw = int(np.searchsorted(b.t, t0 + W * 60))
            if iw >= b.n or b.t[iw] != t0 + W * 60:
                continue
            drive = (b.mid[iw] - b.bo[i0] * 0.5 - b.ao[i0] * 0.5) / a
            for H in HS:
                ie = int(np.searchsorted(b.t, t0 + (W + H) * 60))
                if ie >= b.n or b.t[ie] != t0 + (W + H) * 60:
                    continue
                rows.append(dict(sym=sym, day=dd, W=W, H=H, drive=drive, fwd=(b.mid[ie] - b.mid[iw]) / a, cost=(b.ao[iw] - b.bo[iw]) / a, year=int(b.year[iw])))
    return pd.DataFrame(rows)


def main():
    out = []
    for g, (syms, om) in GROUPS.items():
        T = pd.concat([sym_trades(s, om) for s in syms])
        for hyp, sg in (("mom", 1), ("fade", -1)):
            T["sig"] = np.sign(T.drive) * sg * T.fwd; T["net"] = T.sig - T.cost
            D = T.groupby(["day", "W", "H"]).agg(sig=("sig", "mean"), net=("net", "mean"), year=("year", "first")).reset_index()
            D["phase"] = np.where(D.year <= 2023, "dev", np.where(D.year == 2024, "val", "hold"))
            for (W, H, ph), x in D.groupby(["W", "H", "phase"]):
                out.append(dict(group=g, hyp=hyp, W=W, H=H, phase=ph, n=len(x), sig=x.sig.mean(), net=x.net.mean(), t=x.net.mean() / (x.net.std(ddof=1) / np.sqrt(len(x))) if len(x) > 3 else np.nan, cost=(x.sig - x.net).mean()))
    R = pd.DataFrame(out); R.to_csv(r"D:\finance\scratch\lab\iter11_raw.csv", index=False)
    P = R.pivot_table(index=["group", "hyp", "W", "H"], columns="phase", values=["n", "sig", "net", "t", "cost"]); P.columns = [f"{a}_{b}" for a, b in P.columns]; P = P.reset_index()
    print("K =", len(P))
    hit = P[(P.net_dev > 0) & (P.t_dev >= 3.6) & (P.net_val > 0) & (P.t_val >= 2)]
    cols = ["group", "hyp", "W", "H", "n_dev", "net_dev", "t_dev", "n_val", "net_val", "t_val", "net_hold", "t_hold", "cost_dev"]
    print("PRE-REGISTERED HITS:", len(hit)); print(hit[cols].round(4).to_string(index=False) if len(hit) else "none")
    print("\nTop 8 by DEV t (learning only):"); print(P.sort_values("t_dev", ascending=False)[cols].head(8).round(4).to_string(index=False))
    print("\nmedian cost in daily-ATR units:", round(P.cost_dev.median(), 4), "| median |signed mean| dev:", round(P.sig_dev.abs().median(), 4), "| share dev>0 by hyp:", P.groupby("hyp").apply(lambda x: (x.net_dev > 0).mean(), include_groups=False).round(2).to_dict())


if __name__ == "__main__":
    main()
