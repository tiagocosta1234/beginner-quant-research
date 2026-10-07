"""S1 (pre-registered in forex/early_mt5/factor_lab/PREREG_TREND.md): diversified time-series trend following over 21 tradable markets, 2001-2026.
   python -m mt5broker.factor_lab.trend_test --dry-run     coverage only
   python -m mt5broker.factor_lab.trend_test               the pre-registered run"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.factor_lab import factor_test as ft

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "futures" / "data"
IDX = ["spx", "ndx", "dji", "ftse", "dax", "cac", "n225", "hsi"]
FUT = {"GC": "GC=F", "SI": "SI=F", "HG": "HG=F", "ZN": "ZN=F"}
CLASS = {**{c: "EQUITY" for c in IDX}, "GC": "METAL", "SI": "METAL", "HG": "METAL", "ZN": "RATE", **{c: "FX" for c in ft.CCY}}
TC = {**{c: 1.5 for c in IDX}, "GC": 1.5, "SI": 1.5, "HG": 1.5, "ZN": 1.0, **ft.TC.to_dict()}      # bp per unit of notional traded
MARKUP = 0.02
PH = {"DEV": ("2001-01", "2012-12"), "VAL": ("2013-01", "2020-12"), "HOLD": ("2021-01", "2026-08")}


def closes():
    px, clipped = {}, 0
    for c in IDX:
        d = pd.read_csv(DATA / "external_index_daily" / f"{c}.csv", parse_dates=["date"]).set_index("date").close
        px[c] = d
    for k, f in FUT.items():
        d = pd.read_csv(DATA / "daily_ohlc" / f"{f}_yahoo_ohlc.csv", parse_dates=["date"]).set_index("date").close
        px[k] = d
    P, R = ft.load()
    for c in ft.CCY:
        px[c] = P[c]
    out = {}
    for k, s in px.items():
        s = s.dropna(); s = s[s > 0]; s = s[~s.index.duplicated()].sort_index(); r = s.pct_change(); bad = r.abs() > 0.15; clipped += int(bad.sum())
        if bad.any():                                                    # a >15% daily move is a data / roll artefact for these markets: set it to 0
            s = (1 + r.where(~bad, 0.0).fillna(0.0)).cumprod() * s.iloc[0]
        out[k] = s
    return out, R, clipped


def monthly(out):
    ME, VOL = {}, {}
    for k, s in out.items():
        per = s.index.to_period("M"); ME[k] = s.groupby(per).last()
        r = np.log(s).diff(); v = r.rolling(63).std() * np.sqrt(252); VOL[k] = v.groupby(per).last()
    return pd.DataFrame(ME), pd.DataFrame(VOL)


def run(ME, VOL, R, kind, markup, drop_class=None):
    cols = [c for c in ME.columns if CLASS[c] != drop_class]
    M = ME[cols]; r12 = M / M.shift(12) - 1; r3 = M / M.shift(3) - 1; r1 = M / M.shift(1) - 1
    sig = np.sign(r12) if kind == "H1" else (np.sign(r1) + np.sign(r3) + np.sign(r12)) / 3
    lev = (0.10 / VOL[cols]).clip(upper=3.0)
    ok = sig.notna() & lev.notna() & M.shift(-1).notna()
    n = ok.sum(axis=1).replace(0, np.nan)
    W = (sig * lev).where(ok).div(n, axis=0)
    spot = (M.shift(-1) / M - 1)
    carry = pd.DataFrame(0.0, index=M.index, columns=cols)
    for c in cols:
        if CLASS[c] == "FX":
            carry[c] = ((R[c] - R["USD"]).shift(-1) / 100 / 12).reindex(M.index)
    gross = (W * (spot + carry)).sum(axis=1, min_count=1)
    turn = W.fillna(0).diff().abs(); turn.iloc[0] = W.fillna(0).iloc[0].abs()
    cost = (turn * pd.Series(TC)[cols] / 1e4).sum(axis=1) + W.abs().sum(axis=1) * markup / 12
    net = (gross - cost).loc["2001-01":"2026-07"].dropna(); net.index = net.index + 1
    return net


def phase(s, name):
    a, b = PH[name]; return s.loc[a:b]


def main():
    out, R, clipped = closes(); ME, VOL = monthly(out)
    print(f"markets {len(out)}: " + ", ".join(f"{k} {s.index[0].year}" for k, s in out.items()) + f" | daily moves >15% set to 0: {clipped}")
    print("months per phase:", {k: len(pd.period_range(*v, freq='M')) for k, v in PH.items()})
    if "--dry-run" in sys.argv:
        return
    res = {k: (run(ME, VOL, R, k, 0.0), run(ME, VOL, R, k, MARKUP)) for k in ("H1", "H2")}
    hits = []
    for name, (ib, fl) in res.items():
        print(f"\n== {name}")
        for lab, s in (("INTERBANK-LIKE", ib), ("MT5-LIKE    ", fl)):
            for p in ("DEV", "VAL"):
                print(f"  {lab} {p:4} {ft.fmt(ft.stats(phase(s, p)))}")
            print(f"  {lab} DEV+VAL {ft.fmt(ft.stats(pd.concat([phase(s, 'DEV'), phase(s, 'VAL')])))}")
        dv = pd.concat([phase(fl, "DEV"), phase(fl, "VAL")]); sa = ft.stats(dv); sd, sv = ft.stats(phase(fl, "DEV")), ft.stats(phase(fl, "VAL"))
        c1 = sa["sharpe"] >= 0.4 and sa["t"] >= 2.3; c2 = sd["ann"] > 0 and sv["ann"] > 0
        okc = 0; sh = {}
        for cl in ("EQUITY", "METAL", "RATE", "FX"):
            x = run(ME, VOL, R, name, MARKUP, drop_class=cl); x = pd.concat([phase(x, "DEV"), phase(x, "VAL")]); sh[cl] = round(ft.stats(x)["sharpe"], 2); okc += ft.stats(x)["sharpe"] >= 0.25
        c3 = okc >= 3
        print(f"  drop-one-class pooled Sharpe (MT5-like): {sh} -> {okc} of 4 >= 0.25")
        print(f"  conditions: pooled Sharpe>=0.4 & t>=2.3: {c1} | positive in DEV and VAL: {c2} | not one class: {c3}")
        if c1 and c2 and c3:
            hits.append(name)
    print(f"\nPASSED DEV+VAL (k = 2): {hits}")
    for name in hits:
        h = phase(res[name][1], "HOLD"); a, b = h.loc["2021-01":"2023-12"], h.loc["2024-01":"2026-08"]
        print(f"HOLD (printed because DEV+VAL passed) {name}: {ft.fmt(ft.stats(h))} | halves Sharpe {ft.stats(a)['sharpe']:+.2f} / {ft.stats(b)['sharpe']:+.2f}")
    print("\nDESCRIPTIVE ONLY: by-year net Sharpe (MT5-like)")
    for name, (ib, fl) in res.items():
        print(f"  {name}:", {int(y): round(ft.stats(g)['sharpe'], 1) for y, g in fl.groupby(fl.index.year) if len(g) >= 6})
    pd.concat({k: v[1] for k, v in res.items()}, axis=1).to_csv(Path(__file__).resolve().parent / "trend_returns_mt5broker_like.csv")


if __name__ == "__main__":
    main()
