"""Track A (pre-registered in forex/factor_lab/PREREG_FACTORS.md): carry, momentum, combo and turn-of-month USD on 9 currencies vs USD, FRED data 1999-2026.
   python -m forex.factor_lab.factor_test --dry-run     coverage and observation counts only
   python -m forex.factor_lab.factor_test               the pre-registered run (HOLD printed only for a hypothesis that passes DEV+VAL)"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

D = Path(__file__).resolve().parent / "data" / "fred"
FX = {"EUR": ("DEXUSEU", False), "GBP": ("DEXUSUK", False), "AUD": ("DEXUSAL", False), "NZD": ("DEXUSNZ", False), "JPY": ("DEXJPUS", True),
      "CAD": ("DEXCAUS", True), "CHF": ("DEXSZUS", True), "NOK": ("DEXNOUS", True), "SEK": ("DEXSDUS", True)}
RT = {"USD": "US", "EUR": "EZ", "GBP": "GB", "AUD": "AU", "NZD": "NZ", "JPY": "JP", "CAD": "CA", "CHF": "CH", "NOK": "NO", "SEK": "SE"}
TC = pd.Series({"EUR": 1.2, "GBP": 1.2, "JPY": 1.2, "AUD": 1.5, "NZD": 1.5, "CAD": 1.5, "CHF": 1.5, "NOK": 4.0, "SEK": 4.0})   # bp per unit of notional traded
MARKUP = 0.015                                                                                              # financing markup a year on gross notional (MT5-like)
CCY = list(FX)
PH = {"DEV": ("2002-06", "2014-12"), "VAL": ("2015-01", "2020-12"), "HOLD": ("2021-01", "2025-12")}          # by holding month


def read(sid: str) -> pd.Series:
    df = pd.read_csv(D / f"{sid}.csv"); df.columns = ["date", "v"]; df["date"] = pd.to_datetime(df.date); df["v"] = pd.to_numeric(df.v, errors="coerce")
    return df.set_index("date").v


def load():
    px = {}
    for c, (sid, inv) in FX.items():
        s = read(sid).dropna(); px[c] = 1.0 / s if inv else s
    P = pd.DataFrame(px).sort_index(); P = P[P.index >= "1999-01-04"].ffill(); P = P[P.index.dayofweek < 5]
    R = pd.DataFrame({c: read(f"IR3TIB01{RT[c]}M156N").dropna() for c in RT}); R.index = R.index.to_period("M"); R = R.reindex(pd.period_range(R.index.min(), R.index.max(), freq="M"))
    return P, R


def weights(sig: pd.DataFrame) -> pd.DataFrame:
    ok = sig.notna().all(axis=1)
    rk = sig.rank(axis=1, method="first").values; n = sig.notna().sum(axis=1).values[:, None]
    w = np.zeros(rk.shape); w[rk >= n - 2] = 1 / 3; w[rk <= 3] = -1 / 3
    W = pd.DataFrame(w, index=sig.index, columns=sig.columns); W.loc[~ok] = np.nan
    return W


def signals(ME, R, kind, ccys):
    carry = R[ccys].shift(1)                                                  # 3-month rate of the previous month (known at the month end)
    mom = (ME.shift(1) / ME.shift(12) - 1)[ccys]                              # 12-1 month spot return
    if kind == "carry":
        return carry
    if kind == "mom":
        return mom
    return (carry.rank(axis=1) + mom.rank(axis=1)) / 2


def backtest(ME, R, kind, markup, drop=None):
    ccys = [c for c in CCY if c != drop]
    sig = signals(ME, R, kind, ccys); sig = sig.loc["2002-05":"2025-11"]
    W = weights(sig)
    spot = (ME.shift(-1) / ME - 1)[ccys]
    car = ((R[ccys].sub(R["USD"], axis=0)).shift(-1) / 100 / 12)
    gross = (W * (spot + car)).sum(axis=1)
    turn = W.diff().abs(); turn.iloc[0] = W.iloc[0].abs()
    tcost = (turn * TC[ccys] / 1e4).sum(axis=1); fin = W.abs().sum(axis=1) * markup / 12
    net = (gross - tcost - fin).dropna(); net.index = net.index + 1         # holding month
    return net


def tom(P, cost_bp=3.0):
    daily = P.pct_change()
    per = P.index.to_period("M"); bd = pd.Series(1, index=P.index).groupby(per).cumsum()
    win = (bd <= 3).values
    basket = -daily[CCY].mean(axis=1)
    r = basket[win].groupby(per[win]).sum() - cost_bp / 1e4
    r = r.loc["2002-06":"2025-12"]
    per_ccy = (-daily[CCY][win]).groupby(per[win]).sum().loc["2002-06":"2025-12"].mean()
    return r, per_ccy


def stats(s: pd.Series) -> dict:
    s = s.dropna(); n = len(s)
    if n < 6:
        return dict(n=n, ann=np.nan, vol=np.nan, sharpe=np.nan, t=np.nan, dd=np.nan, worst=np.nan)
    m, sd = s.mean(), s.std(ddof=1); eq = s.cumsum()
    return dict(n=n, ann=m * 12, vol=sd * np.sqrt(12), sharpe=m / sd * np.sqrt(12), t=m / (sd / np.sqrt(n)), dd=float((eq.cummax() - eq).max()), worst=float(s.min()))


def phase(s: pd.Series, name: str) -> pd.Series:
    a, b = PH[name]; return s.loc[a:b]


def fmt(st):
    return f"n {st['n']:3d} ann {st['ann'] * 100:+5.1f}% vol {st['vol'] * 100:4.1f}% Sharpe {st['sharpe']:+.2f} t {st['t']:+.2f} maxDD {st['dd'] * 100:4.1f}% worst month {st['worst'] * 100:+.1f}%"


def main():
    P, R = load()
    ME = P.groupby(P.index.to_period("M")).last()
    dry = "--dry-run" in sys.argv
    print(f"spot {P.index[0].date()}..{P.index[-1].date()} ({len(P)} business days); rates through {R.dropna(how='all').index[-1]}; months of returns: " + ", ".join(f"{k} {len(pd.period_range(*v, freq='M'))}" for k, v in PH.items()))
    if dry:
        print("holding-month counts only; no returns computed"); return
    results = {}
    for name, kind in (("H1 CARRY", "carry"), ("H2 MOMENTUM", "mom"), ("H3 COMBO", "combo")):
        ibk, ftm = backtest(ME, R, kind, 0.0), backtest(ME, R, kind, MARKUP)
        results[name] = (ibk, ftm, kind)
    tm, per_ccy = tom(P); results["H4 TURN-OF-MONTH USD"] = (tm, tm, None)
    hits = []
    for name, (ibk, ftm, kind) in results.items():
        print(f"\n== {name}")
        for lab, s in (("INTERBANK", ibk), ("MT5-LIKE ", ftm)):
            print(f"  {lab} DEV  {fmt(stats(phase(s, 'DEV')))}\n  {lab} VAL  {fmt(stats(phase(s, 'VAL')))}\n  {lab} DEV+VAL {fmt(stats(pd.concat([phase(s, 'DEV'), phase(s, 'VAL')])))}") if kind else None
        if not kind:
            print(f"  DEV      {fmt(stats(phase(ftm, 'DEV')))}\n  VAL      {fmt(stats(phase(ftm, 'VAL')))}\n  DEV+VAL  {fmt(stats(pd.concat([phase(ftm, 'DEV'), phase(ftm, 'VAL')])))}")
        dv = pd.concat([phase(ftm, "DEV"), phase(ftm, "VAL")]); sd, sv, sa = stats(phase(ftm, "DEV")), stats(phase(ftm, "VAL")), stats(dv)
        c1 = sa["sharpe"] >= 0.4 and sa["t"] >= 2.5; c2 = sd["ann"] > 0 and sv["ann"] > 0
        if kind:
            ok = 0; shs = {}
            for c in CCY:
                x = pd.concat([phase(backtest(ME, R, kind, MARKUP, drop=c), p) for p in ("DEV", "VAL")]); shs[c] = round(stats(x)["sharpe"], 2); ok += stats(x)["sharpe"] >= 0.25
            c3 = ok >= 7; print(f"  leave-one-currency-out Sharpe (MT5-like, DEV+VAL): {shs} -> {ok} of 9 >= 0.25")
        else:
            ok = int((per_ccy > 0).sum()); c3 = ok >= 7; print(f"  per-currency USD-window mean positive: {ok} of 9 {({c: round(float(v) * 1e4, 1) for c, v in per_ccy.items()})} (bp per month)")
        print(f"  conditions: pooled Sharpe>=0.4 & t>=2.5: {c1} | positive in DEV and VAL: {c2} | not one currency: {c3}")
        if c1 and c2 and c3:
            hits.append(name)
    print(f"\nPASSED DEV+VAL (k = 4): {hits}")
    for name in hits:
        h = phase(results[name][1], "HOLD"); h1, h2 = h.loc["2021-01":"2023-12"], h.loc["2024-01":"2025-12"]
        print(f"HOLD (printed because DEV+VAL passed) {name}: {fmt(stats(h))} | halves Sharpe {stats(h1)['sharpe']:+.2f} / {stats(h2)['sharpe']:+.2f}")
    print("\nDESCRIPTIVE ONLY (not a decision): by-year net Sharpe at MT5-like costs")
    for name, (ibk, ftm, kind) in results.items():
        yrs = {int(y): round(stats(g)["sharpe"], 1) for y, g in ftm.groupby(ftm.index.year) if len(g) >= 6}
        print(f"  {name}: {yrs}")
    pd.concat({k: v[1] for k, v in results.items()}, axis=1).to_csv(Path(__file__).resolve().parent / "factor_returns_mt5broker_like.csv")


if __name__ == "__main__":
    main()
