"""Family VR: implied-vol regime vs the gold pair's daily P&L (PREREG_VOL_REGIME.md).   python -m mt5broker.ea_research.vol_regime (env VR=dry|run; clean_boot_lib rewrites sys.argv)"""
from __future__ import annotations
import os, sys
os.environ.setdefault("DA_Z", "1.5")
import numpy as np, pandas as pd
from scipy import stats
from mt5broker.ea_research import combo_grid as G

CB = "D:/finance/data_macro/cboe"
DEV = ("2022-01-03", "2024-12-31"); VAL = ("2025-01-01", "2025-12-31"); HOLD = ("2026-01-01", "2026-09-30")


def cboe(name, col):
    d = pd.read_csv(f"{CB}/{name}.csv"); d["date"] = pd.to_datetime(d["date"], format="%m/%d/%Y"); return d.set_index("date")[col].astype(float)


def features(days):
    gvz, v9, v3, sk = cboe("GVZ", "gvz"), cboe("VIX9D", "close"), cboe("VIX3M", "close"), cboe("SKEW", "skew")
    raw = {"F1_GVZ": gvz, "F2_VIX9D_VIX3M": v9 / v3, "F3_SKEW": sk}
    out = {}
    for k, s in raw.items():
        s = s.dropna(); idx = s.index.searchsorted(days, side="left") - 1          # last observation strictly before the day
        out[k] = pd.Series(np.where(idx >= 0, s.to_numpy()[np.clip(idx, 0, None)], np.nan), index=days)
    return pd.DataFrame(out)


def build():
    S = G.pair_series("FT", 1.5, 1.5, 1500.0); days = pd.to_datetime(S["days"] * 86400, unit="s")
    return pd.Series(S["V"], index=days), features(days)


def win(x, w): return x[(x.index >= w[0]) & (x.index <= w[1])]


def diff(V, F, thr, w):
    v, f = win(V, w), win(F, w); ok = f.notna(); v, f = v[ok], f[ok]
    hi, lo = v[f > thr], v[f <= thr]
    t = stats.ttest_ind(hi, lo, equal_var=False).statistic if len(hi) > 2 and len(lo) > 2 else np.nan
    return dict(n_hi=len(hi), n_lo=len(lo), mean_hi=hi.mean(), mean_lo=lo.mean(), diff=hi.mean() - lo.mean(), t=t)


if __name__ == "__main__":
    V, F = build()
    if os.environ.get("VR") == "dry":                                      # coverage only, no outcome statistic is printed
        print("days", len(V), V.index.min().date(), V.index.max().date())
        for k in F: print(k, "non-null", int(F[k].notna().sum()), "DEV median", round(win(F[k], DEV).median(), 3), "last", round(F[k].dropna().iloc[-1], 3))
    if os.environ.get("VR") == "run":
        rows = []
        for k in F:
            thr = win(F[k], DEV).median(); d, v = diff(V, F[k], thr, DEV), diff(V, F[k], thr, VAL)
            acc = bool(abs(d["t"]) >= 2.4 and np.sign(v["diff"]) == np.sign(d["diff"]) and abs(v["diff"]) >= 0.5 * abs(d["diff"]))
            row = dict(feature=k, thr=round(thr, 3), dev_diff=round(d["diff"]), dev_t=round(d["t"], 2), dev_hi=round(d["mean_hi"]), dev_lo=round(d["mean_lo"]),
                       val_diff=round(v["diff"]), val_t=round(v["t"], 2), accepted=acc)
            if acc:
                h = diff(V, F[k], thr, HOLD); row.update(hold_diff=round(h["diff"]), hold_t=round(h["t"], 2), PASS=bool(np.sign(h["diff"]) == np.sign(d["diff"])))
            rows.append(row)
        R = pd.DataFrame(rows); txt = R.to_string(index=False); print(txt)
        open(os.path.join(os.path.dirname(__file__), "VOL_REGIME_RESULT.txt"), "w").write(txt)
