"""Family W: crypto on weekends, exactly as registered in PREREG_CRYPTO_WEEKEND.md.
   python -m forex.ea_research.crypto_weekend --dev | --holdout"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

from forex.ea_research import event_macro as V

HERE = Path(__file__).resolve().parent
STATE = HERE / "CRYPTO_WEEKEND_STATE.json"
COINS = ("BTCUSD", "ETHUSD")
PER = {"DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}


def ts(day, hh, mm): return int((pd.Timestamp(f"{day} {hh:02d}:{mm:02d}") - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1))


def q(m, t, w=300):
    d = V.mkt(m); i = d.index.searchsorted(t)
    if i >= len(d) or d.index[i] > t + w: return None
    r = d.iloc[i]; return float(r.bo), float(r.ao)


def trade(m, ti, tx, side):
    a, b = q(m, ti), q(m, tx)
    if a is None or b is None: return None
    return ((b[0] / a[1] - 1) if side > 0 else (a[0] / b[1] - 1)) * 1e4 - 2 * V.SLIP * 1e4


def mid(m, t):
    x = q(m, t); return None if x is None else (x[0] + x[1]) / 2


def daily_sd(m):
    d = V.mkt(m); s = pd.Series(((d.bo + d.ao) / 2).to_numpy(), index=pd.to_datetime(d.index, unit="s")); c = s.resample("1D").last().dropna(); return np.log(c).diff().rolling(20).std()


def blocks_sd(m):
    d = V.mkt(m); s = pd.Series(((d.bo + d.ao) / 2).to_numpy(), index=pd.to_datetime(d.index, unit="s")); c = s.resample("4h", offset="1h5min").last().dropna(); r = np.log(c).diff()
    return r.rolling(180, min_periods=90).std().shift(1)          # previous 30 days of 4-hour blocks


def run_all(last):
    sats = pd.date_range("2022-01-01", last, freq="W-SAT"); W1, W2, W3, W3d = [], [], [], []
    sdd = {m: daily_sd(m) for m in COINS}; sdb = {m: blocks_sd(m) for m in COINS}
    for S in sats:
        sat, sun = str(S.date()), str((S + pd.Timedelta(days=1)).date()); ti, tx = ts(sat, 1, 5), ts(sun, 22, 50)
        v = [trade(m, ti, tx, 1) for m in COINS]
        if None not in v: W1.append(dict(date=S, net=np.mean(v)))
        legs = []
        for m in COINS:
            a, b = mid(m, ti), mid(m, ts(sun, 12, 0)); sd = sdd[m].asof(pd.Timestamp(sat)) if len(sdd[m]) else np.nan
            if a is None or b is None or not np.isfinite(sd): continue
            r = np.log(b / a)
            if abs(r) > 1.0 * sd:
                x = trade(m, ts(sun, 12, 2), tx, -np.sign(r))
                if x is not None: legs.append(x)
        if legs: W2.append(dict(date=S, net=np.mean(legs)))
    for m in COINS:
        d = V.mkt(m); s = pd.Series(((d.bo + d.ao) / 2).to_numpy(), index=pd.to_datetime(d.index, unit="s")); c = s.resample("4h", offset="1h5min").last(); r = np.log(c).diff(); sd = sdb[m].reindex(c.index)
        for k in range(1, len(c) - 2):
            B0 = c.index[k]                                                       # block k = [B0, B0+4h); its return is known at its END
            if B0 < pd.Timestamp("2022-01-01") or B0 > pd.Timestamp(last) or not np.isfinite(r.iat[k]) or not np.isfinite(sd.iat[k]) or abs(r.iat[k]) <= 2 * sd.iat[k]: continue
            T0 = c.index[k + 1]; end = c.index[k + 2]                             # FIX 2026-10-10 (before any valid result): enter at the end of the signal block, hold the NEXT block
            dow = T0.dayofweek
            if dow == 6 and (end.dayofweek != 6 or end.hour >= 23): end = T0.normalize() + pd.Timedelta(hours=22, minutes=50)
            if (end - T0) <= pd.Timedelta(0) or T0.hour in (23, 0): continue
            ti = int((T0 - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)) + 60; tx = int((end - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1))
            x = trade(m, ti, tx, -np.sign(r.iat[k]))
            if x is None: continue
            (W3 if dow >= 5 else W3d).append(dict(date=T0.normalize(), mkt=m, net=x))
    return {k: pd.DataFrame(v) for k, v in (("W1", W1), ("W2", W2), ("W3", W3), ("W3-weekdays", W3d))}


def st(X, p):
    a, b = PER[p]; x = X[(X.date >= a) & (X.date <= b)].net; n = len(x)
    return dict(n=n, mean=float(x.mean()) if n else np.nan, t=float(x.mean() / (x.std(ddof=1) / np.sqrt(n))) if n > 2 else np.nan, win=float((x > 0).mean()) if n else np.nan, worst=float(x.min()) if n else np.nan)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dev", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    if a.dev:
        R = run_all("2025-12-31"); res = {}
        for k, X in R.items():
            for p in ("DEV", "VAL"):
                s = st(X, p); print(f"{k:12s} {p}: trades {s['n']:4d} | win {100*s['win']:4.1f}% | mean {s['mean']:+7.2f} bp | t {s['t']:+5.2f} | worst {s['worst']:+7.1f}")
                if not k.endswith("weekdays"):
                    with open(V.LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},crypto_weekend,{k},{p},,{s['n']},,{s['mean']:.4f},,{s['t']:.2f},{s['win']:.3f},\n")
            if not k.endswith("weekdays"):
                d, v = st(X, "DEV"), st(X, "VAL"); res[k] = bool(d["mean"] > 0 and d["t"] >= 2.4 and d["n"] >= 100 and v["mean"] > 0); print(f"   {k} acceptance 1-2: {res[k]}")
        STATE.write_text(json.dumps(res))
    if a.holdout:
        res = json.loads(STATE.read_text()); live = [k for k, v in res.items() if v]
        if not live: print("No trial passed acceptance 1-2: the 2026 hold-out stays CLOSED.")
        else:
            R = run_all("2026-09-30")
            for k in live: s = st(R[k], "HOLD"); print(f"{k} HOLD: trades {s['n']} mean {s['mean']:+.2f} bp t {s['t']:+.2f}")
