"""Family LF: reversal after the London 16:00 fix, exactly as registered in PREREG_LONDON_FIX.md.   python -m forex.ea_research.london_fix --dev | --holdout | --dry"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[0] / "data_mt5"
STATE = HERE / "LONDON_FIX_STATE.json"
LEDGER = HERE / "LEDGER.csv"
PAIRS = ("EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCHF", "USDCAD")
PER = {"DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
SLIP = 1e-5
HMS = (1530, 1559, 1606, 1700, 1900)


def pair_trades(m: str, last: str) -> pd.DataFrame:
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "bc", "ao", "ac"]).sort_values("t").drop_duplicates("t")
    d = d[(d.bo > 0) & (d.ao >= d.bo)]
    lo = pd.to_datetime(d.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("Europe/London")
    d = d.assign(day=lo.dt.tz_localize(None).dt.normalize(), hm=lo.dt.hour * 100 + lo.dt.minute).dropna(subset=["day"])
    d = d[d.hm.isin(HMS) & (d.day.dt.dayofweek < 5) & (d.day <= last)].drop_duplicates(["day", "hm"])
    W = d.pivot(index="day", columns="hm", values=["bo", "bc", "ao", "ac"]).dropna()
    r = ((W[("bc", 1559)] + W[("ac", 1559)]) / (W[("bo", 1530)] + W[("ao", 1530)]) - 1)
    sig = r.rolling(60, min_periods=40).std().shift(1); side = -np.sign(r)
    out = pd.DataFrame({"mkt": m, "r_sig": r / sig, "side": side})
    for ex in (1700, 1900):
        lng = (W[("bo", ex)] * (1 - SLIP)) / (W[("ao", 1606)] * (1 + SLIP)) - 1
        sht = (W[("bo", 1606)] * (1 - SLIP)) / (W[("ao", ex)] * (1 + SLIP)) - 1
        out[f"x{ex}"] = np.where(side > 0, lng, np.where(side < 0, sht, np.nan)) * 1e4
    return out.dropna(subset=["side"])


def trades(last: str) -> pd.DataFrame:
    return pd.concat([pair_trades(m, last) for m in PAIRS])


def variant(T: pd.DataFrame, v: str):
    if v == "LF1": X = T.x1700
    elif v == "LF2": X = T.x1700[T.r_sig.abs() > 1.0]
    else: X = T.x1900[T.r_sig.abs() > 1.0]
    X = X.dropna(); daily = X.groupby(level=0).mean(); return X, daily


def sl(x, p): return x[(x.index >= PER[p][0]) & (x.index <= PER[p][1])]


def st(x):
    n = len(x); return dict(n=n, mean=float(x.mean()), t=float(x.mean() / (x.std(ddof=1) / np.sqrt(n))), win=float((x > 0).mean()))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); [ap.add_argument(f"--{k}", action="store_true") for k in ("dev", "holdout", "dry")]; a = ap.parse_args()
    if a.dry:
        T = pair_trades("EURUSD", "2022-03-31"); print(T.head(8)); print("rows", len(T), "| share |r|>1 sigma", (T.r_sig.abs() > 1).mean().round(3))
    if a.dev:
        T = trades("2025-12-31"); res = {}
        for v in ("LF1", "LF2", "LF3"):
            X, D = variant(T, v)
            for p in ("DEV", "VAL"):
                s, tr = st(sl(D, p)), st(sl(X, p)); print(f"{v} {p}: trades {tr['n']} | per trade {tr['mean']:+.2f} bp win {100*tr['win']:.1f}% | daily portfolio days {s['n']} mean {s['mean']:+.2f} bp t {s['t']:+.2f}")
                with open(LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},london_fix,{v},{p},{s['n']},{tr['n']},,{tr['mean']:.4f},,{s['t']:.2f},{tr['win']:.3f},\n")
            d, va, nd = st(sl(D, "DEV")), st(sl(D, "VAL")), len(sl(X, "DEV")); res[v] = bool(d["t"] >= 2.4 and d["mean"] > 0 and va["mean"] > 0 and nd >= 300)
            Y = X[X.index <= "2025-12-31"]; print(f"   {v} acceptance: {res[v]} | per trade by year:", Y.groupby(Y.index.year).mean().round(2).to_dict(), "| by pair 2022-25:", T.loc[T.index <= "2025-12-31"].groupby("mkt").x1700.mean().round(2).to_dict() if v == "LF1" else "")
        STATE.write_text(json.dumps(res))
    if a.holdout:
        res = json.loads(STATE.read_text()); live = [k for k, v in res.items() if v]
        if not live: print("No variant passed: the 2026 hold-out stays CLOSED.")
        else:
            T = trades("2026-09-30")
            for v in live:
                X, D = variant(T, v); s = st(sl(D, "HOLD")); print(f"{v} HOLD 2026: days {s['n']} mean {s['mean']:+.2f} bp t {s['t']:+.2f} | trades {len(sl(X, 'HOLD'))} per trade {sl(X, 'HOLD').mean():+.2f} bp")
                with open(LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},london_fix,{v},HOLD,{s['n']},{len(sl(X, 'HOLD'))},,{s['mean']:.4f},,{s['t']:.2f},{s['win']:.3f},\n")
