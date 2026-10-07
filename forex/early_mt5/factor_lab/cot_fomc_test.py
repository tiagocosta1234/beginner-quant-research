"""S2 (COT positioning) and S3 (FOMC pre-announcement drift), pre-registered in forex/early_mt5/factor_lab/PREREG_COT_FOMC.md.
   python -m mt5broker.factor_lab.cot_fomc_test --dry-run     coverage and counts only
   python -m mt5broker.factor_lab.cot_fomc_test               the pre-registered run (HOLD printed only for a hypothesis that passes DEV+VAL)"""
from __future__ import annotations

import glob
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.factor_lab import factor_test as ft

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[1] / "futures" / "data"
COT_NAMES = {"EUR": "EURO FX - CHICAGO", "GBP": "BRITISH POUND STERLING - CHICAGO", "JPY": "JAPANESE YEN - CHICAGO", "CHF": "SWISS FRANC - CHICAGO", "CAD": "CANADIAN DOLLAR - CHICAGO",
             "AUD": "AUSTRALIAN DOLLAR - CHICAGO", "NZD": "NEW ZEALAND DOLLAR - CHICAGO", "XAU": "GOLD - COMMODITY EXCHANGE"}
MK = list(COT_NAMES)
TCB = {**ft.TC.to_dict(), "XAU": 1.5}
MARKUP = 0.015
PH_W = {"DEV": ("2000-01-01", "2012-12-31"), "VAL": ("2013-01-01", "2020-12-31"), "HOLD": ("2021-01-01", "2025-12-31")}
PH_E = {"DEV": (2000, 2011), "VAL": (2012, 2020), "HOLD": (2021, 2026)}


def load_cot() -> pd.DataFrame:
    fr = []
    for f in sorted(glob.glob(str(HERE / "data" / "cot" / "*.zip"))):
        z = zipfile.ZipFile(f); df = pd.read_csv(z.open(z.namelist()[0]), low_memory=False)
        fr.append(df[["Market and Exchange Names", "As of Date in Form YYYY-MM-DD", "Open Interest (All)", "Noncommercial Positions-Long (All)", "Noncommercial Positions-Short (All)"]])
    d = pd.concat(fr); d.columns = ["name", "date", "oi", "long", "short"]; d["date"] = pd.to_datetime(d.date)
    out = {}
    for k, pre in COT_NAMES.items():
        x = d[d.name.str.startswith(pre)].drop_duplicates("date").set_index("date").sort_index()
        out[k] = (x.long - x.short) / x.oi
    return pd.DataFrame(out)


def prices():
    P, R = ft.load()
    g = pd.read_csv(DATA / "daily_ohlc" / "GC=F_yahoo_ohlc.csv", parse_dates=["date"]).set_index("date").close
    px = P.copy(); px["XAU"] = g.reindex(px.index, method="ffill")
    full = pd.concat([P, g.rename("XAU")], axis=1).ffill()
    return full, R


def wstats(s: pd.Series, per_year=52) -> dict:
    s = s.dropna(); n = len(s)
    if n < 20:
        return dict(n=n, ann=np.nan, vol=np.nan, sharpe=np.nan, t=np.nan, dd=np.nan)
    m, sd = s.mean(), s.std(ddof=1); eq = s.cumsum()
    return dict(n=n, ann=m * per_year, vol=sd * np.sqrt(per_year), sharpe=m / sd * np.sqrt(per_year), t=m / (sd / np.sqrt(n)), dd=float((eq.cummax() - eq).max()))


def fmtw(st):
    return f"n {st['n']:4d} ann {st['ann'] * 100:+5.1f}% vol {st['vol'] * 100:4.1f}% Sharpe {st['sharpe']:+.2f} t {st['t']:+.2f} maxDD {st['dd'] * 100:4.1f}%"


def weekly(NP, full, R, kind, drop=None):
    mk = [m for m in MK if m != drop]
    rep = NP.index[NP.index >= "1999-06-01"]
    entry = pd.DatetimeIndex(rep) + pd.Timedelta(days=6); exit_ = entry + pd.Timedelta(days=7)
    pe = full[mk].reindex(entry, method="ffill").values; px = full[mk].reindex(exit_, method="ffill").values
    ret = pd.DataFrame(px / pe - 1, index=rep, columns=mk)
    car = pd.DataFrame(0.0, index=rep, columns=mk)
    for m in mk:
        if m != "XAU":
            per = pd.PeriodIndex(entry, freq="M"); car[m] = ((R[m] - R["USD"]).reindex(per).values) / 100 / 52
    npm = NP[mk].reindex(rep)
    if kind == "C":
        pct = npm.rolling(156).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True)
        pos = pd.DataFrame(0.0, index=rep, columns=mk); pos[pct >= 0.90] = -1.0; pos[pct <= 0.10] = 1.0; pos = pos.where(pct.notna())
    else:
        pos = np.sign(npm - npm.shift(13))
    vol = ret.rolling(26).std() * np.sqrt(52); lev = (0.10 / vol).clip(upper=3.0)
    W = (pos * lev) / 8.0
    ok = W.notna() & ret.notna(); W = W.where(ok)
    gross = (W * (ret + car)).sum(axis=1, min_count=1)
    turn = W.fillna(0).diff().abs(); tc = (turn * pd.Series(TCB)[mk] / 1e4).sum(axis=1); fin = W.abs().sum(axis=1) * MARKUP / 52
    net = (gross - tc - fin); net.index = pd.DatetimeIndex(net.index) + pd.Timedelta(days=6)
    return net.loc["2000-01-01":"2025-12-31"].dropna()


def pw(s, name):
    a, b = PH_W[name]; return s.loc[a:b]


