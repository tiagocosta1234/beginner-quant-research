"""PREREG_SETTLE_TOM.md: gold / silver settlement-window momentum and the equity turn-of-the-month.
Usage (from edge_lab): python settle_tom.py"""
import numpy as np, pandas as pd
from published_effects import load_ny, TOL

M = pd.Timedelta(minutes=1)


def pricer(d):
    T, O = d.index.to_numpy(), d.open.to_numpy()

    def px(t):
        t = np.datetime64(t); i = np.searchsorted(T, t)
        return O[i] if i < len(T) and T[i] - t <= TOL else np.nan
    return px


def atr_of(d):
    day = d.groupby(d.index.normalize()).agg(h=("high", "max"), l=("low", "min"), c=("close", "last"))
    pc = day.c.shift(1)
    return pd.concat([day.h - day.l, (day.h - pc).abs(), (day.l - pc).abs()], axis=1).max(axis=1).ewm(alpha=1 / 14, adjust=False).mean().shift(1)


def settle_mom(src, sig_t, settle_t, cost, usd):
    d = load_ny(src); px = pricer(d); atr = atr_of(d)
    days = [x for x in atr.index if x.weekday() < 5]
    rows = []
    for k in range(1, len(days)):
        dt, p1 = days[k], days[k - 1]
        A = atr.get(dt, np.nan)
        e, x, prev = px(dt + sig_t), px(dt + settle_t), px(p1 + settle_t)
        if not (A > 0) or not np.isfinite(e + x + prev) or e == prev: continue
        side = np.sign(e - prev)
        rows.append(dict(yr=dt.year, g=side * (x - e), atr=A))
    R = pd.DataFrame(rows); R["cost"] = cost; R["usd"] = usd
    return R


def report(label, R, primary=False):
    rng = np.random.default_rng(20261026)
    net = ((R.g - R.cost) / R.atr).to_numpy(); mir = ((-R.g - R.cost) / R.atr).to_numpy()
    p = float((np.where(rng.random((20000, len(net))) < 0.5, net, mir).mean(axis=1) >= net.mean()).mean())
    ys = pd.Series(net, index=R.yr.to_numpy()).groupby(level=0).mean(); pos = int((ys.loc[[v for v in ys.index if 2020 <= v <= 2026]] > 0).sum())
    ok = primary and net.mean() > 0 and p <= 0.01 and pos >= 5
    print("  %-30s n %5d  win %3.0f%%  gross $/micro %+6.2f  net $/micro %+6.2f  net %+.4f ATR  P %.4f  years>0 %d/7  %s" % (
        label, len(R), 100 * (R.g > R.cost).mean(), (R.g * R.usd).mean(), ((R.g - R.cost) * R.usd).mean(), net.mean(), p, pos,
        ("-> PASS" if ok else "-> NOT SHOWN") if primary else ""))
    print("      by year: " + " ".join("%d %+.4f" % (k, v) for k, v in ys.items()))


def tom(src, cost, usd):
    d = load_ny(src); px = pricer(d); atr = atr_of(d)
    days = pd.DatetimeIndex([x for x in atr.index if x.weekday() < 5 and np.isfinite(px(x + pd.Timedelta(hours=9.5)))])
    ym = days.to_period("M")
    is_tom = np.zeros(len(days), bool)
    for per in ym.unique():
        idx = np.flatnonzero(ym == per)
        is_tom[idx[:3]] = True; is_tom[idx[-1]] = True
    first_m, last_m = ym.min(), ym.max()
    rows = []
    for i, dt in enumerate(days):
        if ym[i] in (first_m, last_m): continue
        A = atr.get(dt, np.nan); a, b = px(dt + pd.Timedelta(hours=9.5)), px(dt + pd.Timedelta(hours=15, minutes=55))
        if not (A > 0) or not np.isfinite(a + b): continue
        rows.append(dict(date=dt, yr=dt.year, mon=str(ym[i]), tom=is_tom[i], g=b - a, atr=A))
    R = pd.DataFrame(rows); R["cost"] = cost; R["usd"] = usd
    return R


if __name__ == "__main__":
    print("P1 GOLD settlement momentum: side = sign(13:00 today - 13:30 prior day), trade 13:00 -> 13:30 ET")
    G = settle_mom("GC", pd.Timedelta(hours=13), pd.Timedelta(hours=13, minutes=30), 0.32, 10.0); report("GC (PRIMARY)", G, True)
    print("\nP2 SILVER settlement momentum: side = sign(12:55 today - 13:25 prior day), trade 12:55 -> 13:25 ET")
    S = settle_mom("SI", pd.Timedelta(hours=12, minutes=55), pd.Timedelta(hours=13, minutes=25), 0.0112, 1000.0); report("SI (secondary)", S)
    print("\nP3 TURN OF THE MONTH: long 09:30 -> 15:55 ET on the last + first 3 trading days")
    T = pd.concat([tom("ES", 0.74, 5.0).assign(mkt="ES"), tom("NQ", 1.1, 2.0).assign(mkt="NQ")], ignore_index=True)
    T["net"] = (T.g - T.cost) / T.atr
    for m in ("ES", "NQ"):
        s = T[T.mkt == m]
        print("  %s  TOM n %d net %+.4f ATR ($%+.2f/micro)  other n %d net %+.4f ATR ($%+.2f/micro)" % (m, s.tom.sum(), s[s.tom].net.mean(), ((s[s.tom].g - s.cost[s.tom]) * s.usd[s.tom]).mean(),
              (~s.tom).sum(), s[~s.tom].net.mean(), ((s[~s.tom].g - s.cost[~s.tom]) * s.usd[~s.tom]).mean()))
    tomm, oth = T[T.tom].net.mean(), T[~T.tom].net.mean(); diff = tomm - oth
    rng = np.random.default_rng(20261026)
    # month-block permutation: in each month, re-draw which 4 of that month's days count as TOM
    groups = [np.flatnonzero((T.mon == mo).to_numpy() & (T.mkt == mk).to_numpy()) for mo in T.mon.unique() for mk in ("ES", "NQ")]
    groups = [g for g in groups if len(g) >= 5]
    net = T.net.to_numpy(); cnt = [int(T.tom.to_numpy()[g].sum()) for g in groups]
    perm = np.empty(20000)
    for r in range(20000):
        msk = np.zeros(len(T), bool)
        for g, c in zip(groups, cnt): msk[rng.choice(g, c, replace=False)] = True
        perm[r] = net[msk].mean() - net[~msk].mean()
    p = float((perm >= diff).mean())
    ys = T[T.tom].groupby("yr").net.mean(); pos = int((ys.loc[[v for v in ys.index if 2020 <= v <= 2026]] > 0).sum())
    ok = tomm > 0 and p <= 0.01 and pos >= 5
    print("  ES+NQ TOM (PRIMARY)  n %d  win %.0f%%  net %+.4f ATR vs other days %+.4f  diff %+.4f  permutation P %.4f  TOM years>0 %d/7  %s" % (
        T.tom.sum(), 100 * (T[T.tom].g > T[T.tom].cost).mean(), tomm, oth, diff, p, pos, "-> PASS" if ok else "-> NOT SHOWN"))
    print("      TOM by year: " + " ".join("%d %+.4f" % (k, v) for k, v in ys.items()))
