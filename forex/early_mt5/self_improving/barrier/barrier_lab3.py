"""fx k=4 cell with stop 3 sigma / take-profit 4 sigma + concurrency (PREREG_BARRIER3.md).  python -m mt5broker.self_improving.barrier.barrier_lab3"""
import sys
ARGV = sys.argv[1:]
import numpy as np, pandas as pd
import xgboost as xgb
from mt5broker.self_improving import platform_v3 as P3
from mt5broker.self_improving.barrier import barrier_lab as B, barrier_lab2 as B2

B2.TP_MULT, B2.SL_MULT = 1.0, 0.75; WINR = B2.TP_MULT / B2.SL_MULT; CLS, K = "fx", 4.0


def fit(data, jobs=6):
    A, Bw, V = data["a"], data["b"], data["val"]; mdl = {}
    for nm in ("RL", "RS"):
        ia, ib = np.isfinite(A[nm]), np.isfinite(Bw[nm])
        m = xgb.XGBRegressor(n_estimators=400, max_depth=5, learning_rate=0.05, subsample=0.7, colsample_bytree=0.5, min_child_weight=200, reg_lambda=10.0, tree_method="hist", n_jobs=jobs, early_stopping_rounds=30, eval_metric="rmse")
        m.fit(A["X"][ia], A[nm][ia], eval_set=[(Bw["X"][ib], Bw[nm][ib])], verbose=False); mdl[nm] = m
    pB = [mdl[n].predict(Bw["X"]) for n in ("RL", "RS")]; pV = [mdl[n].predict(V["X"]) for n in ("RL", "RS")]
    bB, sB, RB = B.choose(Bw, *pB); gridB = (Bw["pos"] % B.GRID == 0) & np.isfinite(RB); best = None
    for q in B.QS:
        tau = float(np.quantile(bB[gridB], q)); sel = gridB & (bB >= tau)
        if sel.sum() >= B.N_MIN:
            mr = float(RB[sel].mean())
            if best is None or mr > best[1]: best = (tau, mr, q)
    if best is None: best = (float(np.quantile(bB[gridB], 0.5)), np.nan, 0.5)
    tau = best[0]; b_, s_, R_ = B.choose(V, *pV); st = B.stat(V, b_, s_, R_, tau); sel = (V["pos"] % B.GRID == 0) & np.isfinite(R_) & (b_ >= tau)
    r = R_[sel]; wins = int((r > WINR - 1e-9).sum()); loss = int((r < -1 + 1e-9).sum()); st["hit"] = wins / max(wins + loss, 1); st["B_meanR"] = best[1]
    return st, sel, s_, R_, V


def main():
    rows = []
    for pl in (121, 122, 123, None):
        data = B2.build_class(CLS, pl, K); st, sel, s_, R_, V = fit(data); ok = st["n"] >= 100 and st["cl"] >= 20 and st["meanR"] >= 0.20 and st["p"] < 0.05
        print(f"{'placebo ' + str(pl) if pl else 'REAL'}: B meanR {st['B_meanR']:+.3f} | VAL n={st['n']} cl={st['cl']} meanR {st['meanR']:+.3f} (stop units) hit {100 * st['hit']:.0f}% z={st['z']:.2f} p={st['p']:.4f} | floor passed={ok}", flush=True)
        if pl is None:
            names = [m for m in P3.CLASSES[CLS]["members"] if len(B2.D6.bars15(m)) > 40000]; t_in = V["t0"][sel]; hold = np.where(s_[sel] > 0, V["dur_l"][sel], V["dur_s"][sel]) * 3600.0
            df = pd.DataFrame(dict(sym=[names[i] for i in V["mkt"][sel]], side=s_[sel], R=R_[sel], t_in=t_in, t_out=t_in + hold)).dropna(); df.to_csv("D:/finance/si_ledgers/BARRIER3_fx_val_trades.csv", index=False)
            grid = np.arange(df.t_in.min(), df.t_out.max(), 3600.0); t_in_a, t_out_a = df.t_in.values, df.t_out.values; sym = df.sym.values
            cnt = np.array([((t_in_a <= g) & (t_out_a > g)).sum() for g in grid]); dist = np.array([len(set(sym[(t_in_a <= g) & (t_out_a > g)])) for g in grid]); act = cnt > 0
            print(f"\nTRADES {len(df)} in VAL | long share {100 * (df.side > 0).mean():.1f}% | median hold {np.median(hold) / 3600:.0f}h | mean R {df.R.mean():+.3f}")
            print(f"CONCURRENT open positions (hourly, whole year): mean {cnt.mean():.1f}, median {np.median(cnt):.0f}, p95 {np.percentile(cnt, 95):.0f}, max {cnt.max()} | when at least one is open: mean {cnt[act].mean():.1f}")
            print(f"DISTINCT symbols open at once: mean {dist.mean():.1f}, median {np.median(dist):.0f}, p95 {np.percentile(dist, 95):.0f}, max {dist.max()}")
            same = pd.Series(cnt - dist); print(f"extra positions on the same symbol (pyramiding): mean {same.mean():.1f}, p95 {np.percentile(same, 95):.0f}, max {same.max()}")
            # dollar view: every trade risks S dollars at the stop; cap the total open stop-risk at CAP; trades skipped (first come) when the cap is full
            for S, CAP in ((1500, 1500), (500, 1500), (250, 1500), (150, 1500), (100, 1500)):
                open_ = []; pnl = []; taken = 0
                for r in df.sort_values("t_in").itertuples():
                    open_ = [(to, rk) for to, rk in open_ if to > r.t_in]
                    if sum(rk for _, rk in open_) + S <= CAP: open_.append((r.t_out, S)); pnl.append((r.t_out, S * r.R)); taken += 1
                p = pd.DataFrame(pnl, columns=["t", "usd"]).sort_values("t"); day = (p.t // 86400).astype(int); dd = p.groupby(day).usd.sum()
                print(f"stop-risk {S:4d} USD per trade, total open risk cap {CAP}: trades taken {taken}/{len(df)} | total {p.usd.sum():+,.0f} USD | days with P&L {len(dd)} | best day {dd.max():+,.0f} worst day {dd.min():+,.0f} | days >= +2000: {(dd >= 2000).sum()}, days <= -1500: {(dd <= -1500).sum()}")


if __name__ == "__main__":
    main()
