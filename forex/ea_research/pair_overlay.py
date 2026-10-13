"""Regime overlay on the pair's size, exactly as registered in PREREG_PAIR_OVERLAY.md.   python -m forex.ea_research.pair_overlay
Builds the MT5-based 2022-26 minute series once, runs the constant-size series for m = 0.6 / 1.0 / 1.2 (both caps, carry-over), splices the days by the overlay state and prints pass / breach / speed for ALL 2022-26 and PRE-BOOM 2022-24."""
import sys
sys.argv = ["x", "--source", "mt5broker"]
import numpy as np
import pandas as pd

from forex.ea_batch import mt5_combo_v2 as V2
from forex.ea_batch.mt5_mc_config import CH
from forex.ea_batch import mt5data_guard_carry as GC
from forex.ea_batch.mt5data_sizing_long import trades_mt5broker

A, CAPD = 100_000.0, 2_000.0


def metrics(V, B, mask):
    Vy, By = V[mask], B[mask]; N = len(Vy); res = []
    for i0 in range(N):
        bal, cnt, out = A, 0.0, None
        for k in range(i0, N):
            if By[k] <= -0.025 * A or bal + By[k] <= 0.92 * A: out = ("breach", k - i0 + 1); break
            x = min(Vy[k], CAPD) if Vy[k] > 0 else Vy[k]; bal += x; cnt += x
            if cnt >= 0.08 * A: out = ("pass", k - i0 + 1); break
        res.append(out)
    d = np.array([n for s, n in [r for r in res if r] if s == "pass"]); br = sum(1 for r in res if r and r[0] == "breach"); n = len(res)
    return f"starts {n}: pass {len(d)} ({100*len(d)/n:.0f}%), breach {br} ({100*br/n:.0f}%), median {np.median(d):.0f} bd, <=42 bd {100*(d<=42).sum()/n:.0f}%, <=62 bd {100*(d<=62).sum()/n:.0f}%"


def main():
    U, E1, R1, st, days = V2.build_ns({"77900": 1.0, "mkt_xau5min": 0.0}, True); _, E2, R2, _, _ = V2.build_ns({"77900": 0.0, "mkt_xau5min": 1.0}, True); S = {}
    for m in (0.6, 1.0, 1.2):
        lots = {k: v * m for k, v in CH.items()}; trs = [trades_mt5broker("77900", lots["sdb"]), trades_mt5broker("mkt_xau5min", lots["xau5"])]; S[m] = GC.series(U, E1, R1, E2, R2, st, lots, trs, CAPD, CAPD, 0.0)
    d = pd.DatetimeIndex(S[1.0]["days"]); K = len(d); V = {m: S[m]["V"] for m in S}; B = {m: S[m]["B"] for m in S}
    g = pd.read_parquet("forex/data_mt5/XAUUSD_M1_rates.parquet", columns=["t", "bc"]).sort_values("t"); g["day"] = pd.to_datetime(g.t // 86400, unit="D"); close = g.groupby("day").bc.last(); sma = close.rolling(100).mean()
    o1 = np.ones(K); o2 = np.ones(K); cum = np.cumsum(V[1.0]); cma = pd.Series(cum).rolling(20).mean().to_numpy()
    for k in range(1, K):
        p = d[k - 1]
        if p in close.index and not np.isnan(sma.get(p, np.nan)): o1[k] = 1.2 if close[p] > sma[p] else 0.6
        if not np.isnan(cma[k - 1]): o2[k] = 1.2 if cum[k - 1] > cma[k - 1] else 0.6
    def splice(mult):
        Vs = np.array([V[mult[k]][k] if mult[k] in V else V[1.0][k] for k in range(K)]); Bs = np.array([B[mult[k]][k] if mult[k] in B else B[1.0][k] for k in range(K)]); return Vs, Bs
    pools = {"ALL 2022-26": (d >= pd.Timestamp("2022-01-01")), "PRE-BOOM 2022-24": (d >= pd.Timestamp("2022-01-01")) & (d < pd.Timestamp("2025-01-01"))}
    for name, mult in (("constant 1.0", np.full(K, 1.0)), ("constant 1.2", np.full(K, 1.2)), ("O1 gold trend (SMA100)", o1), ("O2 pair equity curve (MA20)", o2)):
        Vs, Bs = splice(mult)
        for pn, mask in pools.items():
            print(f"{name:28s} {pn:>16}: P&L {Vs[np.asarray(mask)].sum():9,.0f} | share of days at 1.2 {100*np.mean(mult[np.asarray(mask)] == 1.2):3.0f}% / 0.6 {100*np.mean(mult[np.asarray(mask)] == 0.6):3.0f}% | {metrics(Vs, Bs, np.asarray(mask))}", flush=True)


if __name__ == "__main__":
    main()
