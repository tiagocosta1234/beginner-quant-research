"""Family GR: gold range system at H1 / daily horizons, exactly as registered in PREREG_GOLD_RANGE.md.
   python -m mt5broker.ea_research.gold_range --dry | --dev | --holdout"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[0] / "data_mt5"
STATE = HERE / "GOLD_RANGE_STATE.json"
LEDGER = HERE / "LEDGER.csv"
PER = {"DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
SLIP, RISK = 0.10, 500.0


def m1():
    d = pd.read_parquet(DATA / "XAUUSD_M1_rates.parquet").sort_values("t").drop_duplicates("t")
    return d[(d.bo > 0) & (d.ao >= d.bo)].reset_index(drop=True)


def bars(d, kind):
    """Decision bars: close (bid), high, low between decisions, and the decision time T (= start of the next minute)."""
    if kind == "D":
        dec = d[(d.t % 86400) == 22 * 3600]; dec = dec[pd.to_datetime(dec.t, unit="s").dt.dayofweek < 5]
        T = dec.t.to_numpy() + 60; c = dec.bc.to_numpy()
        seg = np.searchsorted(d.t.to_numpy(), T); hi = np.maximum.reduceat(d.bh.to_numpy(), seg[:-1]) if len(seg) > 1 else np.array([])
        lo = np.minimum.reduceat(d.bl.to_numpy(), seg[:-1]); hi = np.r_[np.nan, hi]; lo = np.r_[np.nan, lo]
        hour_ok = np.ones(len(T), bool)
    else:
        g = d.groupby(d.t // 3600); B = pd.DataFrame({"c": g.bc.last(), "h": g.bh.max(), "l": g.bl.min(), "n": g.size()})
        B = B[B.n >= 20]; T = (B.index.to_numpy() + 1) * 3600; c, hi, lo = B.c.to_numpy(), B.h.to_numpy(), B.l.to_numpy()
        hr = (T // 3600) % 24; hour_ok = (hr >= 1) & (hr <= 22)
    prev = np.r_[np.nan, c[:-1]]; tr = np.nanmax(np.vstack([hi - lo, np.abs(hi - prev), np.abs(lo - prev)]), axis=0)
    return pd.DataFrame({"T": T, "c": c, "tr": tr, "ok": hour_ok})


def signals(B, v):
    c = pd.Series(B.c)
    if v in ("GR1", "GR2"): n_er, n_z, er_max, z_in, atr_n, k_stop, max_hold = 20, 20, 0.30, 1.5, 20, 2.5, 5
    else: n_er, n_z, er_max, z_in, atr_n, k_stop, max_hold = 100, 50, 0.25, 2.0, 50, 3.0, 24
    lr = np.log(c).diff(); er = (np.log(c / c.shift(n_er))).abs() / lr.abs().rolling(n_er).sum()
    sma = c.rolling(n_z).mean(); z = (c - sma) / c.rolling(n_z).std(); atr = pd.Series(B.tr).rolling(atr_n).mean()
    rng = (er < er_max) if v != "GR2" else pd.Series(True, index=c.index)
    side = np.where(rng & (z <= -z_in), 1, np.where(rng & (z >= z_in), -1, 0))
    return side, z.to_numpy(), sma.to_numpy(), atr.to_numpy(), k_stop, max_hold


def run(d, v, last):
    B = bars(d, "D" if v in ("GR1", "GR2") else "H"); B = B[B["T"] <= pd.Timestamp(last).value // 10**9 + 86400].reset_index(drop=True)
    side, z, sma, atr, k_stop, max_hold = signals(B, v)
    t = d.t.to_numpy(); bo, ao, bl, ah = d.bo.to_numpy(), d.ao.to_numpy(), d.bl.to_numpy(), d.ah.to_numpy(); T = B["T"].to_numpy(); c = B.c.to_numpy()
    out = []; k = 0; n = len(B)
    while k < n - 1:
        s = side[k]
        if s == 0 or not B.ok.iat[k] or not np.isfinite(atr[k]): k += 1; continue
        i = int(np.searchsorted(t, T[k]))
        if i >= len(t) or t[i] > T[k] + 300: k += 1; continue
        e = (ao[i] + SLIP) if s > 0 else (bo[i] - SLIP); stop = e - s * k_stop * atr[k]; q = RISK / (k_stop * atr[k])
        j_end, px, why = None, None, None; kk = k
        while kk < n - 1 and j_end is None:
            kk += 1; i2 = int(np.searchsorted(t, T[kk]))
            seg_hit = np.nonzero((bl[i:i2] <= stop) if s > 0 else (ah[i:i2] >= stop))[0]
            if len(seg_hit):
                j = i + seg_hit[0]; px = (min(stop, bo[j]) - SLIP) if s > 0 else (max(stop, ao[j]) + SLIP); j_end, why = j, "stop"; break
            i = i2
            cross = (c[kk] >= sma[kk]) if s > 0 else (c[kk] <= sma[kk])
            if v == "GR3": cross = (z[kk] >= 0) if s > 0 else (z[kk] <= 0)
            if cross or kk - k >= max_hold:
                if i2 >= len(t): break
                px = (bo[i2] - SLIP) if s > 0 else (ao[i2] + SLIP); j_end, why = i2, "exit"
        if j_end is None: break
        pl = (px - e) * s * q
        out.append(dict(date=pd.Timestamp(int(t[j_end]) // 86400 * 86400, unit="s"), side=s, R=pl / RISK, usd=pl, why=why, entry_t=int(T[k])))
        k = kk + (0 if why == "exit" else 0)
        while k < n and T[k] <= t[j_end]: k += 1
    return pd.DataFrame(out)


def daily(X):
    s = X.groupby("date").usd.sum(); idx = pd.bdate_range("2022-01-03", s.index.max()); return s.reindex(idx).fillna(0.0)


def sl(x, p): return x[(x.index >= PER[p][0]) & (x.index <= PER[p][1])]


def st(x):
    n = len(x); return dict(n=n, mean=float(x.mean()), t=float(x.mean() / (x.std(ddof=1) / np.sqrt(n))) if n > 2 and x.std() > 0 else np.nan)


def pair_daily():
    from mt5broker.ea_research import clean_boot_lib as L
    S = L.series("FT", 1.2); return pd.Series(S["V"], index=pd.to_datetime(S["days"] * 86400, unit="s"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); [ap.add_argument(f"--{k}", action="store_true") for k in ("dry", "dev", "holdout")]; a = ap.parse_args()
    d = m1()
    if a.dry:
        for v in ("GR1", "GR3"):
            X = run(d, v, "2022-06-30"); print(v, len(X), "trades to 2022-06 |", X.head(5).to_string(index=False)); print("   exits:", X.why.value_counts().to_dict(), "| mean R", round(X.R.mean(), 3))
    if a.dev:
        P = pair_daily(); res = {}
        for v in ("GR1", "GR2", "GR3"):
            X = run(d, v, "2025-12-31"); X = X[X.date >= "2022-01-01"]; D = daily(X)
            for p in ("DEV", "VAL"):
                x = sl(X.set_index("date"), p); s = st(sl(D, p)); pf = x.usd[x.usd > 0].sum() / -x.usd[x.usd < 0].sum() if (x.usd < 0).any() else np.nan
                print(f"{v} {p}: trades {len(x)} | mean {x.R.mean():+.3f} R | win {100*(x.R > 0).mean():.1f}% | PF {pf:.2f} | daily t {s['t']:+.2f} | USD {x.usd.sum():+,.0f}")
                with open(LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},gold_range,{v},{p},{s['n']},{len(x)},{x.usd.sum():.1f},{x.R.mean():.4f},{pf:.3f},{s['t']:.2f},{(x.R > 0).mean():.3f},\n")
            dv = sl(D, "DEV"); y23 = D[(D.index >= "2022-01-01") & (D.index <= "2023-12-31")].sum(); cor = D.corr(P.reindex(D.index).fillna(0.0))
            sd, sv = st(dv), st(sl(D, "VAL")); nd = len(sl(X.set_index("date"), "DEV"))
            res[v] = bool(sd["t"] >= 2.4 and sd["mean"] > 0 and y23 > 0 and sv["mean"] > 0 and nd >= 60 and cor <= 0.3)
            print(f"   {v} acceptance: {res[v]} | 2022-23 USD {y23:+,.0f} | corr with pair {cor:+.2f} | USD by year:", D.groupby(D.index.year).sum().round(0).to_dict())
        STATE.write_text(json.dumps(res))
    if a.holdout:
        res = json.loads(STATE.read_text()); live = [k for k, v in res.items() if v]
        if not live: print("No variant passed: the 2026 hold-out stays CLOSED.")
        for v in live:
            X = run(d, v, "2026-09-30"); D = daily(X[X.date >= "2022-01-01"]); x = sl(X.set_index("date"), "HOLD"); s = st(sl(D, "HOLD"))
            print(f"{v} HOLD 2026: trades {len(x)} mean {x.R.mean():+.3f} R | daily t {s['t']:+.2f} | USD {x.usd.sum():+,.0f}")
            with open(LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},gold_range,{v},HOLD,{s['n']},{len(x)},{x.usd.sum():.1f},{x.R.mean():.4f},,{s['t']:.2f},{(x.R > 0).mean():.3f},\n")
