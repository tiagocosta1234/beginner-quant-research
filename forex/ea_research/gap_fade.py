"""Family GF: opening-gap fade on US index CFDs, exactly as registered in PREREG_GAP_FADE.md.   python -m forex.ea_research.gap_fade --dry | --dev | --holdout"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[0] / "data_mt5"
STATE = HERE / "GAP_FADE_STATE.json"
LEDGER = HERE / "LEDGER.csv"
PER = {"DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
SLIP = 1e-5
COLS = ("bo", "bh", "bc", "ao", "al", "ac")


def session(m):
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet").sort_values("t").drop_duplicates("t"); d = d[(d.bo > 0) & (d.ao >= d.bo)]
    ny = pd.to_datetime(d.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("America/New_York").dt.tz_localize(None)
    d = d.assign(ny=ny.values).dropna(subset=["ny"]); ny = pd.DatetimeIndex(d.ny)
    k = (ny.hour * 60 + ny.minute - 570).to_numpy(); ok = (k >= 0) & (k < 390) & (ny.dayofweek < 5)
    d = d[ok]; day = ny[ok].normalize(); k = k[ok]; days = pd.DatetimeIndex(sorted(set(day))); di = days.get_indexer(day)
    M = {c: np.full((len(days), 390), np.nan) for c in COLS}
    for c in M: M[c][di, k] = d[c].to_numpy()
    good = np.isfinite(M["bc"]).sum(1) >= 300 & np.isfinite(M["bo"][:, 0]) & np.isfinite(M["bo"][:, 1])
    good = (np.isfinite(M["bc"]).sum(1) >= 300) & np.isfinite(M["bo"][:, 0]) & np.isfinite(M["bo"][:, 1]) & np.isfinite(M["bc"][:, 389])
    return days[good], {c: v[good] for c, v in M.items()}


def trades(m, last):
    days, M = session(m); keep = days <= pd.Timestamp(last); days = days[keep]; M = {c: v[keep] for c, v in M.items()}
    mid_close = (M["bc"][:, 389] + M["ac"][:, 389]) / 2; mid_open = (M["bo"][:, 0] + M["ao"][:, 0]) / 2
    rows = []
    for i in range(1, len(days)):
        if (days[i] - days[i - 1]).days > 4: continue
        prev = mid_close[i - 1]; g = mid_open[i] / prev - 1
        rows.append(dict(date=days[i], g=g, prev=prev, i=i))
    T = pd.DataFrame(rows).set_index("date"); T["sig"] = T.g.rolling(60, min_periods=40).std().shift(1)
    out = []
    for date, r in T.dropna().iterrows():
        i = int(r.i); side = -1 if r.g > 0 else 1
        e = M["ao"][i, 1] * (1 + SLIP) if side > 0 else M["bo"][i, 1] * (1 - SLIP)
        res = {}
        for nm, kend in (("x1555", 385), ("x1100", 90)):
            seg = M["bh"][i, 1:kend] if side > 0 else M["al"][i, 1:kend]
            hit = np.nonzero(seg >= r.prev)[0] if side > 0 else np.nonzero(seg <= r.prev)[0]
            if len(hit) and (r.prev - e) * side > 0: px = r.prev
            else: px = M["bo"][i, kend] * (1 - SLIP) if side > 0 else M["ao"][i, kend] * (1 + SLIP)
            res[nm] = side * (px - e) / e * 1e4
        out.append(dict(date=date, mkt=m, z=abs(r.g) / r.sig, **res))
    return pd.DataFrame(out)


def all_trades(last): return pd.concat([trades(m, last) for m in ("SP", "NSDQ", "DOW")], ignore_index=True)


def variant(T, v):
    if v == "GF1": X = T[(T.z >= 0.5) & (T.z <= 2.0)].set_index("date").x1555
    elif v == "GF2": X = T[T.z > 2.0].set_index("date").x1555
    else: X = T[(T.z >= 0.5) & (T.z <= 2.0)].set_index("date").x1100
    return X, X.groupby(level=0).mean()


def sl(x, p): return x[(x.index >= PER[p][0]) & (x.index <= PER[p][1])]


def st(x):
    n = len(x); return dict(n=n, mean=float(x.mean()), t=float(x.mean() / (x.std(ddof=1) / np.sqrt(n))) if n > 2 else np.nan, win=float((x > 0).mean()))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); [ap.add_argument(f"--{k}", action="store_true") for k in ("dry", "dev", "holdout")]; a = ap.parse_args()
    if a.dry:
        T = trades("NSDQ", "2022-03-31"); print(T.head(8).round(2)); print("rows", len(T), "| share 0.5-2 sigma", ((T.z >= .5) & (T.z <= 2)).mean().round(2), "| >2", (T.z > 2).mean().round(2))
    if a.dev:
        T = all_trades("2025-12-31"); res = {}
        for v in ("GF1", "GF2", "GF3"):
            X, D = variant(T, v)
            for p in ("DEV", "VAL"):
                s, tr = st(sl(D, p)), st(sl(X, p)); print(f"{v} {p}: trades {tr['n']} on {s['n']} days | per trade {tr['mean']:+.2f} bp win {100*tr['win']:.1f}% | daily mean {s['mean']:+.2f} bp t {s['t']:+.2f}")
                with open(LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},gap_fade,{v},{p},{s['n']},{tr['n']},,{tr['mean']:.4f},,{s['t']:.2f},{tr['win']:.3f},\n")
            d, va = st(sl(D, "DEV")), st(sl(D, "VAL")); res[v] = bool(d["t"] >= 2.4 and d["mean"] > 0 and va["mean"] > 0 and d["n"] >= 150)
            y = X[X.index <= "2025-12-31"]; print(f"   {v} acceptance: {res[v]} | per trade by year:", y.groupby(y.index.year).mean().round(2).to_dict())
        STATE.write_text(json.dumps(res))
    if a.holdout:
        res = json.loads(STATE.read_text()); live = [k for k, v in res.items() if v]
        if not live: print("No variant passed: the 2026 hold-out stays CLOSED.")
        else:
            T = all_trades("2026-09-30")
            for v in live:
                X, D = variant(T, v); s = st(sl(D, "HOLD")); print(f"{v} HOLD 2026: days {s['n']} mean {s['mean']:+.2f} bp t {s['t']:+.2f} | trades {len(sl(X, 'HOLD'))}")
                with open(LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},gap_fade,{v},HOLD,{s['n']},{len(sl(X, 'HOLD'))},,{s['mean']:.4f},,{s['t']:.2f},{s['win']:.3f},\n")
