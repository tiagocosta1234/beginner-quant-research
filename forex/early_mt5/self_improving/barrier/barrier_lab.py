"""First-passage bracket lab (PREREG_BARRIER.md).  python -m mt5broker.self_improving.barrier.barrier_lab [--placebo 101] [--jobs 6] [--tag NAME]"""
import sys
ARGV = sys.argv[1:]
import argparse, time
from pathlib import Path
import numpy as np, pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
import xgboost as xgb
from mt5broker.self_improving import platform_v3 as P3
from mt5broker.self_improving.freeform import ff6_data as D6
from mt5broker.self_improving.ml import ml_lab_tv as M

LED = Path("D:/finance/si_ledgers"); NB = 48; K = 32; KS = (1.0, 2.0); WINS = {"a": D6.WA, "b": D6.WB, "val": D6.VAL}
N_MIN, CL_MIN, R_MIN, BONF = 100, 20, 0.20, 0.05 / 8; QS = (0.50, 0.70, 0.80, 0.90, 0.95); GRID = 8


def labels(h, k, sd1h):
    n = len(h); bo, bh, bl, bc, ao, ah, al, ac = (h[c].values.astype(np.float64) for c in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")); t0 = h.t0.values
    i = np.arange(n); ok = (i + K < n); ic = np.minimum(i, n - K - 1); e = ic + 1
    eL, eS = ao[e], bo[e]; out = {}
    for side in (1, -1):
        ent = eL if side > 0 else eS; X = k * sd1h[ic] * ent; tp = ent + X if side > 0 else ent - X; sl = ent - X if side > 0 else ent + X
        done = np.zeros(n, bool); R = np.zeros(n)
        for m in range(K):
            j = e + m; hit_tp = (bh[j] >= tp) if side > 0 else (al[j] <= tp); hit_sl = (bl[j] <= sl) if side > 0 else (ah[j] >= sl)
            new = ~done & (hit_tp | hit_sl); R[new] = np.where(hit_sl[new], -1.0, 1.0); done |= new
        fin = (bc[ic + K] - ent) / X if side > 0 else (ent - ac[ic + K]) / X
        R = np.where(done, R, np.clip(fin, -1, 1)); contiguous = (t0[ic + K] - t0[e]) == (K - 1) * D6.BAR
        out[side] = np.where(ok & contiguous & np.isfinite(R) & (X > 0), R, np.nan)
    return out[1], out[-1]


def market_arrays(h, k):
    c = h.bc.values; lc = np.log(c); r = np.diff(lc, prepend=lc[0]); sd = pd.Series(r).rolling(384, min_periods=192).std().values
    spr = (h.spm / h.spm.rolling(96, min_periods=48).median()).values; rvn = (h.rv.values / sd ** 2)
    P4 = [np.log(h.bo.values), np.log(h.bh.values), np.log(h.bl.values), lc]
    micro = [np.clip(np.nan_to_num(rvn, nan=1.0, posinf=20.0), 0, 20), np.clip(np.nan_to_num(spr, nan=1.0, posinf=5.0), 0, 5), np.clip(np.nan_to_num(h.tvr.values, nan=0.0, posinf=3.0, neginf=-3.0), -3, 3)]
    W4 = [sliding_window_view(p, NB) for p in P4]; Wm = [sliding_window_view(m, NB) for m in micro]
    t0 = h.t0.values; hour = (t0 // 3600) % 24; dow = ((t0 // 86400) + 3) % 7; sdmed = pd.Series(sd).rolling(2000, min_periods=500).median().values; volr = np.log(sd / sdmed)
    RL, RS = labels(h, k, sd * 4.0); out = {}
    for w, (a0, b0) in WINS.items():
        a, b = D6.ts(a0), D6.ts(b0) + 86400; inw = np.nonzero((t0 >= a) & (t0 < b))[0]
        if len(inw) == 0: continue
        pos = np.arange(len(inw)); keep = (pos % 4 == 0) & (inw >= NB - 1) & np.isfinite(sd[inw]) & np.isfinite(volr[inw]) & (hour[inw] >= 1) & (hour[inw] <= 14); idx = inw[keep]; pos = pos[keep]
        Xp = np.clip(np.concatenate([(W4[q][idx - NB + 1] - lc[idx][:, None]) / sd[idx][:, None] for q in range(4)], axis=1), -30, 30); Xm = np.concatenate([Wm[q][idx - NB + 1] for q in range(3)], axis=1)
        Xt = np.stack([np.sin(2 * np.pi * hour[idx] / 24), np.cos(2 * np.pi * hour[idx] / 24), np.sin(2 * np.pi * dow[idx] / 7), np.cos(2 * np.pi * dow[idx] / 7), volr[idx]], axis=1)
        out[w] = dict(X=np.concatenate([Xp, Xm, Xt], axis=1).astype(np.float32), RL=RL[idx], RS=RS[idx], pos=pos, week=(t0[idx] // (7 * 86400)).astype(np.int32))
    return out


def build_class(cls, placebo, k):
    hs = {}
    for m in P3.CLASSES[cls]["members"]:
        h = D6.bars15(m)
        if len(h) > 40000: hs[m] = M.with_tv(m, h)
    if placebo is not None: hs = D6.Stack.shuffle(hs, placebo)
    parts = {w: [] for w in WINS}
    for mi, (m, h) in enumerate(hs.items()):
        for w, d in market_arrays(h, k).items(): d["mkt"] = np.full(len(d["pos"]), mi, np.int16); parts[w].append(d)
    return {w: {q: np.concatenate([p[q] for p in P]) for q in P[0]} for w, P in parts.items()}


def choose(d, pl, ps):
    best = np.maximum(pl, ps); side = np.where(pl >= ps, 1, -1); R = np.where(side > 0, d["RL"], d["RS"]); return best, side, R


def stat(d, best, side, R, tau):
    grid = (d["pos"] % GRID == 0) & np.isfinite(R); sel = grid & (best >= tau)
    if sel.sum() == 0: return dict(n=0, cl=0, meanR=np.nan, hit=np.nan, z=np.nan, p=1.0)
    nm = int(d["mkt"].max()) + 1; base = {}
    for s_, col in ((1, "RL"), (-1, "RS")):
        ok = (d["pos"] % GRID == 0) & np.isfinite(d[col]); base[s_] = np.bincount(d["mkt"][ok], weights=d[col][ok], minlength=nm) / np.maximum(np.bincount(d["mkt"][ok], minlength=nm), 1)
    mk, sd_, r = d["mkt"][sel], side[sel], R[sel]; ex = r - np.where(sd_ > 0, base[1][mk], base[-1][mk]); n, cl, z, p = M.cluster_stat(ex, d["week"][sel])
    w, l = (r == 1.0).sum(), (r == -1.0).sum(); return dict(n=int(n), cl=int(cl), meanR=float(r.mean()), hit=float(w / max(w + l, 1)), z=z, p=p)


def run_cell(data, jobs):
    A, B, V = data["a"], data["b"], data["val"]; mdl = {}
    for nm in ("RL", "RS"):
        ia, ib = np.isfinite(A[nm]), np.isfinite(B[nm])
        m = xgb.XGBRegressor(n_estimators=400, max_depth=5, learning_rate=0.05, subsample=0.7, colsample_bytree=0.5, min_child_weight=200, reg_lambda=10.0, tree_method="hist", n_jobs=jobs, early_stopping_rounds=30, eval_metric="rmse")
        m.fit(A["X"][ia], A[nm][ia], eval_set=[(B["X"][ib], B[nm][ib])], verbose=False); mdl[nm] = m
    pB = [mdl[n].predict(B["X"]) for n in ("RL", "RS")]; pV = [mdl[n].predict(V["X"]) for n in ("RL", "RS")]
    bB, sB, RB = choose(B, *pB); best = None; gridB = (B["pos"] % GRID == 0) & np.isfinite(RB)
    for q in QS:
        tau = float(np.quantile(bB[gridB], q)); sel = gridB & (bB >= tau)
        if sel.sum() >= N_MIN:
            mr = float(RB[sel].mean())
            if best is None or mr > best[1]: best = (tau, mr, q)
    if best is None: best = (float(np.quantile(bB[gridB], 0.5)), np.nan, 0.5)
    tau, bmr, q = best; res = dict(tau_q=q, B_meanR=bmr)
    for nm, d, pp in (("B", B, pB), ("VAL", V, pV)):
        b_, s_, R_ = choose(d, *pp); st = stat(d, b_, s_, R_, tau); res.update({f"{nm}_{k_}": v for k_, v in st.items()})
    res["pass"] = bool(res["VAL_n"] >= N_MIN and res["VAL_cl"] >= CL_MIN and res["VAL_meanR"] >= R_MIN and res["VAL_p"] < BONF); return res


def run(placebo, jobs, tag):
    name = tag or (f"placebo{placebo}" if placebo is not None else "real"); rows = []; t00 = time.time()
    for cls in P3.CLASSES:
        for k in KS:
            data = build_class(cls, placebo, k); r = run_cell(data, jobs); r.update(cls=cls, k=k); rows.append(r)
            print(f"[{cls} k={k}] B meanR {r['B_meanR']:+.3f} | VAL n={r['VAL_n']} cl={r['VAL_cl']} meanR {r['VAL_meanR']:+.3f} hit {100 * r['VAL_hit']:.0f}% z={r['VAL_z']:.2f} p={r['VAL_p']:.3f} | pass={r['pass']}", flush=True); del data
    df = pd.DataFrame(rows); df.to_csv(LED / f"BARRIER_{name}.csv", index=False)
    print(f"DONE {name}: cells passing {int(df['pass'].sum())} of {len(df)} | max VAL meanR {df.VAL_meanR.max():+.3f} | max VAL hit {100 * df.VAL_hit.max():.0f}% | max VAL z {df.VAL_z.max():.2f} | {time.time() - t00:.0f}s", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--placebo", type=int, default=None); ap.add_argument("--jobs", type=int, default=6); ap.add_argument("--tag", default=None); a = ap.parse_args(ARGV); run(a.placebo, a.jobs, a.tag)
