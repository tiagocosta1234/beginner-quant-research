"""Frequent-trading lab on real ticks (PREREG_HF.md).
   python -m forex.self_improving.hf.hf_lab [--placebo 61] [--jobs 16] [--tag NAME] [--classes fx,idx,cmd,crypto]"""
import sys
ARGV = sys.argv[1:]

import argparse
import re
import time

import numpy as np
import pandas as pd
from scipy import stats
import xgboost as xgb

from forex.self_improving.hf import hf_data as D

LEDGER = D.FEAT.parent / "si_ledgers"; LEDGER.mkdir(parents=True, exist_ok=True)
EXECS = ("mkt", "lim0", "lim1"); QS = (0.50, 0.70, 0.80, 0.90, 0.95); N_MIN, CL_MIN = 2000, 20; BONF = 0.05 / 48; CAP = 300000


def load_class(cls, placebo):
    frames = []
    for mi, sym in enumerate(D.SYMS[cls]):
        f = pd.read_parquet(D.FEAT / f"{sym}.parquet"); f["mkt"] = mi
        if placebo is not None:                                            # labels circularly shifted by a common fraction of the timeline: no feature-label relation, all real costs and fills
            frac = 0.15 + 0.7 * np.random.default_rng(placebo).random(); k = int(len(f) * frac); lab = [c for c in f.columns if re.fullmatch(r"m[GLS]\d+|l\d[LS]\d+", c)]
            f[lab] = np.roll(f[lab].values, k, axis=0)
        frames.append(f)
    return pd.concat(frames, ignore_index=True)


def label_cols(ex, H):
    if ex == "mkt": return None, f"mG{H}", f"mL{H}", f"mS{H}"
    d = ex[-1]; return None, None, f"l{d}L{H}", f"l{d}S{H}"


def cluster(ex, day):
    n = len(ex)
    if n < 30: return n, 0, np.nan, 1.0
    m = ex.mean(); u, inv = np.unique(day, return_inverse=True); res = np.bincount(inv, weights=ex - m); cl = len(u)
    if cl < 5: return n, cl, np.nan, 1.0
    se = np.sqrt((res ** 2).sum() * cl / (cl - 1)) / n
    if se == 0: return n, cl, np.nan, 1.0
    z = m / se; return n, cl, float(z), float(stats.t.sf(z, cl - 1))


def greedy(df, sel, H):
    """Keep orders in time order per market with no overlap (conservative: an order blocks the market until it can no longer be open)."""
    keep = np.zeros(len(df), bool); span = D.LAT + D.WAIT + H * 60000 + D.LAT; t = df.t.values; mk = df.mkt.values; idx = np.nonzero(sel)[0]
    for m in np.unique(mk[idx]):
        free = -1
        for i in idx[mk[idx] == m]:
            if t[i] >= free: keep[i] = True; free = t[i] + span
    return keep


def fit(Xa, ya, Xb, yb, jobs, seed=1):
    if len(ya) > CAP: s = np.random.default_rng(seed).choice(len(ya), CAP, replace=False); Xa, ya = Xa[s], ya[s]
    m = xgb.XGBRegressor(n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.7, colsample_bytree=0.5, min_child_weight=200, reg_lambda=10.0, tree_method="hist", max_bin=64, n_jobs=jobs, early_stopping_rounds=30, eval_metric="rmse")
    m.fit(Xa, ya, eval_set=[(Xb, yb)], verbose=False); return m


