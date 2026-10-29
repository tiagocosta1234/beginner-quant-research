"""BRK-REGIME exactly as in PREREG_BRK_REGIME.md: market-wide climate filters (global volatility, cross-market trendiness) on session breakouts.
   python -m forex.ea_research.brk_regime"""
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from forex.ea_research.brk_xs import closes
from forex.ea_research.ict2 import SYMS, nw_t

P = {"DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "2026": ("2026-01-01", "2026-10-02")}


def main():
    with ProcessPoolExecutor(8) as ex:
        C = pd.DataFrame(dict(ex.map(closes, SYMS))).sort_index().ffill(limit=3)
    r = np.log(C).diff()
    eq = r[["SP", "NSDQ", "DAX"]].mean(axis=1)
    gv = eq.rolling(20).std() * np.sqrt(252)
    tr = (r.rolling(20).sum().abs() / (r.rolling(20).std() * np.sqrt(20))).mean(axis=1)
    rank = lambda s: s.rolling(250, min_periods=120).rank(pct=True).shift(1)          # known at the day start
    gvr, trr = rank(gv), rank(tr)
    e = pd.read_parquet("data/si_ledgers/BRK_EXITS.parquet")
    e = e[e.kind == "BRK"].copy()
    e["sday"] = e.t_entry // 86400
    e["gvr"], e["trr"] = e.sday.map(gvr), e.sday.map(trr)
    def st(g, a, b):
        s = g[(g.day >= a) & (g.day <= b)]
        return len(s), s.X4_noTP.mean(), nw_t(s.groupby("day").X4_noTP.mean().to_numpy())
    base = {k: st(e, *v) for k, v in P.items()}
    print("base:", {k: f"{v[1]:+.3f}" for k, v in base.items()}, "| rank coverage", round(e.gvr.notna().mean(), 3))
    for name, sel in (("G1 high global vol", e.gvr >= 0.67), ("G2 high trendiness", e.trr >= 0.67)):
        r_ = {k: st(e[sel], *v) for k, v in P.items()}
        g = [r_["DEV"][1] >= 0.05 and r_["DEV"][2] >= 2.24, r_["VAL"][1] > 0 and r_["VAL"][2] >= 1.65, r_["DEV"][1] - base["DEV"][1] >= 0.05 and r_["VAL"][1] - base["VAL"][1] >= 0.05]
        print(f"{name}: " + " | ".join(f"{k} n{v[0]} {v[1]:+.3f} (t {v[2]:+.2f})" for k, v in r_.items()) + f" | gates {''.join('Y' if z else 'n' for z in g)} PASS {all(g)}")
    m = e.groupby(e.day.dt.to_period("M")).agg(R=("X4_noTP", "mean"), gv=("gvr", "mean"), tr=("trr", "mean"))
    print("monthly correlation of the breakout result with: global-vol rank", round(m.R.corr(m.gv), 3), "| trendiness rank", round(m.R.corr(m.tr), 3), f"({len(m)} months)")
    print("by global-vol tercile (all periods):", e.groupby(pd.cut(e.gvr, [0, 0.33, 0.67, 1.0]), observed=True).X4_noTP.mean().round(3).to_dict())
    print("by trendiness tercile (all periods):", e.groupby(pd.cut(e.trr, [0, 0.33, 0.67, 1.0]), observed=True).X4_noTP.mean().round(3).to_dict())
    print("share of high-vol days by year:", e.assign(h=e.gvr >= 0.67).groupby(e.day.dt.year).h.mean().round(2).to_dict())
    print("share of high-trendiness days by year:", e.assign(h=e.trr >= 0.67).groupby(e.day.dt.year).h.mean().round(2).to_dict())


if __name__ == "__main__":
    main()
