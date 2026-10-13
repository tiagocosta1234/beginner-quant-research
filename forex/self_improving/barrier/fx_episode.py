"""Episode game (+2,000 / -1,500 of equity, multi-day, no midnight reset) on the multi-symbol FX cell found in BARRIER2 (fx, k=4, symmetric 4-sigma brackets, 28 pairs, 2025).
Trades: VAL 2025 trades of the model trained on 2022-23H1 (tau chosen on 2023H2-24). Each trade risks S USD at its own stop (4 hourly sigmas); total open stop-risk capped at CAP (first come).
At a barrier every open position is closed at the minute quote and a new episode starts.  python -m forex.self_improving.barrier.fx_episode"""
import sys
ARGV = sys.argv[1:]
import numpy as np, pandas as pd
from forex.self_improving import platform_v3 as P3
from forex.self_improving.barrier import barrier_lab as B, barrier_lab2 as B2, barrier_lab3 as B3

B2.TP_MULT, B2.SL_MULT = 1.0, 1.0; UP, DN, K = 2000.0, 1500.0, 4.0
T0, T1 = int(pd.Timestamp("2025-01-01").timestamp()), int(pd.Timestamp("2026-01-01").timestamp())


def trades_val():
    data = B2.build_class("fx", None, K); st, sel, s_, R_, V = B3.fit(data); names = [m for m in P3.CLASSES["fx"]["members"] if len(B2.D6.bars15(m)) > 40000]
    side = s_[sel]; ent = np.where(side > 0, V["entL"][sel], V["entS"][sel]); X = K * V["x1h"][sel] * ent; hold = np.where(side > 0, V["dur_l"][sel], V["dur_s"][sel]) * 3600.0
    df = pd.DataFrame(dict(sym=[names[i] for i in V["mkt"][sel]], side=side, R=R_[sel], t_in=V["t0"][sel] + 900.0, ent=ent, X=X, t_out=V["t0"][sel] + hold)).dropna()
    print(f"VAL trades {len(df)} (hit {100 * (df.R == 1).sum() / max(((df.R == 1) | (df.R == -1)).sum(), 1):.0f}%, mean R {df.R.mean():+.3f}, long share {100 * (df.side > 0).mean():.0f}%)", flush=True); return df.sort_values("t_in").reset_index(drop=True)


def grids(syms):
    g = np.arange(T0, T1 + 3 * 86400, 60, dtype=np.int64); out = {}
    for s in syms:
        d = pd.read_parquet(f"{P3.DATA}/{s}_M1_rates.parquet", columns=["t", "bc", "ac"]).sort_values("t").drop_duplicates("t"); d = d[(d.t >= T0 - 86400) & (d.t < T1 + 4 * 86400)]
        i = np.clip(np.searchsorted(d.t.values, g, side="right") - 1, 0, len(d) - 1); out[s] = (d.bc.values[i], d.ac.values[i])
    return g, out


def pick(df, S, CAP):
    keep, open_ = [], []
    for r in df.itertuples():
        open_ = [(to, rk) for to, rk in open_ if to > r.t_in]
        if sum(rk for _, rk in open_) + S <= CAP: open_.append((r.t_out, S)); keep.append(r.Index)
    return df.loc[keep].reset_index(drop=True)


def episodes(tr, S, g, mk):
    in_s, out_s = tr.t_in.values.copy(), tr.t_out.values.copy(); side, ent, X = tr.side.values, tr.ent.values, tr.X.values; sym = tr.sym.values; q = S / X; pl = S * tr.R.values; eps = []; t_cur = float(T0); n = len(g)
    while t_cur < T1:
        a0 = int(np.searchsorted(g, t_cur)); found = None
        for span in (3, 10, 40, 400):
            b0 = min(int(np.searchsorted(g, t_cur + span * 86400)), n)
            if b0 - a0 < 5: break
            t_m = g[a0:b0]; P = np.zeros(b0 - a0); sel = np.nonzero((in_s >= t_cur) & (in_s < t_m[-1]) & (out_s > t_cur))[0]
            for j in sel:
                lo_ = max(int(np.searchsorted(t_m, in_s[j])), 0); hi_ = int(np.searchsorted(t_m, out_s[j])); bid, ask = mk[sym[j]]; mark = (bid if side[j] > 0 else ask)[a0:b0]
                P[lo_:hi_] += side[j] * (mark[lo_:hi_] - ent[j]) * q[j]; P[hi_:] += pl[j]
            hit = np.nonzero((P >= UP) | (P <= -DN))[0]
            if len(hit): found = (int(hit[0]), t_m, P, sel, a0); break
            if b0 >= n: break
        if found is None: break
        i, t_m, P, sel, a0 = found; tmi = int(t_m[i])
        for j in sel:
            if in_s[j] <= tmi < out_s[j]:
                bid, ask = mk[sym[j]]; m = (bid if side[j] > 0 else ask)[a0 + i]; pl[j] = side[j] * (m - ent[j]) * q[j]; out_s[j] = tmi
        eps.append(dict(start=t_cur, end=tmi, res=1 if P[i] >= UP else -1, pnl=float(P[i]), n_open=int(sum(1 for j in sel if in_s[j] <= tmi), ), n_sym=len(set(sym[j] for j in sel if in_s[j] <= tmi < out_s[j] + 1)))); t_cur = tmi + 60.0
    return pd.DataFrame(eps)


def main():
    df = trades_val(); g, mk = grids(sorted(df.sym.unique()))
    for S, CAP in ((250, 1500), (500, 1500), (500, 3000), (1000, 3000)):
        tr = pick(df, S, CAP); e = episodes(tr, S, g, mk)
        if len(e) == 0: print(f"S={S} CAP={CAP}: no closed episode"); continue
        e["hours"] = (e.end - e.start) / 3600.0; w = (e.res == 1).sum(); print(f"stop-risk {S:4d} / open-risk cap {CAP}: trades taken {len(tr)} | closed episodes {len(e)} | +2000 {w} ({100 * w / len(e):.0f}%) -1500 {len(e) - w} | median length {e.hours.median():.0f} h | net {e.pnl.sum():+,.0f} | symbols open at the barrier: median {e.n_sym.median():.0f} max {e.n_sym.max()}", flush=True)
        steps = np.where(e.res.values > 0, UP, -DN); out = []
        for k in range(len(steps)):
            c = 0.0
            for j in range(k, len(steps)):
                c += steps[j]
                if c >= 8000: out.append(("pass", (e.end.values[j] - e.start.values[k]) / 86400)); break
                if c <= -8000: out.append(("breach", (e.end.values[j] - e.start.values[k]) / 86400)); break
        if out:
            o = pd.DataFrame(out, columns=["r", "d"]); print(f"      from every start in 2025: {len(o)} resolved | pass {100 * (o.r == 'pass').mean():.0f}% breach {100 * (o.r == 'breach').mean():.0f}% | calendar days to pass: median {o[o.r == 'pass'].d.median():.0f}")
        e.to_csv(f"D:/finance/si_ledgers/FX_EPISODES_S{S}_CAP{CAP}.csv", index=False)


if __name__ == "__main__":
    main()
