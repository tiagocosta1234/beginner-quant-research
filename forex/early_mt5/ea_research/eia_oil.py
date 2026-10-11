"""Family OE: WTI around the EIA inventory report, exactly as registered in PREREG_EIA_OIL.md.   python -m mt5broker.ea_research.eia_oil --dev | --holdout"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[0] / "data_mt5"
STATE = HERE / "EIA_OIL_STATE.json"
LEDGER = HERE / "LEDGER.csv"
PER = {"DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
SLIP = 1e-5


def releases(last):
    hol = set(USFederalHolidayCalendar().holidays("2021-12-01", last))
    out = []
    for w in pd.date_range("2021-12-01", last, freq="W-WED"):
        mon = w - pd.Timedelta(days=2)
        if any((mon + pd.Timedelta(days=k)) in hol for k in range(3)): out.append(w + pd.Timedelta(days=1, hours=11))
        else: out.append(w + pd.Timedelta(hours=10, minutes=30))
    return out


def frame(last):
    d = pd.read_parquet(DATA / "WTI_M1_rates.parquet", columns=["t", "bo", "bc", "ao", "ac"]).sort_values("t").drop_duplicates("t"); d = d[(d.bo > 0) & (d.ao >= d.bo)]
    ny = pd.to_datetime(d.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("America/New_York").dt.tz_localize(None)
    d = d.assign(ny=ny.values).dropna(subset=["ny"]).drop_duplicates("ny").set_index("ny")
    rows = []
    for R in releases(last):
        need = [R - pd.Timedelta(minutes=1), R + pd.Timedelta(minutes=15), R + pd.Timedelta(minutes=16), R.normalize() + pd.Timedelta(hours=14, minutes=30), R.normalize() + pd.Timedelta(hours=9)]
        if not all(x in d.index for x in need): continue
        a, b, e, x, p = (d.loc[k] for k in need)
        first = ((b.bc + b.ac) / (a.bc + a.ac)) - 1; side = np.sign(first)
        mom = ((x.bo * (1 - SLIP)) / (e.ao * (1 + SLIP)) - 1) if side > 0 else (1 - (x.ao * (1 + SLIP)) / (e.bo * (1 - SLIP)))
        rev = (1 - (x.ao * (1 + SLIP)) / (e.bo * (1 - SLIP))) if side > 0 else ((x.bo * (1 - SLIP)) / (e.ao * (1 + SLIP)) - 1)
        pre = (a.bo * (1 - SLIP)) / (p.ao * (1 + SLIP)) - 1      # exit at R-1 open ~ its bar; uses the R-1 bar's open bid
        rows.append(dict(date=R.normalize(), first=first, OE1=mom * 1e4, OE2=rev * 1e4, OE3=pre * 1e4))
    F = pd.DataFrame(rows).set_index("date"); F["sd"] = F["first"].rolling(52, min_periods=26).std().shift(1); return F


def series(F, v):
    if v == "OE3": return F.OE3
    return F[v][(F["first"].abs() >= 0.5 * F.sd)]


def sl(x, p): return x[(x.index >= PER[p][0]) & (x.index <= PER[p][1])]


def st(x):
    n = len(x); return dict(n=n, mean=float(x.mean()), t=float(x.mean() / (x.std(ddof=1) / np.sqrt(n))) if n > 2 else np.nan, win=float((x > 0).mean()))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dev", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    if a.dev:
        F = frame("2025-12-31"); res = {}
        print(f"events with all minutes: {len(F)}")
        for v in ("OE1", "OE2", "OE3"):
            x = series(F, v)
            for p in ("DEV", "VAL"):
                s = st(sl(x, p)); print(f"{v} {p}: events {s['n']} | mean {s['mean']:+.1f} bp | win {100*s['win']:.1f}% | t {s['t']:+.2f}")
                with open(LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},eia_oil,{v},{p},{s['n']},{s['n']},,{s['mean']:.4f},,{s['t']:.2f},{s['win']:.3f},\n")
            d, va = st(sl(x, "DEV")), st(sl(x, "VAL")); res[v] = bool(d["t"] >= 2.6 and d["mean"] > 0 and va["mean"] > 0 and d["n"] >= 80)
            print(f"   {v} acceptance: {res[v]} | by year:", x[x.index <= '2025-12-31'].groupby(x[x.index <= '2025-12-31'].index.year).mean().round(1).to_dict())
        STATE.write_text(json.dumps(res))
    if a.holdout:
        res = json.loads(STATE.read_text()); live = [k for k, v in res.items() if v]
        if not live: print("No variant passed: the 2026 hold-out stays CLOSED.")
        else:
            F = frame("2026-09-30")
            for v in live: s = st(sl(series(F, v), "HOLD")); print(f"{v} HOLD 2026: events {s['n']} mean {s['mean']:+.1f} bp t {s['t']:+.2f}")
