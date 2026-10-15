"""BEST3M_CYCLE (PREREG_BEST3M_CYCLE.md): MT5 Pro cycles trading every symbol's best breakout rule of the last 3 months at once.
   python -m forex.ea_research.best3m_cycle [--dry]"""
import sys

import numpy as np
import pandas as pd

import forex.ea_research.orb11_entry as oe

SIZES = (100, 200, 300)
DATA_END = pd.Timestamp("2026-10-02")


def long_table():
    T = pd.read_parquet("D:/finance/si_ledgers/ORB11_ENTRY.parquet")
    T = T[(T.trig != "CTRL") & (T.trig != "FADE") & (T.day <= DATA_END)].reset_index(drop=True)
    parts = []
    for f in oe.FILTS:
        m = oe.fmask(T, f)
        for x in ("r1", "rh"):
            s = T.loc[m, ["mkt", "day", "sess", "trig", x]].rename(columns={x: "R"})
            s["rule"] = s.sess + " " + s.trig + " " + f + " " + ("1:1" if x == "r1" else "hold")
            parts.append(s[["mkt", "day", "rule", "R"]])
    Z = pd.concat(parts, ignore_index=True); Z["mon"] = Z.day.dt.to_period("M")
    return Z


def choose_monthly(Z):
    """for each month M: per symbol the rule with the highest total R over the 3 previous calendar months (>= 15 trades, total > 0)."""
    agg = Z.groupby(["mkt", "rule", "mon"]).R.agg(["sum", "size"]).reset_index()
    months = pd.period_range("2022-03", "2026-10", freq="M"); out = []
    for M in months:
        w = agg[(agg.mon >= M - 3) & (agg.mon < M)].groupby(["mkt", "rule"])[["sum", "size"]].sum().reset_index()
        w = w[(w["size"] >= 15) & (w["sum"] > 0)]
        if len(w) == 0: continue
        b = w.sort_values("sum", ascending=False).drop_duplicates("mkt")
        out.append(b.assign(mon=M)[["mkt", "rule", "mon"]])
    return pd.concat(out, ignore_index=True)


def daily(Ztr):
    g = Ztr.groupby("day").R
    d = pd.DataFrame({"net": g.sum(), "neg": Ztr.R.clip(upper=0).groupby(Ztr.day).sum(), "n": g.size()})
    return d.sort_index()


def cycle(d, i0, X, pess):
    """returns (status 1 pass / 2 breach / 0 running, calendar days, worst day USD)."""
    bal = 100_000.0; days = d.index; net = d.net.to_numpy() * X; worst = (d.neg.to_numpy() if pess else d.net.to_numpy()) * X; wmin = 0.0
    for i in range(i0, len(d)):
        wmin = min(wmin, worst[i])
        if worst[i] <= -2500 or bal + worst[i] <= 92_000: return 2, (days[i] - days[i0]).days, wmin
        bal += min(net[i], 2000.0)
        if bal >= 108_000: return 1, (days[i] - days[i0]).days, wmin
    return 0, (days[-1] - days[i0]).days, wmin


