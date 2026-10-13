"""Hold-until-a-barrier lab (PREREG_BARRIER2.md).  python -m mt5broker.self_improving.barrier.barrier_lab2 [--placebo 111] [--jobs 6] [--tag NAME]"""
import sys
ARGV = sys.argv[1:]
import argparse, time
import numpy as np, pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from mt5broker.self_improving import platform_v3 as P3
from mt5broker.self_improving.freeform import ff6_data as D6
from mt5broker.self_improving.ml import ml_lab_tv as M
from mt5broker.self_improving.barrier import barrier_lab as B

K2 = 480; KS2 = (2.0, 4.0); TP_MULT = 1.0; SL_MULT = 1.0      # asymmetric bracket: take-profit = TP_MULT x X, stop = SL_MULT x X, R in stop units (win = TP_MULT/SL_MULT)


def labels2(h, k, sd1h):
    """Returns RL, RS, exit time of long, exit time of short (epoch s); NaN R if the data ends before resolution."""
    n = len(h); bo, bh, bl, bc, ao, ah, al, ac = (h[c].values.astype(np.float64) for c in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")); t0 = h.t0.values
    hour = (t0 // 3600) % 24; roll = (hour == 23) | (hour == 0); i = np.arange(n - 1); e = i + 1; res = {}
    for side in (1, -1):
        ent = (ao if side > 0 else bo)[e]; X0 = k * sd1h[i] * ent; Xt, X = X0 * TP_MULT, X0 * SL_MULT; win = TP_MULT / SL_MULT; tp = ent + Xt if side > 0 else ent - Xt; sl = ent - X if side > 0 else ent + X
        R = np.full(len(i), np.nan); T = np.full(len(i), np.nan); act = np.nonzero(np.isfinite(X) & (X > 0))[0]
        for m in range(K2):
            if len(act) == 0: break
            j = e[act] + m; inr = j < n; act_in = act[inr]; j = j[inr]
            if len(act_in) == 0: break
            chk = ~roll[j]; hit_tp = ((bh[j] >= tp[act_in]) if side > 0 else (al[j] <= tp[act_in])) & chk; hit_sl = ((bl[j] <= sl[act_in]) if side > 0 else (ah[j] >= sl[act_in])) & chk
            fin = hit_tp | hit_sl; idx = act_in[fin]; R[idx] = np.where(hit_sl[fin], -1.0, win); T[idx] = t0[j[fin]]
            keep = np.ones(len(act), bool); pos_in = np.nonzero(inr)[0]; keep[pos_in[fin]] = False; act = act[keep]
        # unresolved after K2 bars (or data end): exit at close only if the 5 days elapsed
        ok5 = act[(e[act] + K2 - 1) < n]
        if len(ok5):
            jx = e[ok5] + K2 - 1; R[ok5] = np.clip(((bc[jx] - ent[ok5]) if side > 0 else (ent[ok5] - ac[jx])) / X[ok5], -1, win); T[ok5] = t0[jx]
        res[side] = (np.concatenate([R, [np.nan]]), np.concatenate([T, [np.nan]]))
    return res[1][0], res[-1][0], res[1][1], res[-1][1]


def market_arrays(h, k):
    c = h.bc.values; lc = np.log(c); r = np.diff(lc, prepend=lc[0]); sd = pd.Series(r).rolling(384, min_periods=192).std().values
    spr = (h.spm / h.spm.rolling(96, min_periods=48).median()).values; rvn = (h.rv.values / sd ** 2)
    P4 = [np.log(h.bo.values), np.log(h.bh.values), np.log(h.bl.values), lc]
    micro = [np.clip(np.nan_to_num(rvn, nan=1.0, posinf=20.0), 0, 20), np.clip(np.nan_to_num(spr, nan=1.0, posinf=5.0), 0, 5), np.clip(np.nan_to_num(h.tvr.values, nan=0.0, posinf=3.0, neginf=-3.0), -3, 3)]
    W4 = [sliding_window_view(p, B.NB) for p in P4]; Wm = [sliding_window_view(m, B.NB) for m in micro]
    t0 = h.t0.values; hour = (t0 // 3600) % 24; dow = ((t0 // 86400) + 3) % 7; sdmed = pd.Series(sd).rolling(2000, min_periods=500).median().values; volr = np.log(sd / sdmed)
    RL, RS, TL, TS = labels2(h, k, sd * 4.0); out = {}
    for w, (a0, b0) in B.WINS.items():
        a, b = D6.ts(a0), D6.ts(b0) + 86400; inw = np.nonzero((t0 >= a) & (t0 < b))[0]
        if len(inw) == 0: continue
        pos = np.arange(len(inw)); keep = (pos % 4 == 0) & (inw >= B.NB - 1) & np.isfinite(sd[inw]) & np.isfinite(volr[inw]) & (hour[inw] >= 1) & (hour[inw] <= 14); idx = inw[keep]; pos = pos[keep]
        Xp = np.clip(np.concatenate([(W4[q][idx - B.NB + 1] - lc[idx][:, None]) / sd[idx][:, None] for q in range(4)], axis=1), -30, 30); Xm = np.concatenate([Wm[q][idx - B.NB + 1] for q in range(3)], axis=1)
        Xt = np.stack([np.sin(2 * np.pi * hour[idx] / 24), np.cos(2 * np.pi * hour[idx] / 24), np.sin(2 * np.pi * dow[idx] / 7), np.cos(2 * np.pi * dow[idx] / 7), volr[idx]], axis=1)
        rl, rs = RL[idx].copy(), RS[idx].copy(); rl[~(TL[idx] < b)] = np.nan; rs[~(TS[idx] < b)] = np.nan          # no label built from prices after the window end
        out[w] = dict(entL=h.ao.values[np.minimum(idx + 1, len(h) - 1)], entS=h.bo.values[np.minimum(idx + 1, len(h) - 1)], x1h=sd[idx] * 4.0, t0=t0[idx], X=np.concatenate([Xp, Xm, Xt], axis=1).astype(np.float32), RL=rl, RS=rs, pos=pos, week=(t0[idx] // (7 * 86400)).astype(np.int32), dur_l=(TL[idx] - t0[idx]) / 3600.0, dur_s=(TS[idx] - t0[idx]) / 3600.0)
    return out


def build_class(cls, placebo, k):
    hs = {}
    for m in P3.CLASSES[cls]["members"]:
        h = D6.bars15(m)
        if len(h) > 40000: hs[m] = M.with_tv(m, h)
    if placebo is not None: hs = D6.Stack.shuffle(hs, placebo)
    parts = {w: [] for w in B.WINS}
    for mi, (m, h) in enumerate(hs.items()):
        for w, d in market_arrays(h, k).items(): d["mkt"] = np.full(len(d["pos"]), mi, np.int16); parts[w].append(d)
    return {w: {q: np.concatenate([p[q] for p in P]) for q in P[0]} for w, P in parts.items()}


def run(placebo, jobs, tag):
    name = tag or (f"placebo{placebo}" if placebo is not None else "real"); rows = []; t00 = time.time()
    for cls in P3.CLASSES:
        for k in KS2:
            data = build_class(cls, placebo, k); r = B.run_cell(data, jobs); r.update(cls=cls, k=k)
            V = data["val"]; r["VAL_hours_median"] = float(np.nanmedian(np.concatenate([V["dur_l"], V["dur_s"]]))); rows.append(r)
            print(f"[{cls} k={k}] B meanR {r['B_meanR']:+.3f} | VAL n={r['VAL_n']} cl={r['VAL_cl']} meanR {r['VAL_meanR']:+.3f} hit {100 * r['VAL_hit']:.0f}% z={r['VAL_z']:.2f} p={r['VAL_p']:.3f} | median hold {r['VAL_hours_median']:.0f}h | pass={r['pass']}", flush=True); del data
    df = pd.DataFrame(rows); df.to_csv(B.LED / f"BARRIER2_{name}.csv", index=False)
    print(f"DONE {name}: cells passing {int(df['pass'].sum())} of {len(df)} | max VAL meanR {df.VAL_meanR.max():+.3f} | max VAL hit {100 * df.VAL_hit.max():.0f}% | max VAL z {df.VAL_z.max():.2f} | {time.time() - t00:.0f}s", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--placebo", type=int, default=None); ap.add_argument("--jobs", type=int, default=6); ap.add_argument("--tag", default=None); a = ap.parse_args(ARGV); run(a.placebo, a.jobs, a.tag)
