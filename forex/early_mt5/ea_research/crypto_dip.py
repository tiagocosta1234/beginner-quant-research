"""Family CD: dip reversal in MT5 broker's crypto CFDs, exactly as registered in PREREG_CRYPTO_DIP.md.   python -m mt5broker.ea_research.crypto_dip --dev | --holdout"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[0] / "data_mt5"
STATE = HERE / "CRYPTO_DIP_STATE.json"
LEDGER = HERE / "LEDGER.csv"
COINS = ("BTCUSD", "ETHUSD", "LTCUSD", "XRPUSD", "ADAUSD", "BCHUSD", "BNBUSD", "SOLUSD")
PER = {"DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
SLIP = 1e-5


def coin_trades(m, last):
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "bl", "bc", "ao", "ah"]).sort_values("t").drop_duplicates("t")
    d = d[(d.bo > 0) & (d.ao >= d.bo)].reset_index(drop=True); t = d.t.to_numpy()
    dec = d[d.t % 86400 == 12 * 3600 - 60].set_index("t").bc                     # the 11:59 bar closes at 12:00
    dec = dec[dec.index <= pd.Timestamp(last).value // 10**9 + 86400]
    r = dec.pct_change(); sd = r.rolling(60, min_periods=40).std(); z3 = np.log(dec / dec.shift(3)) / (sd * np.sqrt(3))
    bo, ao, bl, ah = d.bo.to_numpy(), d.ao.to_numpy(), d.bl.to_numpy(), d.ah.to_numpy(); out = []
    for k in range(len(dec)):
        z = z3.iat[k]
        if not np.isfinite(z) or abs(z) < 2.0: continue
        side = 1 if z <= -2.0 else -1; T0 = int(dec.index[k]) + 60; T1 = T0 + 86400
        i0 = int(np.searchsorted(t, T0)); i1 = int(np.searchsorted(t, T1))
        if i0 >= len(t) or i1 >= len(t) or t[i0] > T0 + 300 or t[i1] > T1 + 300: continue
        e = ao[i0] * (1 + SLIP) if side > 0 else bo[i0] * (1 - SLIP); stop = e * (1 - side * 3 * sd.iat[k])
        hit = np.nonzero(bl[i0:i1] <= stop)[0] if side > 0 else np.nonzero(ah[i0:i1] >= stop)[0]
        if len(hit): j = i0 + hit[0]; px = min(stop, bo[j]) * (1 - SLIP) if side > 0 else max(stop, ao[j]) * (1 + SLIP)
        else: px = bo[i1] * (1 - SLIP) if side > 0 else ao[i1] * (1 + SLIP)
        bp = ((px - e) / e if side > 0 else (e - px) / e) * 1e4
        out.append(dict(date=pd.Timestamp(T0 // 86400 * 86400, unit="s"), mkt=m, side=side, bp=bp, stopped=bool(len(hit))))
    return pd.DataFrame(out)


def all_trades(last): return pd.concat([coin_trades(m, last) for m in COINS], ignore_index=True)


def variant(T, v):
    X = T[T.side > 0] if v in ("CD1", "CD2") else T[T.side < 0]
    if v == "CD2": X = X[X.mkt.isin(["BTCUSD", "ETHUSD"])]
    X = X.set_index("date").bp; return X, X.groupby(level=0).mean()


def sl(x, p): return x[(x.index >= PER[p][0]) & (x.index <= PER[p][1])]


def st(x):
    n = len(x); return dict(n=n, mean=float(x.mean()), t=float(x.mean() / (x.std(ddof=1) / np.sqrt(n))) if n > 2 else np.nan, win=float((x > 0).mean()) if n else np.nan)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dev", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    if a.dev:
        T = all_trades("2025-12-31"); res = {}
        for v in ("CD1", "CD2", "CD3"):
            X, D = variant(T, v)
            for p in ("DEV", "VAL"):
                s, tr = st(sl(D, p)), st(sl(X, p)); print(f"{v} {p}: trades {tr['n']} on {s['n']} days | per trade {tr['mean']:+.1f} bp win {100*tr['win']:.1f}% | daily mean {s['mean']:+.1f} bp t {s['t']:+.2f}")
                with open(LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},crypto_dip,{v},{p},{s['n']},{tr['n']},,{tr['mean']:.4f},,{s['t']:.2f},{tr['win']:.3f},\n")
            d, va = st(sl(D, "DEV")), st(sl(D, "VAL")); res[v] = bool(d["t"] >= 2.4 and d["mean"] > 0 and va["mean"] > 0 and d["n"] >= 60)
            y = X[X.index <= "2025-12-31"]; print(f"   {v} acceptance: {res[v]} | per trade by year:", y.groupby(y.index.year).mean().round(1).to_dict())
        STATE.write_text(json.dumps(res))
    if a.holdout:
        res = json.loads(STATE.read_text()); live = [k for k, v in res.items() if v]
        if not live: print("No variant passed: the 2026 hold-out stays CLOSED.")
        else:
            T = all_trades("2026-09-30")
            for v in live:
                X, D = variant(T, v); s = st(sl(D, "HOLD")); print(f"{v} HOLD 2026: days {s['n']} mean {s['mean']:+.1f} bp t {s['t']:+.2f} | trades {len(sl(X, 'HOLD'))}")
                with open(LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},crypto_dip,{v},HOLD,{s['n']},{len(sl(X, 'HOLD'))},,{s['mean']:.4f},,{s['t']:.2f},{s['win']:.3f},\n")
