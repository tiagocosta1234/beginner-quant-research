"""Family NA: noise-area intraday momentum, exactly as registered in PREREG_NOISE_AREA.md.   python -m mt5broker.ea_research.noise_area --dev | --holdout"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[0] / "data_mt5"
STATE = HERE / "NOISE_AREA_STATE.json"
LEDGER = HERE / "LEDGER.csv"
PER = {"DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
SLIP = 1e-5
MARKS = [30 + 30 * i for i in range(12)]          # minutes after 09:30 of 10:00 .. 15:30


def session(m: str):
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet").sort_values("t").drop_duplicates("t")
    d = d[(d.bo > 0) & (d.ao >= d.bo)]
    ny = pd.to_datetime(d.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("America/New_York").dt.tz_localize(None)
    d = d.assign(ny=ny.values).dropna(subset=["ny"]); ny = pd.DatetimeIndex(d.ny)  # FIX 2026-10-11: values are New York wall time (the first run used UTC by mistake)
    k = (ny.hour * 60 + ny.minute - 570).to_numpy(); ok = (k >= 0) & (k < 390) & (ny.dayofweek < 5)
    d = d[ok]; day = ny[ok].normalize(); k = k[ok]
    days = pd.DatetimeIndex(sorted(set(day))); di = days.get_indexer(day); n = len(days)
    M = {c: np.full((n, 390), np.nan) for c in ("bo", "ao", "bc", "ac")}
    for c in M: M[c][di, k] = d[c].to_numpy()
    good = np.isfinite(M["bc"]).sum(1) >= 300
    for c in M: M[c] = pd.DataFrame(M[c]).ffill(axis=1).bfill(axis=1).to_numpy()
    return days[good], {c: v[good] for c, v in M.items()}


def run(m: str, variant: str, last: str) -> pd.DataFrame:
    days, M = session(m); keep = days <= pd.Timestamp(last); days = days[keep]; M = {c: v[keep] for c, v in M.items()}
    mid = (M["bc"] + M["ac"]) / 2; op = (M["bo"][:, 0] + M["ao"][:, 0]) / 2; move = np.abs(mid / op[:, None] - 1)
    rows = []
    for i in range(15, len(days)):
        if (days[i] - days[i - 1]).days > 4: continue
        sig = move[i - 14:i].mean(0); prev = mid[i - 1, 389]; hi_ref, lo_ref = max(op[i], prev), min(op[i], prev)
        pos, entry, pnl, ntr = 0, 0.0, 0.0, 0
        for mk in MARKS:
            kd = mk - 1; px = mid[i, kd]; ub, lb = hi_ref * (1 + sig[kd]), lo_ref * (1 - sig[kd]); vw = mid[i, :kd + 1].mean()
            if variant == "NA2": ex_l, ex_s = px < ub, px > lb
            else: ex_l, ex_s = px < max(ub, vw), px > min(lb, vw)
            if pos > 0 and ex_l: pnl += (M["bo"][i, mk] / entry - 1) - SLIP; pos = 0
            elif pos < 0 and ex_s: pnl += (entry / M["ao"][i, mk] - 1) - SLIP; pos = 0
            if pos == 0 and px > ub: pos, entry, ntr = 1, M["ao"][i, mk] * (1 + SLIP), ntr + 1
            elif pos == 0 and px < lb: pos, entry, ntr = -1, M["bo"][i, mk] * (1 - SLIP), ntr + 1
        if pos > 0: pnl += (M["bc"][i, 389] / entry - 1) - SLIP
        elif pos < 0: pnl += (entry / M["ac"][i, 389] - 1) - SLIP
        r = np.log(mid[i - 14:i, 389] / mid[i - 15:i - 1, 389]); vt = min(4.0, 0.02 / max(r.std(ddof=1), 1e-6))
        rows.append(dict(date=days[i], bp=pnl * 1e4, trades=ntr, vt=vt))
    return pd.DataFrame(rows).set_index("date")


def variant_series(v: str, last: str) -> pd.DataFrame:
    mk = ("NSDQ",) if v == "NA3" else ("SP", "NSDQ", "DOW")
    parts = [run(m, "NA2" if v == "NA2" else "NA1", last) for m in mk]
    idx = parts[0].index
    for p in parts[1:]: idx = idx.intersection(p.index)
    return pd.DataFrame({"bp": sum(p.loc[idx, "bp"] for p in parts) / len(parts), "trades": sum(p.loc[idx, "trades"] for p in parts),
                         "bp_vt": sum(p.loc[idx, "bp"] * p.loc[idx, "vt"] for p in parts) / len(parts)})


def st(x):
    n = len(x); return dict(n=n, mean=float(x.mean()), t=float(x.mean() / (x.std(ddof=1) / np.sqrt(n))), win=float((x > 0).mean()), act=int((x != 0).sum()))


def sl(X, p): return X[(X.index >= PER[p][0]) & (X.index <= PER[p][1])]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dev", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    if a.dev:
        res = {}
        for v in ("NA1", "NA2", "NA3"):
            X = variant_series(v, "2025-12-31")
            for p in ("DEV", "VAL"):
                s = st(sl(X, p).bp); print(f"{v} {p}: days {s['n']} (active {s['act']}) | mean {s['mean']:+.2f} bp/day | win {100*s['win']:.1f}% | daily t {s['t']:+.2f} | trades {int(sl(X, p).trades.sum())}"
                                         + (f" | vol-target diag mean {sl(X, p).bp_vt.mean():+.2f} bp t {st(sl(X, p).bp_vt)['t']:+.2f}" if v == "NA1" else ""))
                with open(LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},noise_area,{v},{p},{s['n']},{s['act']},,{s['mean']:.4f},,{s['t']:.2f},{s['win']:.3f},\n")
            d, va = st(sl(X, "DEV").bp), st(sl(X, "VAL").bp); res[v] = bool(d["t"] >= 2.4 and d["mean"] > 0 and va["mean"] > 0 and d["act"] >= 300)
            Y = X[X.index <= "2025-12-31"]; print(f"   {v} acceptance: {res[v]} | by year bp/day:", Y.bp.groupby(Y.index.year).mean().round(2).to_dict())
        STATE.write_text(json.dumps(res))
    if a.holdout:
        res = json.loads(STATE.read_text()); live = [k for k, v in res.items() if v]
        if not live: print("No variant passed: the 2026 hold-out stays CLOSED.")
        for v in live:
            X = variant_series(v, "2026-09-30"); s = st(sl(X, "HOLD").bp); print(f"{v} HOLD 2026: days {s['n']} mean {s['mean']:+.2f} bp/day t {s['t']:+.2f} win {100*s['win']:.1f}%")
            with open(LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},noise_area,{v},HOLD,{s['n']},{s['act']},,{s['mean']:.4f},,{s['t']:.2f},{s['win']:.3f},\n")
