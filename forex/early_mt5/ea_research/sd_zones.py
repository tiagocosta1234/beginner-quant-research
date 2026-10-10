"""Family Z: Trade-with-Pat supply/demand zones, as registered in PREREG_SD_ZONES.md.
   python -m mt5broker.ea_research.sd_zones --dev | --holdout"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.ea_research import stacked_va as G

HERE = Path(__file__).resolve().parent
STATE = HERE / "SD_ZONES_STATE.json"
CACHE = Path("D:/finance/tmp/sd_zones_trades.parquet")
MKTS = G.FX + G.IDX + ["XAUUSD"]
PER = G.PER


def run_market(m):
    d = G.load(m); t = d.t.to_numpy(); ah, al, ao, bh, bl, bo, ac, bc = (d[k].to_numpy() for k in ("ah", "al", "ao", "bh", "bl", "bo", "ac", "bc"))
    H = d.groupby(d.t // 3600).agg(o=("mc", "first"), h=("mc", "max"), l=("mc", "min"), c=("mc", "last")).reset_index(names="hb"); H["start"] = H.hb * 3600
    o, h, l, c = (H[k].to_numpy() for k in ("o", "h", "l", "c")); n = len(H)
    tr = np.maximum(h - l, np.maximum(abs(h - np.r_[np.nan, c[:-1]]), abs(l - np.r_[np.nan, c[:-1]]))); atr = pd.Series(tr).rolling(14).mean().to_numpy()
    out = []; busy_until = 0
    for k in range(23, n - 2):
        for side in (1, -1):
            imp = [(c[i] - o[i]) * side > 0 for i in (k - 2, k - 1, k)]
            if not all(imp) or not np.isfinite(atr[k]): continue
            if sum(abs(c[i] - o[i]) for i in (k - 2, k - 1, k)) < 1.5 * atr[k]: continue
            fvg = (l[k] > h[k - 2] or l[k - 1] > h[k - 3]) if side > 0 else (h[k] < l[k - 2] or h[k - 1] < l[k - 3])
            bos = h[k] > h[k - 22:k - 2].max() if side > 0 else l[k] < l[k - 22:k - 2].min()
            if not (fvg and bos): continue
            zl, zh = l[k - 3], h[k - 3]; tgt = max(h[k - 2:k + 1]) if side > 0 else min(l[k - 2:k + 1])
            for j in range(k + 1, min(n, k + 121)):
                touch = l[j] <= zh if side > 0 else h[j] >= zl
                if not touch: continue
                conf = (c[j] > zh if side > 0 else c[j] < zl) and (h[j] - l[j]) < 2 * atr[j]
                if conf and H.start.iat[j] >= busy_until:
                    tsig = int(H.start.iat[j]) + 3600 + 120; i0 = int(np.searchsorted(t, tsig)); ts_ = pd.Timestamp(tsig, unit="s")
                    if i0 < len(t) and t[i0] <= tsig + 300 and ts_.hour not in (23, 0) and not (ts_.dayofweek == 4 and ts_.hour >= 21) and ts_.dayofweek < 5:
                        r = sim(side, i0, t, ah, al, ao, bh, bl, bo, ac, bc, zl, zh, tgt)
                        if r is not None:
                            r.update(mkt=m, date=ts_.normalize()); out.append(r); busy_until = r.pop("t_exit")
                break
    return out


def sim(side, i0, t, ah, al, ao, bh, bl, bo, ac, bc, zl, zh, tgt):
    e = ao[i0] if side > 0 else bo[i0]; S = zl * (1 - 2e-4) if side > 0 else zh * (1 + 2e-4); dd = (e - S) * side
    if dd <= 0 or (tgt - e) * side < dd: return None
    ts0 = pd.Timestamp(t[i0], unit="s"); fri = (ts0.normalize() + pd.Timedelta(days=(4 - ts0.dayofweek) % 7, hours=21)).value // 10**9
    end = min(t[i0] + 48 * 3600, fri); j1 = int(np.searchsorted(t, end)); j1 = max(j1, i0 + 1)
    # Z1 single
    z1 = None
    for j in range(i0, min(j1, len(t))):
        if (bl[j] <= S) if side > 0 else (ah[j] >= S): z1 = ((min(S, bo[j]) - e) if side > 0 else (e - max(S, ao[j]))) / dd; break
        if (bh[j] >= tgt) if side > 0 else (al[j] <= tgt): z1 = (tgt - e) * side / dd; break
    jj = min(j1, len(t)) - 1
    if z1 is None: z1 = ((bc[jj] - e) if side > 0 else (e - ac[jj])) / dd
    # Z2 basket: units 1 @ e, 2 @ e - d, 4 @ e - 2d; stop all @ e - 3d; exit at tgt if 1 unit, else at avg + d
    lv = [e, e - side * dd, e - side * 2 * dd]; un = [1, 2, 4]; filled = [True, False, False]; stop = e - side * 3 * dd; res = None; jx = jj
    for j in range(i0, min(j1, len(t))):
        for q in (1, 2):
            if not filled[q] and ((ah[j] <= lv[q]) if side > 0 else (bl[j] >= lv[q])): filled[q] = True
        if (bl[j] <= stop) if side > 0 else (ah[j] >= stop): px = min(stop, bo[j]) if side > 0 else max(stop, ao[j]); res = px; jx = j; break
        units = sum(u for u, f in zip(un, filled) if f); avg = sum(u * p for u, p, f in zip(un, lv, filled) if f) / units
        goal = tgt if units == 1 else avg + side * dd
        if (bh[j] >= goal) if side > 0 else (al[j] <= goal): res = goal; jx = j; break
    if res is None: res = bc[jj] if side > 0 else ac[jj]
    pnl_d = sum(u * (res - p) * side for u, p, f in zip(un, lv, filled) if f) / dd                      # in units of d per first-unit
    return dict(side=side, z1=z1, z2_d=pnl_d, z2_units=sum(u for u, f in zip(un, filled) if f), risk_bp=dd / e * 1e4, t_exit=int(t[jx] if jx < len(t) else t[-1]))


def build():
    if CACHE.exists(): return pd.read_parquet(CACHE)
    T = pd.DataFrame([r for m in MKTS for r in run_market(m)]); T.to_parquet(CACHE); return T


def st(x):
    n = len(x); return dict(n=n, mean=float(x.mean()), t=float(x.mean() / (x.std(ddof=1) / np.sqrt(n))) if n > 2 else np.nan, win=float((x > 0).mean()), pf=float(x[x > 0].sum() / -x[x < 0].sum()) if (x < 0).any() else np.nan)


def dev():
    T = build(); res = {}
    for p in ("DEV", "VAL"):
        X = G.sl(T, PER[p]); s = st(X.z1); print(f"Z1 single {p}: trades {s['n']} | win {100*s['win']:.1f}% | mean {s['mean']:+.3f} R | PF {s['pf']:.2f} | t {s['t']:+.2f}")
        with open(G.LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},sd_zones,Z1,{p},,{s['n']},,{s['mean']:.4f},{s['pf']:.3f},{s['t']:.2f},{s['win']:.3f},\n")
        if p == "DEV": dv = s
    v = st(G.sl(T, PER["VAL"]).z1); res["Z1"] = bool(dv["n"] >= 200 and dv["mean"] > 0 and dv["t"] >= 2.0 and v["mean"] > 0); print("   Z1 acceptance 1-2:", res["Z1"])
    Y = G.sl(T, ("2022-01-01", "2025-12-31")); print("   Z1 by class (2022-25 mean R, n):", {k: (round(float(g.z1.mean()), 3), len(g)) for k, g in Y.groupby(np.where(Y.mkt.isin(G.IDX), "index", np.where(Y.mkt == "XAUUSD", "gold", "FX")))}, "| median risk", round(float(Y.risk_bp.median()), 1), "bp | trades/month", round(len(Y) / 48, 1))
    usd = Y.z2_d * 150.0                                                                                  # first unit risks 150 USD (0.15%)
    print(f"Z2 basket (diagnostic) 2022-25: baskets {len(Y)} | win {100*(Y.z2_d > 0).mean():.1f}% (single Z1: {100*(Y.z1 > 0).mean():.1f}%) | mean {usd.mean():+.1f} USD per basket | units filled 1/3/7: {[(Y.z2_units == u).mean().round(3) for u in (1, 3, 7)]}")
    print(f"   worst basket {usd.min():,.0f} USD | 5 worst {sorted(usd.round(0))[:5]} | total {usd.sum():,.0f} USD over 4 years | days whose summed basket loss < -2,500: {int((usd.groupby(Y.date).sum() < -2500).sum())}")
    STATE.write_text(json.dumps(res))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dev", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    if a.dev: dev()
    if a.holdout:
        if not json.loads(STATE.read_text()).get("Z1"): print("Z1 did not pass acceptance 1-2: the 2026 hold-out stays CLOSED.")
