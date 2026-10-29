"""Iteration 29 (pre-registered in lab/PREREG.md): swing rule families on the FX pairs with complete tick-built data.   python -m forex.intraday_lab.iter29_fx_swing"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"
OUTDIR = Path("data/scratch/lab")
PAIRS = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "CADCHF", "CADJPY")
COMM, SWAP = 0.3e-4, 0.7e-4
STOP_ATR, TGT_ATR, MAXD = 2.0, 3.0, 10


def daily(sym):
    m = pd.read_parquet(DATA / f"{sym}_M1_ticks_full.parquet", columns=["time", "open", "high", "low", "close", "ask_open", "ask_high", "ask_low", "ask_close"])
    d = pd.to_datetime(m.time.values, unit="s").normalize(); g = m.groupby(d)
    a = pd.DataFrame({"bo": g.open.first(), "bh": g.high.max(), "bl": g.low.min(), "bc": g.close.last(), "ao": g.ask_open.first(), "ah": g.ask_high.max(), "al": g.ask_low.min(), "ac": g.ask_close.last()})
    a = a[a.index.dayofweek < 5]
    return a[(a.bh - a.bl) > 0]


def rsi(c, n=3):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def signals(a):
    c = (a.bc + a.ac) / 2; hi, lo = a.bh, a.bl; out = {}
    for N in (20, 55):
        s = np.zeros(len(a)); s[(c > hi.shift(1).rolling(N).max()).values] = 1; s[(c < lo.shift(1).rolling(N).min()).values] = -1; out[f"DON{N}"] = s
    r3 = rsi(c); sma = c.rolling(100).mean(); s = np.zeros(len(a)); s[((c > sma) & (r3 < 15)).values] = 1; s[((c < sma) & (r3 > 85)).values] = -1; out["PB"] = s
    z = (c - c.rolling(20).mean()) / c.rolling(20).std(); s = np.zeros(len(a)); s[(z < -2).values] = 1; s[(z > 2).values] = -1; out["MR"] = s
    return out


def nights(d0, d1):
    n = 0; d = d0
    while d < d1:
        n += 3 if d.dayofweek == 2 else 1; d += pd.Timedelta(days=1)
    return n


def trades(sym, a, sig):
    tr = (np.maximum(a.bh - a.bl, np.maximum((a.bh - a.bc.shift(1)).abs(), (a.bl - a.bc.shift(1)).abs()))).rolling(14).mean().shift(1).values
    idx = a.index; bo, bh, bl, ao, ah, al = (a[k].values for k in ("bo", "bh", "bl", "ao", "ah", "al")); bc, ac = a.bc.values, a.ac.values; n = len(a); out = []; t = 0
    while t < n - 2:
        s = sig[t]
        if s == 0 or np.isnan(tr[t + 1]):
            t += 1; continue
        e = t + 1; atr = tr[e]; sd = STOP_ATR * atr; side = int(s)
        px = ao[e] if side > 0 else bo[e]; stop = px - side * sd; tgt = px + side * TGT_ATR * atr; exit_px = None; j = e
        while j < min(n, e + MAXD):
            hit_s, hit_t = (bl[j] <= stop, bh[j] >= tgt) if side > 0 else (ah[j] >= stop, al[j] <= tgt)
            if hit_s:
                exit_px = stop; break
            if hit_t:
                exit_px = tgt; break
            j += 1
        if exit_px is None:
            j = min(n, e + MAXD) - 1; exit_px = bc[j] if side > 0 else ac[j]
        gross = (exit_px - px) * side; cost = COMM * px * 2 + SWAP * px * nights(idx[e], idx[j])
        out.append((sym, idx[e], side, (gross - cost) / sd, gross / sd, cost / sd))
        t = j + 1
    return out


def tstat(x):
    x = np.asarray(x)
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 30 and x.std(ddof=1) > 0 else np.nan


def main():
    rows = {k: [] for k in ("DON20", "DON55", "PB", "MR")}
    for sym in PAIRS:
        a = daily(sym)
        for fam, s in signals(a).items():
            rows[fam] += trades(sym, a, s)
    hits = []
    for fam, r in rows.items():
        T = pd.DataFrame(r, columns=["pair", "d", "side", "R", "gross_R", "cost_R"]); T["y"] = T.d.dt.year
        T["ph"] = np.where(T.d < "2024-01-01", "dev", np.where(T.d < "2025-01-01", "val", "hold")); T.to_csv(OUTDIR / f"iter29_{fam}.csv", index=False)
        dv, vl = T[T.ph == "dev"], T[T.ph == "val"]
        pos_dev = int((dv.groupby("pair").R.mean() > 0).sum()); pos_val = int((vl.groupby("pair").R.mean() > 0).sum())
        yrs = T[T.y >= 2022].groupby("y").R.mean(); ypos = int((yrs > 0).sum())
        r_ = dict(family=fam, n=len(T), n_dev=len(dv), n_val=len(vl), mean_dev=dv.R.mean(), t_dev=tstat(dv.R), mean_val=vl.R.mean(), t_val=tstat(vl.R), pairs_pos_dev=pos_dev, pairs_pos_val=pos_val,
                  gross_dev=dv.gross_R.mean(), cost_dev=dv.cost_R.mean(), years_pos=ypos, long_dev=dv[dv.side > 0].R.mean(), short_dev=dv[dv.side < 0].R.mean(), by_year={int(k): round(float(v), 3) for k, v in yrs.items()})
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r_.items()}, flush=True)
        if r_["mean_dev"] > 0 and r_["t_dev"] >= 2.5 and r_["mean_val"] > 0 and r_["t_val"] >= 2.0 and pos_dev >= 8 and pos_val >= 8 and ypos >= 4:
            hits.append(r_)
    print(f"PRE-REGISTERED HITS (k = 4): {len(hits)}")
    for h in hits:
        T = pd.read_csv(OUTDIR / f"iter29_{h['family']}.csv"); x = T[T.ph == "hold"]
        print("HOLD (printed because DEV and VAL passed):", h["family"], f"n {len(x)} mean R {x.R.mean():.3f} t {tstat(x.R):.2f}")


if __name__ == "__main__":
    main()
