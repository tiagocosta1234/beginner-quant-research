"""Family CX: weekly cross-sectional crypto momentum / reversal, exactly as registered in PREREG_CRYPTO_XS.md.   python -m mt5broker.ea_research.crypto_xs --dev | --holdout"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[0] / "data_mt5"
STATE = HERE / "CRYPTO_XS_STATE.json"
LEDGER = HERE / "LEDGER.csv"
COINS = ("BTCUSD", "ETHUSD", "LTCUSD", "XRPUSD", "ADAUSD", "BCHUSD", "BNBUSD", "SOLUSD")
PER = {"DEV": ("2022-01-03", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
SLIP = 1e-5


def noon(m):
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "ao"])
    d = d[(d.bo > 0) & (d.ao >= d.bo) & (d.t % 86400 == 12 * 3600)]
    d.index = pd.to_datetime(d.t // 86400 * 86400, unit="s"); return d[["bo", "ao"]]


def weekly(last):
    Q = {m: noon(m) for m in COINS}; mons = pd.date_range("2021-12-06", last, freq="W-MON"); rows = []
    mid = pd.DataFrame({m: (q.bo + q.ao) / 2 for m, q in Q.items()})
    for M in mons:
        N = M + pd.Timedelta(days=7)
        if N > pd.Timestamp(last) + pd.Timedelta(days=7): break
        ok = [m for m in COINS if M in Q[m].index and N in Q[m].index]
        r1 = {m: mid.at[M, m] / mid.at[M - pd.Timedelta(days=7), m] - 1 for m in ok if (M - pd.Timedelta(days=7)) in mid.index and np.isfinite(mid.at[M - pd.Timedelta(days=7), m])}
        r4 = {m: mid.at[M, m] / mid.at[M - pd.Timedelta(days=28), m] - 1 for m in ok if (M - pd.Timedelta(days=28)) in mid.index and np.isfinite(mid.at[M - pd.Timedelta(days=28), m])}
        lg = {m: ((Q[m].at[N, "bo"] * (1 - SLIP)) / (Q[m].at[M, "ao"] * (1 + SLIP)) - 1) * 1e4 for m in ok}
        sh = {m: (1 - (Q[m].at[N, "ao"] * (1 + SLIP)) / (Q[m].at[M, "bo"] * (1 - SLIP))) * 1e4 for m in ok}   # FIX: short P&L = 1 - exit/entry
        row = {"week": M}
        for nm, sig, mom in (("CX1", r1, True), ("CX2", r1, False), ("CX3", r4, True)):
            if len(sig) < 6: continue
            rk = sorted(sig, key=sig.get); top, bot = rk[-2:], rk[:2]
            L, S = (top, bot) if mom else (bot, top)
            row[nm] = np.mean([lg[m] for m in L] + [sh[m] for m in S])
            row[nm + "_gross"] = np.mean([(mid.at[N, m] / mid.at[M, m] - 1) * 1e4 for m in L] + [(1 - mid.at[N, m] / mid.at[M, m]) * 1e4 for m in S])
        rows.append(row)
    return pd.DataFrame(rows).set_index("week")


def sl(x, p): return x[(x.index >= PER[p][0]) & (x.index <= PER[p][1])]


def st(x):
    x = x.dropna(); n = len(x); return dict(n=n, mean=float(x.mean()), t=float(x.mean() / (x.std(ddof=1) / np.sqrt(n))), win=float((x > 0).mean()))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dev", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    if a.dev:
        W = weekly("2025-12-31"); res = {}
        for v in ("CX1", "CX2", "CX3"):
            for p in ("DEV", "VAL"):
                s, g = st(sl(W[v], p)), st(sl(W[v + "_gross"], p)); print(f"{v} {p}: weeks {s['n']} | net {s['mean']:+.1f} bp/week (gross {g['mean']:+.1f}) | win {100*s['win']:.0f}% | t {s['t']:+.2f} (gross t {g['t']:+.2f})")
                with open(LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},crypto_xs,{v},{p},{s['n']},{s['n']},,{s['mean']:.4f},,{s['t']:.2f},{s['win']:.3f},gross {g['mean']:.1f}\n")
            d, va = st(sl(W[v], "DEV")), st(sl(W[v], "VAL")); res[v] = bool(d["t"] >= 2.4 and d["mean"] > 0 and va["mean"] > 0)
            y = W[v][W.index <= "2025-12-31"]; print(f"   {v} acceptance: {res[v]} | net by year:", y.groupby(y.index.year).mean().round(1).to_dict())
        STATE.write_text(json.dumps(res))
    if a.holdout:
        res = json.loads(STATE.read_text()); live = [k for k, v in res.items() if v]
        if not live: print("No variant passed: the 2026 hold-out stays CLOSED.")
        else:
            W = weekly("2026-09-30")
            for v in live: s = st(sl(W[v], "HOLD")); print(f"{v} HOLD 2026: weeks {s['n']} mean {s['mean']:+.1f} bp t {s['t']:+.2f}")
