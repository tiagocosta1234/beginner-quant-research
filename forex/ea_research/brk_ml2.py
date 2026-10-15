"""BRK-ML2 exactly as in PREREG_BRK_ML2.md: walk-forward XGBoost selection of the hour-map breakouts.
   python -m forex.ea_research.brk_ml2 --dry | (no flag) run"""
import sys

import numpy as np
import pandas as pd

from forex.ea_research.ict2 import nw_t

FEATS = ["c_crypto", "c_energy", "c_fx", "c_index", "c_metal", "h", "side", "wd", "dom", "lbox", "box_rel", "trail_mh", "trail_m", "trail_c", "crowd"]
FOLDS = ((2022, 2023), (2023, 2024), (2024, 2025), (2025, 2026))


def features(end_day=None):
    df = pd.read_parquet("D:/finance/si_ledgers/BRK_HOURS.parquet")
    if end_day is not None:
        df = df[df.day < end_day]
    df = df.sort_values("t_entry").reset_index(drop=True)
    for c in ("crypto", "energy", "fx", "index", "metal"):
        df[f"c_{c}"] = (df.c == c).astype(float)
    df["wd"] = df.day.dt.dayofweek
    mdays = df[["mkt", "day"]].drop_duplicates().sort_values(["mkt", "day"])
    mdays["dom"] = mdays.groupby([mdays.mkt, mdays.day.dt.to_period("M")]).cumcount() + 1
    df = df.merge(mdays, on=["mkt", "day"], how="left")
    df["lbox"] = np.log(df.box_sp.clip(lower=0.5, upper=3000))
    df = df.sort_values(["mkt", "h", "day"])
    g = df.groupby(["mkt", "h"])
    df["trail_mh"] = g.R.transform(lambda s: s.shift(1).rolling(60, min_periods=20).mean())
    df["box_rel"] = (df.box_sp / g.box_sp.transform(lambda s: s.shift(1).rolling(60, min_periods=20).median())).clip(0, 20)
    md = df.groupby(["mkt", "day"]).R.mean().rename("m_day").reset_index().sort_values(["mkt", "day"])
    md["trail_m"] = md.groupby("mkt").m_day.transform(lambda s: s.shift(1).rolling(20, min_periods=10).mean())
    cd = df.groupby(["c", "day"]).R.mean().rename("c_day").reset_index().sort_values(["c", "day"])
    cd["trail_c"] = cd.groupby("c").c_day.transform(lambda s: s.shift(1).rolling(20, min_periods=10).mean())
    df = df.merge(md[["mkt", "day", "trail_m"]], on=["mkt", "day"], how="left").merge(cd[["c", "day", "trail_c"]], on=["c", "day"], how="left")
    df = df.sort_values("t_entry")
    df["crowd"] = df.groupby(["c", "day", "h"]).t_entry.rank(method="min") - 1
    return df.reset_index(drop=True)


def dry():
    df = features()
    print("rows", len(df), "| feature NaN share:", df[FEATS].isna().mean().round(3).to_dict())
    print(df[FEATS + ["R"]].describe().T[["mean", "min", "max"]].round(3).to_string())
    x = df[(df.mkt == "EURUSD") & (df.day == "2024-06-12")].head(3)
    print("hand check EURUSD 2024-06-12:", x[["h", "side", "R", "trail_mh", "trail_m", "crowd", "dom", "box_rel"]].round(3).to_dict("records"))
    # causality: trailing features of a day must not change when later days are removed
    cut = pd.Timestamp("2024-03-13")
    cols = ["trail_mh", "trail_m", "trail_c", "box_rel", "crowd", "dom"]
    a = df[df.day < cut - pd.Timedelta(days=1)].set_index(["mkt", "h", "day"])[cols].sort_index()
    b = features(cut)
    b = b[b.day < cut - pd.Timedelta(days=1)].set_index(["mkt", "h", "day"])[cols].sort_index()
    ok = len(a) == len(b) and np.allclose(a.to_numpy(float), b.to_numpy(float), equal_nan=True)
    print("truncation:", "PASS" if ok else f"FAIL {len(a)} {len(b)}")


def run():
    from xgboost import XGBRegressor
    df = features()
    df["yr"] = df.day.dt.year
    out = []
    for tr_last, te in FOLDS:
        tr, ts = df[df.yr <= tr_last], df[df.yr == te].copy()
        mdl = XGBRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, n_jobs=12, random_state=1)
        mdl.fit(tr[FEATS].to_numpy(float), tr.R.clip(-1.5, 4).to_numpy())
        thr = np.quantile(mdl.predict(tr[FEATS].to_numpy(float)), 0.9)
        ts["pred"] = mdl.predict(ts[FEATS].to_numpy(float))
        ts["sel"] = ts.pred >= thr
        out.append(ts)
        imp = pd.Series(mdl.feature_importances_, index=FEATS).sort_values(ascending=False).head(5).round(3).to_dict()
        print(f"fold train<= {tr_last} -> {te}: selected {ts.sel.mean():.1%} of {len(ts)} | top features {imp}")
    T = pd.concat(out)
    T[["mkt", "day", "h", "side", "R", "pred", "sel", "yr"]].to_parquet("D:/finance/si_ledgers/BRK_ML2.parquet")
    r = {}
    for lab, yrs in (("DEV", (2023, 2024)), ("VAL", (2025,)), ("2026", (2026,))):
        s = T[T.yr.isin(yrs)]
        on, off = s[s.sel], s[~s.sel]
        r[lab] = (len(on), on.R.mean(), nw_t(on.groupby("day").R.mean().to_numpy()), off.R.mean())
    gt = [r["DEV"][1] >= 0.05 and r["DEV"][2] >= 1.96, r["VAL"][1] > 0 and r["VAL"][2] >= 1.65, r["DEV"][1] - r["DEV"][3] >= 0.05 and r["VAL"][1] - r["VAL"][3] >= 0.05]
    print("S1 top decile: " + " | ".join(f"{k} n{v[0]} {v[1]:+.3f} (t {v[2]:+.2f}) unselected {v[3]:+.3f}" for k, v in r.items()) + f" | gates {''.join('Y' if z else 'n' for z in gt)} PASS {all(gt)}")
    s = T[T.sel]
    print("selected by class (DEV / VAL / 2026):", {c: "/".join(f"{x[x.yr.isin(y)].R.mean():+.3f}" for y in ((2023, 2024), (2025,), (2026,))) for c, x in s.assign(c=s.mkt.map(__import__('forex.ea_research.analog', fromlist=['mclass']).mclass)).groupby("c")})
    T["dec"] = T.groupby("yr").pred.transform(lambda p: pd.qcut(p.rank(method="first"), 10, labels=False))
    print("mean R by prediction decile (rows test year):")
    print(T.pivot_table(index="yr", columns="dec", values="R", aggfunc="mean").round(3).to_string())


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