def event_stats(r_event: pd.Series, mean_non: float, cost_bp: float, direction=1):
    x = direction * (r_event - mean_non) - cost_bp / 1e4
    return x


def fe(x: pd.Series):
    n = len(x)
    if n < 8:
        return f"n {n}"
    return f"n {n:3d} mean {x.mean() * 1e4:+6.1f} bp (t {x.mean() / (x.std(ddof=1) / np.sqrt(n)):+.2f}) hit {np.mean(x > 0) * 100:3.0f}% Sharpe@8/yr {x.mean() / x.std(ddof=1) * np.sqrt(8):+.2f} | 5x leverage {x.mean() * 8 * 5 * 100:+.1f}%/yr"


def main():
    NP = load_cot(); full, R = prices(); dry = "--dry-run" in sys.argv
    ev = pd.read_csv(DATA / "events" / "fomc_statement_dates.csv", parse_dates=["date"]).date
    print(f"COT markets {list(NP.columns)} weeks {NP.dropna().shape[0]} from {NP.dropna().index[0].date()} to {NP.index[-1].date()} | FOMC dates {len(ev)} ({ev.iloc[0].date()}..{ev.iloc[-1].date()})")
    if dry:
        for ph, (a, b) in PH_E.items():
            print(f"FOMC events {ph}: {int(((ev.dt.year >= a) & (ev.dt.year <= b)).sum())}")
        return
    hits = []
    res = {}
    print("\n== S2 positioning (weekly, MT5-like costs)")
    for name, kind in (("S2-C CONTRARIAN EXTREME", "C"), ("S2-T POSITIONING TREND", "T")):
        s = weekly(NP, full, R, kind); res[name] = s
        dv = pd.concat([pw(s, "DEV"), pw(s, "VAL")]); sa = wstats(dv); sd, sv = wstats(pw(s, "DEV")), wstats(pw(s, "VAL"))
        print(f"{name}\n  DEV {fmtw(sd)}\n  VAL {fmtw(sv)}\n  DEV+VAL {fmtw(sa)}")
        sh = {}; ok = 0
        for m in MK:
            x = weekly(NP, full, R, kind, drop=m); x = pd.concat([pw(x, "DEV"), pw(x, "VAL")]); sh[m] = round(wstats(x)["sharpe"], 2); ok += wstats(x)["sharpe"] >= 0.25
        c1 = sa["sharpe"] >= 0.4 and sa["t"] >= 2.6; c2 = sd["ann"] > 0 and sv["ann"] > 0; c3 = ok >= 6
        print(f"  drop-one-market Sharpe {sh} -> {ok} of 8 >= 0.25 | conditions: Sharpe>=0.4 & t>=2.6 {c1} | DEV and VAL positive {c2} | not one market {c3}")
        if c1 and c2 and c3:
            hits.append(name)
    print("\n== S3 FOMC pre-announcement drift (event return = close(D-1)->close(D) minus the mean of non-event days, net of 3 bp)")
    series = {"S3-A SPX (long)": (pd.read_csv(DATA / "external_index_daily" / "spx.csv", parse_dates=["date"]).set_index("date").close, 1.0),
              "S3-B DAX (long)": (pd.read_csv(DATA / "external_index_daily" / "dax.csv", parse_dates=["date"]).set_index("date").close, 1.0)}
    usd = -full[ft.CCY].pct_change().mean(axis=1)
    series["S3-C USD basket noon(D-1)->noon(D) (two-sided)"] = (None, 0.0)
    for name, (cl, direction) in series.items():
        r = usd.dropna() if cl is None else cl.pct_change().dropna()
        idx = r.index.intersection(pd.DatetimeIndex(ev)); rev = r.loc[idx]; non = r.drop(idx); mean_non = non.mean()
        if direction == 0.0:
            ph_dv = rev[(rev.index.year >= 2000) & (rev.index.year <= 2020)]; direction = 1.0 if (ph_dv.mean() - mean_non) >= 0 else -1.0
        x = event_stats(rev, mean_non, 3.0, direction); print(f"{name} (direction {int(direction):+d}, mean of non-event days {mean_non * 1e4:+.1f} bp)")
        sub = {ph: x[(x.index.year >= a) & (x.index.year <= b)] for ph, (a, b) in PH_E.items()}
        dv = pd.concat([sub["DEV"], sub["VAL"]]); tt = dv.mean() / (dv.std(ddof=1) / np.sqrt(len(dv)))
        for ph in ("DEV", "VAL"):
            print(f"  {ph:4} {fe(sub[ph])}")
        print(f"  DEV+VAL {fe(dv)}")
        c1 = tt >= 2.6; c2 = sub["DEV"].mean() > 0 and sub["VAL"].mean() > 0
        print(f"  conditions: t>=2.6 {c1} | DEV and VAL same sign {c2}")
        if c1 and c2:
            hits.append(name); print(f"  HOLD (printed because DEV+VAL passed): {fe(sub['HOLD'])}")
    print(f"\nPASSED DEV+VAL (k = 5): {hits}")
    for name in hits:
        if name.startswith("S2"):
            h = pw(res[name], "HOLD"); print(f"HOLD {name}: {fmtw(wstats(h))} | halves Sharpe {wstats(h.loc[:'2023-12-31'])['sharpe']:+.2f} / {wstats(h.loc['2024-01-01':])['sharpe']:+.2f}")
    print("\nDESCRIPTIVE ONLY: S2 by-year net Sharpe")
    for name, s in res.items():
        print(f"  {name}: {({int(y): round(wstats(g)['sharpe'], 1) for y, g in s.groupby(s.index.year) if len(g) >= 20})}")


if __name__ == "__main__":
    main()