def main():
    Z = long_table(); Ch = choose_monthly(Z)
    if "--dry" in sys.argv:
        M = pd.Period("2026-07", "M"); c = Ch[Ch.mon == M]
        print(f"{len(Z)} rule-trades; months with picks {Ch.mon.nunique()}; picks for {M}: {len(c)}"); print(c.head(8).to_string(index=False))
        # causality: recompute July picks with all data after 2026-06-30 removed -> identical
        c2 = choose_monthly(Z[Z.day < "2026-07-01"]); c2 = c2[c2.mon == M]
        print("truncation:", "identical" if c.sort_values("mkt").reset_index(drop=True).equals(c2.sort_values("mkt").reset_index(drop=True)) else "DIFFERENT")
        return
    pd.set_option("display.width", 250)
    # B causal
    Zb = Z.merge(Ch, on=["mkt", "rule", "mon"]); db = daily(Zb)
    print(f"B CAUSAL: {len(Zb)} trades on {len(db)} days, {db.n.mean():.1f} trades a day; mean {Zb.R.mean():+.3f} R a trade; by year R a trade: "
          f"{Zb.groupby(Zb.day.dt.year).R.mean().round(3).to_dict()}; daily net R by year: {db.groupby(db.index.year).net.sum().round(1).to_dict()}")
    bdays = pd.bdate_range("2022-03-01", "2026-08-31")[::5]
    starts = np.unique(np.searchsorted(db.index, bdays))
    rows = []
    for X in SIZES:
        for pess in (False, True):
            for i0 in starts:
                s, n, w = cycle(db, i0, X, pess)
                rows.append(dict(X=X, mode="pessimistic" if pess else "optimistic", start=db.index[i0], st=s, days=n, worst=w))
    R = pd.DataFrame(rows); R["yr"] = R.start.dt.year
    print(f"\n{len(starts)} cycle starts 2022-03..2026-08 (every 5th business day). P(pass) / P(breach) within 30 and 60 calendar days and by 2026-10-02:")
    for (X, mode), g in R.groupby(["X", "mode"]):
        p30 = ((g.st == 1) & (g.days <= 30)).mean(); b30 = ((g.st == 2) & (g.days <= 30)).mean()
        p60 = ((g.st == 1) & (g.days <= 60)).mean(); b60 = ((g.st == 2) & (g.days <= 60)).mean()
        md = g[g.st == 1].days.median()
        print(f"  ${X} a trade, {mode:11s}: 30d pass {p30:5.1%} breach {b30:5.1%} | 60d pass {p60:5.1%} breach {b60:5.1%} | ever pass {(g.st == 1).mean():5.1%} breach {(g.st == 2).mean():5.1%} running {(g.st == 0).mean():5.1%} | median days to pass {md}")
    print("\n  by start year, $200 a trade (pass / breach, ever; optimistic | pessimistic):")
    for y, g in R[R.X == 200].groupby("yr"):
        o, p = g[g["mode"] == "optimistic"], g[g["mode"] == "pessimistic"]
        print(f"   {y}: {(o.st == 1).mean():.0%} / {(o.st == 2).mean():.0%} | {(p.st == 1).mean():.0%} / {(p.st == 2).mean():.0%}  ({len(o)} starts)")
    R.to_csv("D:/finance/si_ledgers/BEST3M_CYCLE_B.csv", index=False)
    # A in-sample: the table's rules, traded over the same 3 months
    A0 = pd.Timestamp("2026-07-03"); w = Z[(Z.day >= A0)]
    agg = w.groupby(["mkt", "rule"]).R.agg(["sum", "size"]).reset_index(); agg = agg[agg["size"] >= 15]
    pick = agg.sort_values("sum", ascending=False).drop_duplicates("mkt")[["mkt", "rule"]]
    Za = w.merge(pick, on=["mkt", "rule"]); da = daily(Za)
    print(f"\nA IN-SAMPLE (the table's {len(pick)} rules, 2026-07-03..10-02): {len(Za)} trades, {Za.R.sum():+.1f} R in total, {da.n.mean():.1f} trades a day, worst day {da.net.min():+.1f} R (losers only {da.neg.min():+.1f} R)")
    for X in SIZES:
        for pess in (False, True):
            s, n, wm = cycle(da, 0, X, pess)
            print(f"  ${X} a trade, {'pessimistic' if pess else 'optimistic':11s}: {['still running', 'PASS', 'BREACH'][s]} after {n} days (worst day ${wm:,.0f})")
    # B restricted to the same 3 months
    for X in SIZES:
        i0 = int(np.searchsorted(db.index, A0)); s, n, wm = cycle(db, i0, X, False)
        print(f"  causal version over the same months, ${X}, optimistic: {['still running', 'PASS', 'BREACH'][s]} after {n} days; net {db.net.iloc[i0:].sum():+.1f} R")


if __name__ == "__main__":
    main()
