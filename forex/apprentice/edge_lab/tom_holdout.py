"""PREREG_TOM_HOLDOUT.md: turn-of-the-month open-to-close on SPY / QQQ, 1993 - May 2019 (before the futures sample).
Usage (from edge_lab): python tom_holdout.py"""
import numpy as np, pandas as pd

DLY = "D:/finance/beginner-quant-research/futures/data/daily/%s_yahoo_daily.csv"
COST = 0.02


def load(sym):
    d = pd.read_csv(DLY % sym); d["date"] = pd.to_datetime(d.date); d = d.sort_values("date").drop_duplicates("date")
    d = d[d.date <= "2019-05-31"].reset_index(drop=True)
    ym = d.date.dt.to_period("M"); d["mon"] = ym.astype(str)
    d["tom"] = False
    for per, idx in d.groupby(ym).groups.items():
        idx = sorted(idx); d.loc[idx[:3], "tom"] = True; d.loc[idx[-1], "tom"] = True
    d = d[(ym != ym.min()) & (ym != ym.max())]
    stale = (d.open == d.close.shift(1))
    d = d[~stale & (d.open > 0)].copy()
    d["net"] = 100 * (d.close / d.open - 1) - COST; d["sym"] = sym; d["yr"] = d.date.dt.year
    return d, int(stale.sum())


if __name__ == "__main__":
    parts = []
    for s in ("SPY", "QQQ"):
        d, st = load(s); parts.append(d)
        print("%s %s..%s  days %d  stale opens dropped %d  TOM n %d net %+.4f%%  other net %+.4f%%  TOM win %.0f%%" % (
            s, d.date.min().date(), d.date.max().date(), len(d), st, d.tom.sum(), d[d.tom].net.mean(), d[~d.tom].net.mean(), 100 * (d[d.tom].net > 0).mean()))
    T = pd.concat(parts, ignore_index=True)
    tm, ot = T[T.tom].net.mean(), T[~T.tom].net.mean(); diff = tm - ot
    rng = np.random.default_rng(20261026)
    groups = [g.to_numpy() for _, g in T.groupby(["mon", "sym"]).groups.items()]
    groups = [g for g in groups if len(g) >= 5]
    tom = T.tom.to_numpy(); net = T.net.to_numpy(); cnt = [int(tom[g].sum()) for g in groups]
    perm = np.empty(20000)
    for r in range(20000):
        msk = np.zeros(len(T), bool)
        for g, c in zip(groups, cnt): msk[rng.choice(g, c, replace=False)] = True
        perm[r] = net[msk].mean() - net[~msk].mean()
    p = float((perm >= diff).mean())
    ys = T[T.tom].groupby("yr").net.mean(); frac = (ys > 0).mean()
    ok = tm > 0 and p <= 0.01 and frac >= 0.6
    print("\nPOOLED SPY+QQQ TOM  n %d  win %.0f%%  net %+.4f%% vs other days %+.4f%%  diff %+.4f%%  permutation P %.4f  TOM years>0 %d/%d (%.0f%%)  %s" % (
        T.tom.sum(), 100 * (T[T.tom].net > 0).mean(), tm, ot, diff, p, (ys > 0).sum(), len(ys), 100 * frac, "-> PASS" if ok else "-> NOT SHOWN"))
    for lo, hi in ((1993, 1999), (2000, 2009), (2010, 2019)):
        s = T[(T.yr >= lo) & (T.yr <= hi)]
        print("  %d-%d  TOM n %4d net %+.4f%%  other %+.4f%%  diff %+.4f%%" % (lo, hi, s.tom.sum(), s[s.tom].net.mean(), s[~s.tom].net.mean(), s[s.tom].net.mean() - s[~s.tom].net.mean()))
    print("  TOM by year: " + " ".join("%d %+.3f" % (k, v) for k, v in ys.items()))
