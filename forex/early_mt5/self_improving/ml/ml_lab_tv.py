"""ML lab + relative tick_volume channel (PREREG_ML_TV.md). Identical to ml_lab.py except the third micro channel and the tag ML3_.
   python -m mt5broker.self_improving.ml.ml_lab_tv [--placebo 51] [--jobs 16] [--tag NAME] [--classes fx,idx,cmd,crypto]"""
import sys
ARGV = sys.argv[1:]          # legacy mt5broker modules overwrite sys.argv at import time

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from scipy import stats
import xgboost as xgb

from mt5broker.self_improving import platform_v3 as P3
from mt5broker.self_improving.freeform import ff6_data as D6

HERE = Path(__file__).resolve().parent
LEDGERS = Path("D:/finance/si_ledgers"); LEDGERS.mkdir(parents=True, exist_ok=True)
NB = 48; HLIST = (4, 16, 96); HIDX = [D6.HS.index(h) for h in HLIST]; WINS = {"a": D6.WA, "b": D6.WB, "val": D6.VAL}
QS = (0.50, 0.70, 0.80, 0.90, 0.95); N_MIN, CL_MIN, BP_MIN = 100, 20, 3.0; BONF = 0.05 / 12

TV = Path("D:/finance/ticks_vol")


def with_tv(m, h):
    """Relative tick volume of each 15-minute bar: log(sum of M1 tick_volume / its causal rolling median over 96 bars). Same MT5 server-clock epoch as the bars."""
    h = h.copy(); v = pd.read_parquet(TV / f"{m}.parquet", columns=["time", "tick_volume"]); v = v.groupby(v.time // D6.BAR).tick_volume.sum()
    s = pd.Series(v.reindex(h.t0.values // D6.BAR).values.astype(float)); med = s.rolling(96, min_periods=48).median()
    h["tvr"] = np.log(np.maximum(s, 1.0) / np.maximum(med, 1.0)).values; return h


def market_arrays(h, carry):
    n = len(h); c = h.bc.values; lc = np.log(c); r = np.diff(lc, prepend=lc[0]); sd = pd.Series(r).rolling(384, min_periods=192).std().values
    spr = (h.spm / h.spm.rolling(96, min_periods=48).median()).values; rvn = (h.rv.values / sd ** 2)
    P4 = [np.log(h.bo.values), np.log(h.bh.values), np.log(h.bl.values), lc]; micro = [np.clip(np.nan_to_num(rvn, nan=1.0, posinf=20.0), 0, 20), np.clip(np.nan_to_num(spr, nan=1.0, posinf=5.0), 0, 5), np.clip(np.nan_to_num(h.tvr.values, nan=0.0, posinf=3.0, neginf=-3.0), -3, 3)]
    W4 = [sliding_window_view(p, NB) for p in P4]; Wm = [sliding_window_view(m, NB) for m in micro]
    hour = (h.t0.values // 3600) % 24; dow = ((h.t0.values // 86400) + 3) % 7; sdmed = pd.Series(sd).rolling(2000, min_periods=500).median().values; volr = np.log(sd / sdmed)
    L, S, X, G = D6.fwd(h, carry); t0 = h.t0.values
    out = {}
    for w, (a0, b0) in WINS.items():
        a, b = D6.ts(a0), D6.ts(b0) + 86400; inw = np.nonzero((t0 >= a) & (t0 < b))[0]
        if len(inw) == 0: continue
        pos = np.arange(len(inw)); keep = (pos % 4 == 0) & (inw >= NB - 1) & np.isfinite(sd[inw]) & np.isfinite(volr[inw]) & ~np.isin(hour[inw], (23, 0)); idx = inw[keep]; pos = pos[keep]      # Amendment 1: no decision in the rollover hours
        Xp = np.concatenate([(W4[k][idx - NB + 1] - lc[idx][:, None]) / sd[idx][:, None] for k in range(4)], axis=1); Xp = np.clip(Xp, -30, 30)
        Xm = np.concatenate([Wm[k][idx - NB + 1] for k in range(3)], axis=1)
        Xt = np.stack([np.sin(2 * np.pi * hour[idx] / 24), np.cos(2 * np.pi * hour[idx] / 24), np.sin(2 * np.pi * dow[idx] / 7), np.cos(2 * np.pi * dow[idx] / 7), volr[idx]], axis=1)
        Xf = np.concatenate([Xp, Xm, Xt], axis=1).astype(np.float32)
        G_, L_, S_, X_ = G[idx][:, HIDX].astype(np.float64), L[idx][:, HIDX].astype(np.float64), S[idx][:, HIDX].astype(np.float64), X[idx][:, HIDX]
        xh = ((X_ - D6.BAR) // 3600) % 24; bad = (X_ > b) | (xh == 23) | (xh == 0); G_[bad] = np.nan; L_[bad] = np.nan; S_[bad] = np.nan      # Amendment 1: no exit bar in the rollover hours either
        y = np.stack([np.clip(G_[:, j] / (sd[idx] * np.sqrt(HLIST[j])), -5, 5) for j in range(3)], axis=1)
        out[w] = dict(X=Xf, y=y, G=G_, L=L_, S=S_, pos=pos, week=(t0[idx] // (7 * 86400)).astype(np.int32))
    return out


def build_class(cls, placebo):
    carry = P3.CLASSES[cls]["carry"]; hs = {}
    for m in P3.CLASSES[cls]["members"]:
        h = with_tv(m, D6.bars15(m))
        if len(h) > 40000: hs[m] = h
    if placebo is not None: hs = D6.Stack.shuffle(hs, placebo)
    parts = {w: [] for w in WINS}
    for mi, (m, h) in enumerate(hs.items()):
        arr = market_arrays(h, carry)
        for w, d in arr.items(): d["mkt"] = np.full(len(d["pos"]), mi, np.int16); parts[w].append(d)
    return {w: {k: np.concatenate([p[k] for p in P]) for k in P[0]} for w, P in parts.items()}


def cluster_stat(ex, week):
    n = len(ex)
    if n < 30: return n, 0, np.nan, 1.0
    m = ex.mean(); wk = week - week.min(); cnt = np.bincount(wk); res = np.bincount(wk, weights=ex - m); cl = int((cnt > 0).sum())
    if cl < 5: return n, cl, np.nan, 1.0
    se = np.sqrt((res ** 2).sum() * cl / (cl - 1)) / n
    if se == 0: return n, cl, np.nan, 1.0
    z = m / se; return n, cl, float(z), float(stats.t.sf(z, cl - 1))


def trades(d, pred, hj, tau):
    H = HLIST[hj]; grid = (d["pos"] % H == 0) & np.isfinite(d["y"][:, hj]); side = np.sign(pred); sel = grid & (np.abs(pred) >= tau) & (side != 0)
    net = np.where(side > 0, d["L"][:, hj], d["S"][:, hj]); g = d["G"][:, hj]; gs = np.where(side > 0, g, 1.0 / (1.0 + g) - 1.0)
    return sel, side, net, gs, grid


def baseline(d, hj, grid):
    """Random-timing gross mean per market and side on the same grid."""
    g = d["G"][:, hj]; out = {}
    for sd_ in (1, -1):
        gs = g if sd_ > 0 else 1.0 / (1.0 + g) - 1.0; ok = grid & np.isfinite(gs); nm = int(d["mkt"].max()) + 1
        out[sd_] = np.bincount(d["mkt"][ok], weights=gs[ok], minlength=nm) / np.maximum(np.bincount(d["mkt"][ok], minlength=nm), 1)
    return out


def run_cell(data, hj, jobs):
    A, B, V = data["a"], data["b"], data["val"]; ia, ib, iv = np.isfinite(A["y"][:, hj]), np.isfinite(B["y"][:, hj]), np.isfinite(V["y"][:, hj])
    m = xgb.XGBRegressor(n_estimators=400, max_depth=5, learning_rate=0.05, subsample=0.7, colsample_bytree=0.5, min_child_weight=200, reg_lambda=10.0, tree_method="hist", n_jobs=jobs, early_stopping_rounds=30, eval_metric="rmse")
    m.fit(A["X"][ia], A["y"][ia, hj], eval_set=[(B["X"][ib], B["y"][ib, hj])], verbose=False)
    pb, pv = m.predict(B["X"]), m.predict(V["X"]); best = None
    for q in QS:
        selg = (B["pos"] % HLIST[hj] == 0) & ib
        tau = float(np.quantile(np.abs(pb[selg]), q)); sel, side, net, gs, grid = trades(B, pb, hj, tau)
        if sel.sum() >= N_MIN:
            mn = float(np.nanmean(net[sel]))
            if best is None or mn > best[1]: best = (tau, mn, q)
    if best is None: tau = float(np.quantile(np.abs(pb[(B["pos"] % HLIST[hj] == 0) & ib]), 0.5)); best = (tau, np.nan, 0.5)
    tau, bmean, q = best
    res = dict(tau_q=q, trees=int(m.best_iteration + 1 if hasattr(m, "best_iteration") and m.best_iteration is not None else 400), B_net_bp=1e4 * bmean if np.isfinite(bmean) else np.nan)
    for nm, d, p in (("B", B, pb), ("VAL", V, pv)):
        ok = np.isfinite(d["y"][:, hj]); res[f"{nm}_ic"] = float(stats.spearmanr(p[ok], d["y"][ok, hj])[0])
        sel, side, net, gs, grid = trades(d, p, hj, tau); bl = baseline(d, hj, grid)
        if sel.sum() == 0: res.update({f"{nm}_n": 0, f"{nm}_cl": 0, f"{nm}_net_bp": np.nan, f"{nm}_z": np.nan, f"{nm}_p": 1.0}); continue
        mk = d["mkt"][sel]; sd_ = side[sel]; ex = gs[sel] - np.where(sd_ > 0, bl[1][mk], bl[-1][mk]); n, cl, z, pv_ = cluster_stat(ex, d["week"][sel])
        res.update({f"{nm}_n": int(n), f"{nm}_cl": int(cl), f"{nm}_net_bp": 1e4 * float(np.nanmean(net[sel])), f"{nm}_z": z, f"{nm}_p": pv_})
    res["pass"] = bool(res["VAL_n"] >= N_MIN and res["VAL_cl"] >= CL_MIN and res["VAL_net_bp"] >= BP_MIN and res["VAL_p"] < BONF)
    return res


def run(placebo, jobs, tag, classes):
    name = tag or (f"placebo{placebo}" if placebo is not None else "real"); rows = []; t00 = time.time()
    for cls in classes:
        t0 = time.time(); data = build_class(cls, placebo); print(f"[{cls}] windows built in {time.time()-t0:.0f}s: " + " ".join(f"{w}={len(data[w]['pos']):,}" for w in data), flush=True)
        for hj, H in enumerate(HLIST):
            t1 = time.time(); r = run_cell(data, hj, jobs); r.update(cls=cls, H=H); rows.append(r)
            print(f"[{cls} H={H}] IC B {r['B_ic']:+.4f} VAL {r['VAL_ic']:+.4f} | tau q={r['tau_q']} | B net {r['B_net_bp']:+.1f}bp | VAL n={r['VAL_n']} cl={r['VAL_cl']} net {r['VAL_net_bp']:+.1f}bp z={r['VAL_z']:.2f} p={r['VAL_p']:.3f} | pass={r['pass']} ({time.time()-t1:.0f}s)", flush=True)
        del data
    df = pd.DataFrame(rows); df.to_csv(LEDGERS / f"ML3_{name}.csv", index=False)
    print(f"DONE {name}: cells passing {int(df['pass'].sum())} of {len(df)} | max VAL IC {df.VAL_ic.max():+.4f} | max VAL z {df.VAL_z.max():.2f} | {time.time()-t00:.0f}s", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--placebo", type=int, default=None); ap.add_argument("--jobs", type=int, default=16); ap.add_argument("--tag", default=None); ap.add_argument("--classes", default="fx,idx,cmd,crypto"); a = ap.parse_args(ARGV)
    run(a.placebo, a.jobs, a.tag, a.classes.split(","))
