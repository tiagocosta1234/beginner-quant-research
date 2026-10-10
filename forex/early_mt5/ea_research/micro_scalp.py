"""Our own GoldenShot-style micro-scalp, exactly as registered in PREREG_MICRO_SCALP.md (the trader 2026-10-09: "(original wording omitted)").
   python -m mt5broker.ea_research.micro_scalp --build | --trials
--build: for every Monday-Thursday cached tick day, a candidate every 120 s inside the entry windows, both directions, outcome under the fixed exit geometry (stop 20, target 4, trailing from +1.2 at 0.6 distance in 0.3 steps, 30-minute cap, entry latency 300 ms), features from MT5 M1 bars. --trials: S1 logistic, S2 gradient boosting, S3 hand rule; DEV 2025-10..2026-03, VAL 2026-04..2026-09."""
from __future__ import annotations

import datetime as dt
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5"
LEDGER = HERE / "LEDGER.csv"
CACHE = Path(r"D:\finance\scratch\microscalp_cache.parquet")
TICKS = sorted(glob.glob(r"D:\finance\scratch\ticks_gold\*.parquet"))
SL, TP, START, DIST, STEP, LAT, K_MS = 20.0, 4.0, 1.2, 0.6, 0.3, 300, 30 * 60 * 1000
WINDOWS = ((6 * 3600, 14 * 3600 + 20 * 60), (14 * 3600 + 35 * 60, 15 * 3600 + 20 * 60), (15 * 3600 + 45 * 60, 21 * 3600))
SPLIT = int(pd.Timestamp("2026-04-01").timestamp())


def features() -> pd.DataFrame:
    m = pd.read_parquet(DATA / "XAUUSD_M1_rates.parquet", columns=["t", "bo", "bh", "bl", "bc"]).sort_values("t").reset_index(drop=True); m["m"] = m.t // 60; m = m.drop_duplicates("m").set_index("m")
    full = np.arange(m.index.min(), m.index.max() + 1); m = m.reindex(full).ffill(); c, h, l = m.bc, m.bh, m.bl
    F = pd.DataFrame(index=m.index)
    for k in (1, 3, 5, 15, 30, 60):
        F[f"ret{k}"] = c - c.shift(k)
    F["range5"] = h.rolling(5).max() - l.rolling(5).min(); F["range30"] = h.rolling(30).max() - l.rolling(30).min(); F["pos30"] = (c - l.rolling(30).min()) / (F.range30 + 1e-9)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1); F["atr14"] = tr.rolling(14).mean(); e1, e2 = c.ewm(span=100, adjust=False).mean(), c.ewm(span=250, adjust=False).mean(); F["ema_gap"] = e1 - e2; F["ema_slope"] = F.ema_gap - F.ema_gap.shift(30)
    F["c_vs_ema100"] = c - e1; hour = ((m.t % 86400) / 3600).fillna(0); F["hs"], F["hc"] = np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24)
    return F.shift(1)                                                                  # the feature row of minute m uses only bars completed before minute m


def trade(ms, bid, ask, i0, side):
    t0 = ms[i0] + LAT; i = int(np.searchsorted(ms, t0)); j_end = int(np.searchsorted(ms, ms[i] + K_MS)) if i < len(ms) else len(ms)
    if i >= len(ms) - 5 or j_end - i < 50: return None
    entry, prof = (ask[i], bid[i + 1:j_end] - ask[i]) if side > 0 else (bid[i], bid[i] - ask[i + 1:j_end]); t = ms[i + 1:j_end]; mfe = np.maximum.accumulate(prof)
    lvl = np.where(mfe >= START, np.floor((mfe - DIST) / STEP) * STEP, -np.inf); lvl = np.maximum.accumulate(np.maximum(lvl, -SL)); k = np.clip(np.searchsorted(t, t - LAT, side="left"), 0, len(t) - 1)
    eff = np.maximum(np.where(t - LAT >= t[0], lvl[k], -SL), -SL); a = np.nonzero(prof >= TP)[0]; b = np.nonzero(prof <= eff)[0]; a = a[0] if len(a) else 10 ** 9; b = b[0] if len(b) else 10 ** 9
    if a == 10 ** 9 and b == 10 ** 9: return float(prof[-1]), int(t[-1])
    return (float(TP), int(t[a])) if a <= b else (float(prof[b]), int(t[b]))


