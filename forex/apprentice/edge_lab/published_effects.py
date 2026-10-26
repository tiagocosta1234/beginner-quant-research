"""PREREG_PUBLISHED_EFFECTS.md: overnight drift at the European open (H1) and US last-30-minute intraday momentum (H2).
Usage (from edge_lab): python published_effects.py"""
import numpy as np, pandas as pd

DB = "D:/finance/beginner-quant-research/futures/data/databento/futures_%s.F_1m.parquet"
COST = {"ES": 0.74, "NQ": 1.1, "GC": 0.32, "SI": 0.0112}
USD = {"ES": 5, "NQ": 2, "GC": 10, "SI": 1000}
TOL = np.timedelta64(5, "m")


def load_ny(src):
    d = pd.read_parquet(DB % src).sort_values("ts")
    d = d[["ts", "open", "high", "low", "close"]].drop_duplicates("ts").set_index("ts")
    d.index = pd.DatetimeIndex(d.index).tz_convert("America/New_York").tz_localize(None)
    return d[~d.index.duplicated()].sort_index()


def build(src):
    d = load_ny(src)
    T, O = d.index.to_numpy(), d.open.to_numpy()

    def px(t):
        t = np.datetime64(t); i = np.searchsorted(T, t)
        return O[i] if i < len(T) and T[i] - t <= TOL else np.nan

    day = d.groupby(d.index.normalize()).agg(h=("high", "max"), l=("low", "min"), c=("close", "last"))
    pc = day.c.shift(1)
    atr = pd.concat([day.h - day.l, (day.h - pc).abs(), (day.l - pc).abs()], axis=1).max(axis=1).ewm(alpha=1 / 14, adjust=False).mean().shift(1)
    days = [x for x in day.index if x.weekday() < 5]
    H = pd.Timedelta(hours=1)
    close16 = {x: px(x + 16 * H) for x in days}
    rows = []
    for k in range(2, len(days)):
        dt, p1, p2 = days[k], days[k - 1], days[k - 2]
        A = atr.get(dt, np.nan)
        if not (A > 0): continue
        r = dict(date=dt, yr=dt.year, mkt=src, atr=A)
        prev_ret = close16[p1] / close16[p2] - 1
        r["prev_neg"] = bool(prev_ret < 0) if np.isfinite(prev_ret) else np.nan
        # H1: 02:00 -> 03:00 ET, and every overnight hour 18:00 (prior evening) .. 09:00 for the descriptive table
        r["h1"] = px(dt + 3 * H) - px(dt + 2 * H)
        for hh in list(range(-6, 9)):
            r["hr%+d" % hh] = px(dt + (hh + 1) * H) - px(dt + hh * H)
        # H2: sign of prior 16:00 -> 10:00, traded 15:30 -> 16:00
        s10, s1530, e16 = px(dt + 10 * H), px(dt + 15.5 * H), px(dt + 16 * H)
        r["sig_gao"] = np.sign(s10 - close16[p1]); r["sig_rest"] = np.sign(s1530 - close16[p1])
        r["last30"] = e16 - s1530
        rows.append(r)
    return pd.DataFrame(rows)


def stat(label, gross, cost, atr, yr, usd, primary=False):
    ok = np.isfinite(gross)
    g, c, a, y = gross[ok], cost[ok], atr[ok], yr[ok]
    net = (g - c) / a; mir = (-g - c) / a
    rng = np.random.default_rng(20261026)
    p = float((np.where(rng.random((20000, len(net))) < 0.5, net, mir).mean(axis=1) >= net.mean()).mean())
    ys = pd.Series(net, index=y).groupby(level=0).mean(); pos = int((ys.loc[[v for v in ys.index if 2020 <= v <= 2026]] > 0).sum())
    pas = primary and net.mean() > 0 and p <= 0.01 and pos >= 5
    span = max((pd.Series(y).max() - pd.Series(y).min() + 1), 1)
    print("  %-34s n %5d (%3.0f/yr)  win %3.0f%%  net %+.4f ATR  $/micro %+7.2f  P %.4f  years>0 %d/7  %s" % (
        label, len(net), len(net) / span, 100 * (g - c > 0).mean(), net.mean(), np.mean((g - c) * usd[ok]), p, pos,
        ("-> PASS" if pas else "-> NOT SHOWN") if primary else ""))
    if primary: print("      by year: " + " ".join("%d %+.4f (%d)" % (k, v, (y == k).sum()) for k, v in ys.items()))


