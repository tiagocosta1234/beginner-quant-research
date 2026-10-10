"""Family N (US index overnight), exactly as registered in PREREG_OVERNIGHT.md.
   python -m mt5broker.ea_research.overnight --dev | --holdout"""
from __future__ import annotations

import argparse
import datetime as dt

import numpy as np
import pandas as pd

from mt5broker.ea_research import event_macro as V

MKTS = ("SP", "NSDQ", "DOW")
PER = {"DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
LEDGER = V.LEDGER


def table(last="2025-12-31") -> pd.DataFrame:
    rows = []
    days = pd.bdate_range("2022-01-03", last)
    for i, D in enumerate(days[:-1]):
        N = days[i + 1]; d, n = str(D.date()), str(N.date()); wk = (N - D).days > 1
        r = dict(date=D, dow=D.dayofweek, weekend=wk)
        for m in MKTS:
            qo, qc, qn = V.quote(m, V.server_s(d, 9, 35)), V.quote(m, V.server_s(d, 15, 55)), V.quote(m, V.server_s(n, 9, 35))
            if qo is None or qc is None or qn is None: r[m] = np.nan; continue
            r[m] = (qn[0] / qc[1] - 1.0) * 1e4 - 2 * V.SLIP * 1e4                       # night, net (buy ask, sell bid)
            r[m + "_g"] = ((qn[0] + qn[1]) / (qc[0] + qc[1]) - 1.0) * 1e4                # night at mids
            r[m + "_day"] = ((qc[0] + qc[1]) / (qo[0] + qo[1]) - 1.0) * 1e4              # day session at mids
        rows.append(r)
    T = pd.DataFrame(rows); T["night"] = T[list(MKTS)].mean(axis=1, skipna=False); T["night_g"] = T[[m + "_g" for m in MKTS]].mean(axis=1, skipna=False)
    T["day"] = T[[m + "_day" for m in MKTS]].mean(axis=1, skipna=False); return T.dropna(subset=["night", "day"])


def describe(T):
    W, X = T[T.weekend], T[~T.weekend]
    print("== descriptive: Mon-Thu nights (15:55 ET -> 09:35 ET next day), NET of the spread, bp ==")
    for y in sorted(X.date.dt.year.unique()):
        for m in MKTS + ("night",):
            x = X[X.date.dt.year == y][m]
            print(f"  {y} {m:6s} n {len(x):3d} | P(>0) {100*(x > 0).mean():4.1f}% | mean {x.mean():+6.2f} median {x.median():+6.2f} sd {x.std():6.1f} skew {x.skew():+5.2f} | 5% {x.quantile(.05):+7.1f} 1% {x.quantile(.01):+7.1f} worst {x.min():+7.1f}")
    print(f"  day session (09:35->15:55, mids) equal-weight: mean {X.day.mean():+.2f} bp, P(>0) {100*(X.day > 0).mean():.1f}% | night gross (mids) mean {X.night_g.mean():+.2f} | spread cost per night {(X.night_g - X.night).mean():.2f} bp")
    print(f"  Friday->Monday window (not traded): n {len(W)} | P(>0) {100*(W.night > 0).mean():.1f}% | mean {W.night.mean():+.2f} sd {W.night.std():.1f} worst {W.night.min():+.1f}")
    print("  P(night > 0) by weekday of D:", {["Mon", "Tue", "Wed", "Thu"][k]: f"{100*(g.night > 0).mean():.1f}% (mean {g.night.mean():+.1f}, n {len(g)})" for k, g in X.groupby("dow")})
    print("  conditional on the day session of D:", {k: f"P(>0) {100*(g.night > 0).mean():.1f}% mean {g.night.mean():+.2f} (n {len(g)})" for k, g in X.groupby(np.where(X.day < 0, "down day", "up day"))})
    X = X.assign(tq=pd.qcut(X.day, 3, labels=["big down", "middle", "big up"]))
    print("  by tercile of the day move:", {k: f"P(>0) {100*(g.night > 0).mean():.1f}% mean {g.night.mean():+.2f}" for k, g in X.groupby("tq", observed=True)})


def trial(T, name, per):
    X = T[~T.weekend]; a, b = PER[per]; X = X[(X.date >= a) & (X.date <= b)]
    x = X.night if name == "N1" else X.night.where(X.day < 0, 0.0)
    act = x[x != 0] if name == "N2" else x; n = len(x)
    t = x.mean() / (x.std(ddof=1) / np.sqrt(n))
    print(f"{name} {per}: nights {n} (active {len(act)}) | mean {x.mean():+.2f} bp/night | active mean {act.mean():+.2f} | P(active>0) {100*(act > 0).mean():.1f}% | t {t:+.2f} | worst {x.min():+.1f}")
    with open(LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},overnight,{name},{per},{n},{len(act)},,{x.mean():.4f},,{t:.2f},{(act > 0).mean():.3f},\n")
    return x.mean(), t


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dev", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    if a.dev:
        T = table(); describe(T); res = {}
        for nm in ("N1", "N2"):
            md, td = trial(T, nm, "DEV"); mv, tv = trial(T, nm, "VAL"); res[nm] = md > 0 and td >= 2.0 and mv > 0
            print(f"   {nm}: acceptance 1-2 {'PASSED (hold-out may be opened)' if res[nm] else 'FAILED (closed)'}")
        T.to_parquet("D:/finance/tmp/overnight_dev.parquet")
    if a.holdout:
        T = table("2026-09-30")
        for nm in ("N1", "N2"): trial(T, nm, "HOLD")
