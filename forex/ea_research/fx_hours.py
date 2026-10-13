"""Family RB: currencies weaken in their own working hours, exactly as registered in PREREG_FX_HOURS.md.   python -m forex.ea_research.fx_hours --dev | --holdout"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[0] / "data_mt5"
STATE = HERE / "FX_HOURS_STATE.json"
LEDGER = HERE / "LEDGER.csv"
PER = {"DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
SLIP = 1e-5
LEGS = {"RB1": [("EURUSD", -1, 800, 1200, "Europe/London"), ("GBPUSD", -1, 800, 1200, "Europe/London"), ("USDCHF", 1, 800, 1200, "Europe/London")],
        "RB2": [("EURUSD", 1, 1400, 1900, "Europe/London"), ("GBPUSD", 1, 1400, 1900, "Europe/London"), ("USDCHF", -1, 1400, 1900, "Europe/London")],
        "RB4": [("USDJPY", 1, 900, 1500, "Asia/Tokyo")]}


def leg(m, side, h0, h1, tz, last):
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "ao"]).sort_values("t").drop_duplicates("t"); d = d[(d.bo > 0) & (d.ao >= d.bo)]
    loc = pd.to_datetime(d.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert(tz)
    d = d.assign(day=loc.dt.tz_localize(None).dt.normalize(), hm=loc.dt.hour * 100 + loc.dt.minute).dropna(subset=["day"])
    d = d[d.hm.isin([h0, h1]) & (d.day.dt.dayofweek < 5) & (d.day <= last)].drop_duplicates(["day", "hm"])
    W = d.pivot(index="day", columns="hm", values=["bo", "ao"]).dropna()
    if side > 0: r = (W[("bo", h1)] * (1 - SLIP)) / (W[("ao", h0)] * (1 + SLIP)) - 1
    else: r = 1 - (W[("ao", h1)] * (1 + SLIP)) / (W[("bo", h0)] * (1 - SLIP))
    return r * 1e4


def daily(v, last):
    if v == "RB3": a, b = daily("RB1", last), daily("RB2", last); idx = a.index.intersection(b.index); return a[idx] + b[idx]
    L = [leg(*x, last) for x in LEGS[v]]; idx = L[0].index
    for x in L[1:]: idx = idx.intersection(x.index)
    return sum(x[idx] for x in L) / len(L)


def sl(x, p): return x[(x.index >= PER[p][0]) & (x.index <= PER[p][1])]


def st(x):
    n = len(x); return dict(n=n, mean=float(x.mean()), t=float(x.mean() / (x.std(ddof=1) / np.sqrt(n))), win=float((x > 0).mean()))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dev", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    if a.dev:
        res = {}
        for v in ("RB1", "RB2", "RB3", "RB4"):
            x = daily(v, "2025-12-31")
            for p in ("DEV", "VAL"):
                s = st(sl(x, p)); print(f"{v} {p}: days {s['n']} | mean {s['mean']:+.2f} bp/day | win {100*s['win']:.1f}% | t {s['t']:+.2f}")
                with open(LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},fx_hours,{v},{p},{s['n']},{s['n']},,{s['mean']:.4f},,{s['t']:.2f},{s['win']:.3f},\n")
            d, va = st(sl(x, "DEV")), st(sl(x, "VAL")); res[v] = bool(d["t"] >= 2.5 and d["mean"] > 0 and va["mean"] > 0)
            y = x[x.index <= "2025-12-31"]; print(f"   {v} acceptance: {res[v]} | by year:", y.groupby(y.index.year).mean().round(2).to_dict())
        STATE.write_text(json.dumps(res))
    if a.holdout:
        res = json.loads(STATE.read_text()); live = [k for k, v in res.items() if v]
        if not live: print("No variant passed: the 2026 hold-out stays CLOSED.")
        for v in live:
            s = st(sl(daily(v, "2026-09-30"), "HOLD")); print(f"{v} HOLD 2026: days {s['n']} mean {s['mean']:+.2f} bp t {s['t']:+.2f}")
            with open(LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},fx_hours,{v},HOLD,{s['n']},{s['n']},,{s['mean']:.4f},,{s['t']:.2f},{s['win']:.3f},\n")