def build():
    F = features(); rows = []; rng = np.random.default_rng(5)
    for f in TICKS:
        d = pd.read_parquet(f); ms, bid, ask = d.ms.to_numpy("int64"), d.bid.to_numpy("float64"), d.ask.to_numpy("float64")
        if pd.Timestamp(int(ms[0]) // 1000, unit="s").dayofweek > 3: continue
        day0 = (int(ms[0]) // 1000) // 86400 * 86400; cand = [day0 + s for a, b in WINDOWS for s in range(a, b - 1800, 120)]
        for ts in cand:
            i0 = int(np.searchsorted(ms, ts * 1000))
            if i0 >= len(ms) - 10 or abs(ms[i0] - ts * 1000) > 5000: continue
            mm = ts // 60; fr = F.loc[mm] if mm in F.index else None
            if fr is None or fr.isna().any(): continue
            for side in (1, -1):
                r = trade(ms, bid, ask, i0, side)
                if r is None: continue
                rows.append(dict(ts=ts, day=day0, side=side, spread=float(ask[i0] - bid[i0]), pnl=r[0], t_exit=r[1] // 1000, **fr.to_dict()))
        print(f, len(rows), flush=True)
    pd.DataFrame(rows).to_parquet(CACHE); print("saved", len(rows))


def tstat(x):
    x = np.asarray(x, float)
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")


def evaluate(D: pd.DataFrame, take: np.ndarray, label: str, extra_cost=0.0):
    X = D[take].sort_values("ts"); busy = 0; keep = []
    for _, r in X.iterrows():                                                              # one position at a time
        if r.ts >= busy: keep.append(r); busy = r.t_exit
    X = pd.DataFrame(keep)
    if not len(X): return dict(n=0)
    p = X.pnl.to_numpy() - extra_cost; w, l_ = p[p > 0].sum(), -p[p <= 0].sum(); day = pd.Series(p, index=X.day.to_numpy()).groupby(level=0).sum()
    return dict(n=len(X), mean=float(p.mean()), win=float((p > 0).mean()), pf=float(w / l_) if l_ > 0 else float("inf"), t=tstat(day.to_numpy()), per_day=len(X) / max(len(day), 1))


def fmt(tag, s):
    return f"{tag:34s} n {s['n']:5d}" + ("" if s["n"] == 0 else f" | mean {s['mean']:+.3f} USD/oz | win {100*s['win']:5.1f}% | PF {s['pf']:4.2f} | daily t {s['t']:+5.2f} | {s['per_day']:.1f} trades per active day")


def ledger(trial, period, s, note=""):
    if s["n"] == 0: return
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},micro_scalp,{trial},{period},,{s['n']},,{s['mean']:.4f},{s['pf']:.3f},{s['t']:.2f},{s['win']:.3f},{note}\n")


def trials():
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    D = pd.read_parquet(CACHE); feats = [c for c in D.columns if c not in ("ts", "day", "pnl", "t_exit")]; D["y"] = (D.pnl > 0).astype(int); dev, val = D[D.ts < SPLIT], D[D.ts >= SPLIT]
    print(f"candidates: DEV {len(dev)} VAL {len(val)} | random control (all candidates): DEV mean {dev.pnl.mean():+.3f} win {100*dev.y.mean():.1f}% | VAL mean {val.pnl.mean():+.3f} win {100*val.y.mean():.1f}%")
    rc = evaluate(val, np.ones(len(val), bool), "random"); print(fmt("VAL random control (sequential)", rc))
    models = {}
    sc = StandardScaler().fit(dev[feats]); lr = LogisticRegression(C=0.3, max_iter=500).fit(sc.transform(dev[feats]), dev.y); models["S1 logistic"] = lambda X: lr.predict_proba(sc.transform(X[feats]))[:, 1]
    gb = HistGradientBoostingClassifier(max_depth=3, max_iter=150, learning_rate=0.05, random_state=1).fit(dev[feats], dev.y); models["S2 boosting"] = lambda X: gb.predict_proba(X[feats])[:, 1]
    for name, fn in models.items():
        sd, sv = fn(dev), fn(val); best = None
        for q in (5, 10, 20):
            th = np.percentile(sd, 100 - q); rd = evaluate(dev, sd >= th, ""); rv = evaluate(val, sv >= th, "")
            print(fmt(f"{name} top {q}% DEV (in-sample)", rd)); print(fmt(f"{name} top {q}% VAL", rv)); ledger(name.split()[0], f"VAL_top{q}", rv, f"{name}; threshold from DEV")
            if best is None or (rd["n"] and rd["mean"] > best[1]): best = (q, rd["mean"], rv)
        print(f"   registered threshold (best DEV mean): top {best[0]}% -> VAL {fmt('', best[2])}")
        q = best[0]; th = np.percentile(sd, 100 - q); print(fmt(f"   cost stress +0.3 USD/oz", evaluate(val, sv >= th, "", 0.3)))
    # S3 hand rule: pullback inside an up / down move
    for nm, D_ in (("DEV", dev), ("VAL", val)):
        up = (D_.ret5 > 0) & (D_.c_vs_ema100 > 0) & (D_.ret3 < 0) & (D_.side == 1); dn = (D_.ret5 < 0) & (D_.c_vs_ema100 < 0) & (D_.ret3 > 0) & (D_.side == -1); s = evaluate(D_, (up | dn).to_numpy(), "")
        print(fmt(f"S3 hand rule {nm}", s)); ledger("S3", nm, s, "pullback in trend rule")


def main():
    if "--build" in sys.argv: build()
    if "--trials" in sys.argv: trials()


if __name__ == "__main__":
    main()