def run_cell(df, ex, H, jobs):
    A, B, V = (df[df.win == w].reset_index(drop=True) for w in ("a", "b", "val")); X = lambda d: d[D.FEATS].values.astype(np.float32); _, gcol, lcol, scol = label_cols(ex, H)
    def one_side(col, sign):
        ya, yb = A[col].values, B[col].values; ia, ib = np.isfinite(ya), np.isfinite(yb)
        sc = np.nanstd(ya) if np.isfinite(ya).sum() > 10 else 1.0
        return fit(X(A)[ia], np.clip(ya[ia] / sc, -8, 8), X(B)[ib], np.clip(yb[ib] / sc, -8, 8), jobs)
    if ex == "mkt":
        ya, yb = A[gcol].values, B[gcol].values; ia, ib = np.isfinite(ya), np.isfinite(yb); sc = np.nanstd(ya)
        m = fit(X(A)[ia], np.clip(ya[ia] / sc, -8, 8), X(B)[ib], np.clip(yb[ib] / sc, -8, 8), jobs); pred = lambda d: m.predict(X(d))
        score = lambda d: (np.abs(pred(d)), np.sign(pred(d)))                   # (strength, side)
    else:
        mL, mS = one_side(lcol, 1), one_side(scol, -1)
        def score(d):
            pl, ps = mL.predict(X(d)), mS.predict(X(d)); return np.maximum(pl, ps), np.where(pl >= ps, 1.0, -1.0)
    sb, sdb = score(B); sv, sdv = score(V); net_col = lambda d, side: np.where(side > 0, d[lcol].values, d[scol].values); best = None
    for q in QS:
        tau = float(np.quantile(sb, q)); sel = (sb >= tau) & (sdb != 0); keep = greedy(B, sel, H); net = net_col(B, sdb)[keep]; net = net[np.isfinite(net)]
        if len(net) >= N_MIN:
            mn = float(net.mean())
            if best is None or mn > best[1]: best = (tau, mn, q)
    if best is None: best = (float(np.quantile(sb, 0.5)), np.nan, 0.5)
    tau, bmean, q = best; res = dict(tau_q=q, B_net_bp=1e4 * bmean if np.isfinite(bmean) else np.nan)
    sel = (sv >= tau) & (sdv != 0); keep = greedy(V, sel, H); side = sdv[keep]; netv = net_col(V, sdv)[keep]; ok = np.isfinite(netv)
    if ok.sum() == 0: res.update(VAL_n=0, VAL_cl=0, VAL_net_bp=np.nan, VAL_z=np.nan, VAL_p=1.0, pass_=False); return res
    base = {}
    for s_, col in ((1, lcol), (-1, scol)):
        for mk in np.unique(V.mkt): v = V[col].values[V.mkt.values == mk]; base[(s_, mk)] = np.nanmean(v) if np.isfinite(v).any() else 0.0
    mk = V.mkt.values[keep][ok]; sd_ = side[ok]; label = netv[ok]; ex_ = label - np.array([base[(int(a), int(b))] for a, b in zip(sd_, mk)]); n, cl, z, p = cluster(ex_, V.dayid.values[keep][ok])
    res.update(VAL_n=int(n), VAL_cl=int(cl), VAL_net_bp=1e4 * float(label.mean()), VAL_z=z, VAL_p=p)
    res["pass_"] = bool(n >= N_MIN and cl >= CL_MIN and res["VAL_net_bp"] > 0 and p < BONF); return res


def lower_priority():
    try:
        import ctypes; ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)   # BELOW_NORMAL: this PC may be the live account PC
    except Exception: pass


def run(placebo, jobs, tag, classes):
    lower_priority()
    name = tag or (f"placebo{placebo}" if placebo is not None else "real"); rows = []; t00 = time.time()
    for cls in classes:
        df = load_class(cls, placebo); print(f"[{cls}] {len(df):,} decisions: " + " ".join(f"{w}={int((df.win==w).sum()):,}" for w in ("a", "b", "val")), flush=True)
        for ex in EXECS:
            for H in D.HLIST:
                t1 = time.time(); r = run_cell(df, ex, H, jobs); r.update(cls=cls, ex=ex, H=H); rows.append(r)
                print(f"[{cls} {ex} H={H}] tau q={r['tau_q']} B net {r['B_net_bp']:+.2f}bp | VAL n={r['VAL_n']} cl={r['VAL_cl']} net {r['VAL_net_bp']:+.2f}bp z={r['VAL_z']:.2f} p={r['VAL_p']:.3f} | pass={r['pass_']} ({time.time()-t1:.0f}s)", flush=True)
        del df
    out = pd.DataFrame(rows); out.to_csv(LEDGER / f"HF_{name}.csv", index=False)
    print(f"DONE {name}: cells passing {int(out.pass_.sum())} of {len(out)} | max VAL net {out.VAL_net_bp.max():+.2f} bp | max VAL z {out.VAL_z.max():.2f} | {time.time()-t00:.0f}s", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--placebo", type=int, default=None); ap.add_argument("--jobs", type=int, default=16); ap.add_argument("--tag", default=None); ap.add_argument("--classes", default="fx,idx,cmd,crypto"); a = ap.parse_args(ARGV)
    run(a.placebo, a.jobs, a.tag, a.classes.split(","))
