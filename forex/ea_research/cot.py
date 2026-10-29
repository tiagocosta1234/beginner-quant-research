"""Family P: CFTC COT positioning, as registered in PREREG_COT.md (DJIA uses the consolidated code 12460+, the x$5 series has gaps).
   python -m forex.ea_research.cot --dev | --holdout"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

from forex.ea_research import event_macro as V

HERE = Path(__file__).resolve().parent
STATE = HERE / "COT_STATE.json"
CODES = {"088691": ("XAUUSD", 1), "084691": ("XAGUSD", 1), "067651": ("WTI", 1), "13874A": ("SP", 1), "209742": ("NSDQ", 1), "12460+": ("DOW", 1), "099741": ("EURUSD", 1), "097741": ("USDJPY", -1),
         "096742": ("GBPUSD", 1), "232741": ("AUDUSD", 1), "090741": ("USDCAD", -1), "092741": ("USDCHF", -1), "112741": ("NZDUSD", 1)}
PER = {"DEV": ("2021-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}


def cot():
    d = pd.concat([pd.read_csv(f, low_memory=False, dtype={"CFTC Contract Market Code": str}) for f in sorted(glob.glob("data/data_macro/cot/deacot*/annual.txt"))])
    d["code"] = d["CFTC Contract Market Code"].str.strip(); d = d[d.code.isin(CODES)]
    d["date"] = pd.to_datetime(d["As of Date in Form YYYY-MM-DD"]); d["net"] = (d["Noncommercial Positions-Long (All)"] - d["Noncommercial Positions-Short (All)"]) / d["Open Interest (All)"]
    return d[["code", "date", "net"]].drop_duplicates(["code", "date"]).sort_values(["code", "date"])


def q(m, t):
    x = V.mkt(m); i = x.index.searchsorted(t)
    if i >= len(x) or x.index[i] > t + 1800: return None
    r = x.iloc[i]; return float(r.bo), float(r.ao)


def ts(day): return int((pd.Timestamp(f"{day} 01:30") - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1))


def weeks(last):
    C = cot(); rows = []
    for code, g in C.groupby("code"):
        m, sgn = CODES[code]; g = g.set_index("date").net
        pct = g.rolling(52, min_periods=52).apply(lambda w: (w[:-1] < w[-1]).mean() + 0.5 * (w[:-1] == w[-1]).mean(), raw=True); ch4 = g - g.shift(4)
        for R in g.index:
            mon = R + pd.Timedelta(days=6); nxt = mon + pd.Timedelta(days=7)
            if mon < pd.Timestamp("2021-01-01") or nxt > pd.Timestamp(last) + pd.Timedelta(days=7): continue
            a, b = q(m, ts(mon.date())), q(m, ts(nxt.date()))
            if a is None or b is None: continue
            long_ = (b[0] / a[1] - 1) * 1e4 - 2 * V.SLIP * 1e4; short_ = (a[0] / b[1] - 1) * 1e4 - 2 * V.SLIP * 1e4
            p1 = 0 if not np.isfinite(pct[R]) else (-1 if pct[R] >= 0.9 else (1 if pct[R] <= 0.1 else 0)); p2 = 0 if not np.isfinite(ch4[R]) else int(np.sign(ch4[R]))
            for nm, s in (("P1", p1), ("P2", p2)):
                side = s * sgn
                if side != 0: rows.append(dict(trial=nm, week=mon, mkt=m, side=side, net=long_ if side > 0 else short_))
    return pd.DataFrame(rows)


def st(X, p):
    a, b = PER[p]; w = X[(X.week >= a) & (X.week <= b)].groupby("week").net.mean(); n = len(w)
    return dict(n=n, pos=int(((X.week >= a) & (X.week <= b)).sum()), mean=float(w.mean()), t=float(w.mean() / (w.std(ddof=1) / np.sqrt(n))) if n > 2 else np.nan, win=float((w > 0).mean()))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dev", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    if a.dev:
        W = weeks("2025-12-31"); res = {}
        for nm, X in W.groupby("trial"):
            for p in ("DEV", "VAL"):
                s = st(X, p); print(f"{nm} {p}: active weeks {s['n']} (market-weeks {s['pos']}) | weekly mean {s['mean']:+.2f} bp | win {100*s['win']:.1f}% | t {s['t']:+.2f}")
                with open(V.LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},cot,{nm},{p},{s['n']},{s['pos']},,{s['mean']:.4f},,{s['t']:.2f},{s['win']:.3f},\n")
            d, v = st(X, "DEV"), st(X, "VAL"); res[nm] = bool(d["mean"] > 0 and d["t"] >= 2.24 and d["n"] >= 100 and v["mean"] > 0)
            Y = X[X.week <= "2025-12-31"]; print(f"   {nm} acceptance 1-2: {res[nm]} | per market (2021-25 mean bp, n):", {k: (round(float(g.net.mean()), 1), len(g)) for k, g in Y.groupby("mkt")})
        STATE.write_text(json.dumps(res))
    if a.holdout:
        res = json.loads(STATE.read_text()); live = [k for k, v in res.items() if v]
        if not live: print("No trial passed acceptance 1-2: the 2026 hold-out stays CLOSED.")
        else:
            W = weeks("2026-09-30")
            for nm in live: s = st(W[W.trial == nm], "HOLD"); print(f"{nm} HOLD: weeks {s['n']} mean {s['mean']:+.2f} bp t {s['t']:+.2f}")
