"""Audit of the only cell above the placebo ceiling in BARRIER2 (fx, k=4): where do the VAL trades and the profit come from?  python -m forex.self_improving.barrier.audit_fx4"""
import sys
ARGV = sys.argv[1:]
import numpy as np, pandas as pd
import xgboost as xgb
from forex.self_improving import platform_v3 as P3
from forex.self_improving.barrier import barrier_lab as B, barrier_lab2 as B2

cls, k = "fx", 4.0; data = B2.build_class(cls, None, k); A, Bw, V = data["a"], data["b"], data["val"]; mdl = {}
for nm in ("RL", "RS"):
    ia, ib = np.isfinite(A[nm]), np.isfinite(Bw[nm])
    m = xgb.XGBRegressor(n_estimators=400, max_depth=5, learning_rate=0.05, subsample=0.7, colsample_bytree=0.5, min_child_weight=200, reg_lambda=10.0, tree_method="hist", n_jobs=6, early_stopping_rounds=30, eval_metric="rmse")
    m.fit(A["X"][ia], A[nm][ia], eval_set=[(Bw["X"][ib], Bw[nm][ib])], verbose=False); mdl[nm] = m
pB = [mdl[n].predict(Bw["X"]) for n in ("RL", "RS")]; pV = [mdl[n].predict(V["X"]) for n in ("RL", "RS")]
bB, sB, RB = B.choose(Bw, *pB); gridB = (Bw["pos"] % B.GRID == 0) & np.isfinite(RB); best = None
for q in B.QS:
    tau = float(np.quantile(bB[gridB], q)); sel = gridB & (bB >= tau)
    if sel.sum() >= B.N_MIN:
        mr = float(RB[sel].mean())
        if best is None or mr > best[1]: best = (tau, mr, q)
tau = best[0]; b_, s_, R_ = B.choose(V, *pV); sel = (V["pos"] % B.GRID == 0) & np.isfinite(R_) & (b_ >= tau)
names = list(P3.CLASSES[cls]["members"]); big = [m for m in names if len(B2.D6.bars15(m)) > 40000]
df = pd.DataFrame(dict(mkt=[big[i] for i in V["mkt"][sel]], side=s_[sel], R=R_[sel], week=V["week"][sel], hold=np.where(s_[sel] > 0, V["dur_l"][sel], V["dur_s"][sel])))
print(f"VAL trades {len(df)} mean R {df.R.mean():+.3f} hit {100 * (df.R == 1).sum() / max(((df.R == 1) | (df.R == -1)).sum(), 1):.0f}% median hold {df.hold.median():.0f}h")
g = df.groupby(["mkt", "side"]).R.agg(["count", "mean"]).round(3); print(g.sort_values("mean", ascending=False).to_string())
print("by side:", df.groupby("side").R.agg(["count", "mean"]).round(3).to_dict())
df["half"] = (df.week > df.week.median()); print("by half of 2025:", df.groupby("half").R.agg(["count", "mean"]).round(3).to_dict())
top = g["count"].sort_values(ascending=False); print("share of trades in the 3 busiest (market, side):", round(top.head(3).sum() / len(df), 2))
