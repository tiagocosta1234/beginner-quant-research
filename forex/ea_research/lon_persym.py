"""LON_PERSYM (PREREG_LON_PERSYM.md): per-symbol London-open breakout choice on DEV, VAL / 2026 check, HistData 2020-21 out-of-time check.
   python -m forex.ea_research.lon_persym"""
import os

import numpy as np
import pandas as pd
from scipy.stats import norm

import forex.ea_research.orb11_entry as oe
import forex.ea_research.orb11_entry_oot as oo
from forex.ea_research.orb11 import PER

HD_OK = lambda s: os.path.exists(f"D:/finance/data_histdata/DAT_ASCII_{oo.HD.get(s, s)}_M1_2020.zip")


def london_spread(sym):
    d = pd.read_parquet(f"forex/data_mt5/{sym}_M1_rates.parquet")
    d = d[(d.t >= pd.Timestamp("2025-10-01").timestamp()) & (d.t < pd.Timestamp("2026-10-03").timestamp())]
    lt = pd.to_datetime(d.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("Europe/London")
    return float(np.median((d.ao - d.bo)[(lt.dt.hour >= 8) & (lt.dt.hour < 17)]))


def main():
    pd.set_option("display.width", 250)
    T = pd.read_parquet("D:/finance/si_ledgers/ORB11_ENTRY.parquet"); T = T[(T.sess == "LON") & (T.trig != "CTRL")].reset_index(drop=True)
    pm = {p: ((T.day >= a) & (T.day <= b)).to_numpy() for p, (a, b) in PER.items()}
    rows = []
    for mk, g in T.groupby("mkt"):
        best = None
        for tg in oe.TRIGS:
            for f in oe.FILTS:
                m = g.index[(g.trig == tg).to_numpy() & oe.fmask(g, f)]
                for x in ("r1", "rh"):
                    dv = m[pm["DEV"][m]]
                    if len(dv) < 50: continue
                    r = dict(mkt=mk, trig=tg, filt=f, exit=x, nDEV=len(dv), DEV=T.loc[dv, x].mean(), VAL=T.loc[m[pm["VAL"][m]], x].mean(),
                             Y26=T.loc[m[pm["Y26"][m]], x].mean(), nVAL=int(pm["VAL"][m].sum()), n26=int(pm["Y26"][m].sum()))
                    if best is None or r["DEV"] > best["DEV"]: best = r
        if best: rows.append(best)
    S = pd.DataFrame(rows); S["kept"] = (S.VAL > 0) & (S.Y26 > 0)
    print(f"1-2. DEV-best London rule per symbol ({len(S)}): DEV {S.DEV.mean():+.3f} -> 2025 {S.VAL.mean():+.3f} (positive {int((S.VAL > 0).sum())}) -> 2026 {S.Y26.mean():+.3f} (positive {int((S.Y26 > 0).sum())}); kept (both > 0): {int(S.kept.sum())}")
    print(S.sort_values("DEV", ascending=False)[["mkt", "trig", "filt", "exit", "nDEV", "DEV", "VAL", "Y26", "kept"]].round(3).to_string(index=False))
    K = S[S.kept].copy(); nk = max(len(K), 1); bar = norm.ppf(1 - 0.05 / nk)
    print(f"\n3. OUT OF TIME 2020-21 (HistData, today's MT5 London spread), {len(K)} kept rules, bar t >= {bar:.2f}, both years > 0:")
    out = []
    for r in K.itertuples():
        if r.mkt == "DOW" or not HD_OK(r.mkt):
            out.append(dict(mkt=r.mkt, note="no HistData series")); print(f"   {r.mkt}: no HistData series"); continue
        sp = london_spread(r.mkt); D = oo.load_hd(r.mkt, sp); oe.load = lambda s, e, D=D: D
        X = pd.DataFrame(oe.market((r.mkt, oe.END)), columns=oe.COLS); X = X[(X.sess == "LON") & (X.trig == r.trig)]
        X = X[oe.fmask(X, r.filt)]
        s = X[r.exit]; yrs = {y: round(v.mean(), 3) for y, v in s.groupby(X.day.dt.year)}; t = oe.tstat(s)
        ok = bool(len(s) > 20 and s.mean() > 0 and t >= bar and all(v > 0 for v in yrs.values()))
        out.append(dict(mkt=r.mkt, rule=f"{r.trig} {r.filt} {r.exit}", n=len(s), mean=s.mean(), t=t, years=yrs, passed=ok))
        print(f"   {r.mkt} {r.trig} {r.filt} {'1:1' if r.exit == 'r1' else 'hold'}: n {len(s)} {s.mean():+.3f} R, t {t:+.2f}, by year {yrs} -> {'PASS' if ok else 'fail'}  (spread {sp:.5g})")
    S.to_csv("D:/finance/si_ledgers/LON_PERSYM.csv", index=False); pd.DataFrame(out).to_csv("D:/finance/si_ledgers/LON_PERSYM_OOT.csv", index=False)
    print("passing out of time:", [o["mkt"] for o in out if o.get("passed")])


if __name__ == "__main__":
    main()
