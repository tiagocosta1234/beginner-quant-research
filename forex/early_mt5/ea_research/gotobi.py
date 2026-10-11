"""Family GT: USDJPY into / after the Tokyo 09:55 fix, exactly as registered in PREREG_GOTOBI.md.   python -m mt5broker.ea_research.gotobi --dev | --holdout"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[0] / "data_mt5"
STATE = HERE / "GOTOBI_STATE.json"
LEDGER = HERE / "LEDGER.csv"
PER = {"DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
SLIP = 1e-5


def gotobi(day: pd.Timestamp) -> bool:
    for k in range(0, 3):                                   # a weekend gotobi moves to the previous Friday
        c = day + pd.Timedelta(days=k)
        if k and c.dayofweek < 5: break
        last = (c + pd.offsets.MonthEnd(0)).day
        if (c.day in (5, 10, 15, 20, 25) or c.day == last) and (k == 0 or c.dayofweek >= 5): return True
    return False


def frame(last: str) -> pd.DataFrame:
    d = pd.read_parquet(DATA / "USDJPY_M1_rates.parquet", columns=["t", "bo", "ao"]).sort_values("t").drop_duplicates("t")
    tk = pd.to_datetime(d.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("Asia/Tokyo")
    d = d.assign(day=tk.dt.tz_localize(None).dt.normalize(), hm=tk.dt.hour * 100 + tk.dt.minute).dropna(subset=["day"])
    d = d[(d.hm.isin([800, 954, 956, 1100])) & (d.day.dt.dayofweek < 5) & (d.day <= last)]
    P = d.pivot_table(index="day", columns="hm", values=["bo", "ao"], aggfunc="first")
    out = pd.DataFrame(index=P.index)
    out["gt1"] = (P[("bo", 954)] / (P[("ao", 800)] * (1 + SLIP)) - 1 - SLIP) * 1e4
    out["gt3"] = ((P[("bo", 956)] * (1 - SLIP)) / P[("ao", 1100)] - 1 - SLIP) * 1e4
    out["gotobi"] = [gotobi(x) for x in out.index]
    return out


def series(F: pd.DataFrame, v: str) -> pd.Series:
    return {"GT1": F.gt1, "GT2": F.gt1[F.gotobi], "GT3": F.gt3[F.gotobi]}[v].dropna()


def st(x):
    n = len(x); return dict(n=n, mean=float(x.mean()), t=float(x.mean() / (x.std(ddof=1) / np.sqrt(n))), win=float((x > 0).mean()))


def sl(x, p): return x[(x.index >= PER[p][0]) & (x.index <= PER[p][1])]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dev", action="store_true"); ap.add_argument("--holdout", action="store_true"); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    if a.dry:
        F = frame("2022-02-28"); print(F.head(12)); print("gotobi days Jan-Feb 2022:", [str(x.date()) for x in F.index[F.gotobi]])
    if a.dev:
        F = frame("2025-12-31"); res = {}
        for v in ("GT1", "GT2", "GT3"):
            x = series(F, v)
            for p in ("DEV", "VAL"):
                s = st(sl(x, p)); print(f"{v} {p}: trades {s['n']} | mean {s['mean']:+.2f} bp | win {100*s['win']:.1f}% | t {s['t']:+.2f}")
                with open(LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},gotobi,{v},{p},{s['n']},{s['n']},,{s['mean']:.4f},,{s['t']:.2f},{s['win']:.3f},\n")
            d, va = st(sl(x, "DEV")), st(sl(x, "VAL")); res[v] = bool(d["t"] >= 2.4 and d["mean"] > 0 and va["mean"] > 0 and d["n"] >= 100)
            y = x[x.index <= "2025-12-31"]; print(f"   {v} acceptance: {res[v]} | by year mean bp:", y.groupby(y.index.year).mean().round(2).to_dict())
        STATE.write_text(json.dumps(res))
    if a.holdout:
        res = json.loads(STATE.read_text()); live = [k for k, v in res.items() if v]
        if not live: print("No variant passed: the 2026 hold-out stays CLOSED.")
        F = frame("2026-09-30")
        for v in live:
            s = st(sl(series(F, v), "HOLD")); print(f"{v} HOLD 2026: trades {s['n']} mean {s['mean']:+.2f} bp t {s['t']:+.2f} win {100*s['win']:.1f}%")
            with open(LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},gotobi,{v},HOLD,{s['n']},{s['n']},,{s['mean']:.4f},,{s['t']:.2f},{s['win']:.3f},\n")
