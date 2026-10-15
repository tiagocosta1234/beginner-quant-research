"""COST-OOS exactly as in PREREG_COST_OOS.md: the box-width-in-spreads breakout filter on seven non-MT5 broker instruments (MT5 broker files).
   python -m forex.ea_research.cost_oos"""
import zlib
import numpy as np
import pandas as pd
from forex.ea_research.breakouts import local_clock
from forex.ea_research.brk_exits import exits
from forex.ea_research.index_oos import load_mt5broker
from forex.ea_research.ict2 import nw_t

H, M = 3600, 60
END = pd.Timestamp("2026-10-03").timestamp()
INST = {"UK100.cash": ("Europe/London", 8 * H, 16 * H + 30 * M), "FRA40.cash": ("Europe/Paris", 9 * H, 17 * H + 30 * M),
        "US2000.cash": ("America/New_York", 9 * H + 30 * M, 16 * H), "MSFT": ("America/New_York", 9 * H + 30 * M, 16 * H),
        "NVDA": ("America/New_York", 9 * H + 30 * M, 16 * H), "XPTUSD": ("Europe/London", 8 * H, 17 * H), "XPDUSD": ("Europe/London", 8 * H, 17 * H)}


def run_inst(sym):
    tz, op_s, cl_s = INST[sym]
    D = load_mt5broker(sym, END)
    t = D["t"]; lc = local_clock(t, tz)
    rows = []
    for d in np.unique(lc // 86400):
        base = d * 86400
        i0, i1 = np.searchsorted(lc, base + op_s), np.searchsorted(lc, base + op_s + 30 * M)
        w1 = np.searchsorted(lc, base + op_s + 3 * H)
        xe = np.searchsorted(lc, base + cl_s)
        if xe >= len(t) or lc[min(xe, len(t) - 1)] // 86400 != d:
            xe -= 1
        if i1 >= len(t) or i1 - i0 < 20 or lc[i0] // 86400 != d or w1 <= i1 + 30 or xe <= i1:
            continue
        cap = np.searchsorted(t, (t[i1] // 86400) * 86400 + 22 * H + 55 * M)
        kend = min(xe, cap, len(t) - 1)
        Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
        sp_med = np.median(D["ao"][i0:i1] - D["bo"][i0:i1])
        if not (Hb > Lb and sp_med > 0):
            continue
        up = np.flatnonzero(D["ah"][i1:w1] >= Hb); dn = np.flatnonzero(D["bl"][i1:w1] <= Lb)
        ku, kd = (i1 + up[0] if len(up) else None), (i1 + dn[0] if len(dn) else None)
        if (ku is None and kd is None) or (ku is not None and ku == kd):
            continue
        side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
        k = ku if side > 0 else kd
        e = max(Hb, D["ao"][k]) if side > 0 else min(Lb, D["bo"][k])
        R = abs(e - (Lb if side > 0 else Hb))
        if k >= kend or not (R > 0 and R >= 2 * (D["ao"][k] - D["bo"][k])):
            continue
        x = exits(D, k, kend, side, e, R)
        if x:
            rows.append(dict(mkt=sym, day=pd.Timestamp(d * 86400, unit="s"), box_spreads=(Hb - Lb) / sp_med, R=x[3], R_comm=x[3] - 0.5 * sp_med / R))
    return pd.DataFrame(rows)


def main():
    df = pd.concat([run_inst(s) for s in INST], ignore_index=True)
    df = df[df.day >= "2022-01-01"]
    df.to_parquet("D:/finance/si_ledgers/COST_OOS.parquet")
    tt = lambda x: x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan
    df["bin"] = pd.cut(df.box_spreads, [0, 10, 15, 25, 40, 60, 1e9], labels=["<10", "10-15", "15-25", "25-40", "40-60", ">60"])
    print("profile (net R with the commission assumption, by box width in spreads):")
    print(df.groupby("bin", observed=True).R_comm.agg(["size", "mean"]).round(3).T.to_string())
    for name, thr in (("K2 >= 40 spreads", 40), ("K1 >= 25 spreads", 25)):
        k = df[df.box_spreads >= thr]
        per = {m: (len(g), round(g.R_comm.mean(), 3)) for m, g in k.groupby("mkt")}
        pos = sum(1 for n, v in per.values() if n >= 30 and v > 0); elig = sum(1 for n, v in per.values() if n >= 30)
        dt_ = nw_t(k.groupby("day").R_comm.mean().to_numpy())
        g = [k.R_comm.mean() > 0 and tt(k.R_comm) >= 1.65 and dt_ >= 1.0, pos >= 4, k.R_comm.mean() - df.R_comm.mean() >= 0.05]
        print(f"\n{name}: n {len(k)} | net {k.R.mean():+.3f} R, with commission {k.R_comm.mean():+.3f} (trade t {tt(k.R_comm):+.2f}, daily t {dt_:+.2f}) | all boxes {df.R_comm.mean():+.3f} | "
              f"positive {pos}/{elig} instruments | gates {''.join('Y' if v else 'n' for v in g)} PASS {all(g)}")
        print("   by instrument (n, R):", per)
        print("   by year:", {y: f"{g_.R_comm.mean():+.3f} (n {len(g_)})" for y, g_ in k.groupby(k.day.dt.year)})


if __name__ == "__main__":
    main()