if __name__ == "__main__":
    D = pd.concat([build(m) for m in COST], ignore_index=True)
    D["cost"] = D.mkt.map(COST); D["usd"] = D.mkt.map(USD).astype(float)
    eq = D[D.mkt.isin(["ES", "NQ"])]
    print("H1  OVERNIGHT DRIFT, long 02:00 -> 03:00 ET")
    for m in ("ES", "NQ"):
        s = eq[eq.mkt == m]; stat("H1a %s" % m, s.h1.to_numpy(), s.cost.to_numpy(), s.atr.to_numpy(), s.yr.to_numpy(), s.usd.to_numpy())
    stat("H1a ES+NQ every day (PRIMARY)", eq.h1.to_numpy(), eq.cost.to_numpy(), eq.atr.to_numpy(), eq.yr.to_numpy(), eq.usd.to_numpy(), True)
    s = eq[eq.prev_neg == True]
    stat("H1b ES+NQ after a down day (PRIMARY)", s.h1.to_numpy(), s.cost.to_numpy(), s.atr.to_numpy(), s.yr.to_numpy(), s.usd.to_numpy(), True)
    for lab, msk in (("2019-2020", eq.yr <= 2020), ("2021-2026", eq.yr >= 2021)):
        s = eq[msk]; stat("H1a ES+NQ %s" % lab, s.h1.to_numpy(), s.cost.to_numpy(), s.atr.to_numpy(), s.yr.to_numpy(), s.usd.to_numpy())
    print("  every overnight hour, ES+NQ, mean GROSS in ATR units (long), 2019-2026 / 2021-2026:")
    for hh in range(-6, 9):
        c = "hr%+d" % hh; g = eq[c] / eq.atr; g2 = eq.loc[eq.yr >= 2021, c] / eq.loc[eq.yr >= 2021, "atr"]
        print("    %02d:00-%02d:00 ET  %+.4f / %+.4f   (n %d)" % (hh % 24, (hh + 1) % 24, g.mean(), g2.mean(), g.notna().sum()))
    print("\nH2  INTRADAY MOMENTUM, 15:30 -> 16:00 ET on the side of prior close -> 10:00")
    D2 = D[(D.sig_gao != 0) & D.sig_gao.notna()]
    for m in COST:
        s = D2[D2.mkt == m]; stat("H2 %s" % m, (s.sig_gao * s.last30).to_numpy(), s.cost.to_numpy(), s.atr.to_numpy(), s.yr.to_numpy(), s.usd.to_numpy())
    stat("H2 4 markets pooled (PRIMARY)", (D2.sig_gao * D2.last30).to_numpy(), D2.cost.to_numpy(), D2.atr.to_numpy(), D2.yr.to_numpy(), D2.usd.to_numpy(), True)
    D3 = D[(D.sig_rest != 0) & D.sig_rest.notna()]
    stat("H2 secondary: prior close -> 15:30 sign", (D3.sig_rest * D3.last30).to_numpy(), D3.cost.to_numpy(), D3.atr.to_numpy(), D3.yr.to_numpy(), D3.usd.to_numpy())
    for m in COST:
        s = D3[D3.mkt == m]; stat("  rest-of-day %s" % m, (s.sig_rest * s.last30).to_numpy(), s.cost.to_numpy(), s.atr.to_numpy(), s.yr.to_numpy(), s.usd.to_numpy())
