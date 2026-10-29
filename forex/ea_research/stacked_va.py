"""Family G: Griff's stacked value areas, exactly as registered in PREREG_STACKED_VA.md.
   python -m forex.ea_research.stacked_va --dry-run | --trials | --holdout"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5"
LEDGER = HERE / "LEDGER.csv"
STATE = HERE / "STACKED_VA_STATE.json"
CACHE = Path("data/tmp/stacked_va_trades.parquet")
FX = ["AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD", "CADCHF", "CADJPY", "CHFJPY", "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD", "EURUSD", "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD", "GBPUSD",
      "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
IDX = ["SP", "NSDQ", "DOW", "DAX", "NIKKEI", "ASX"]
PER = {"DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}


def load(m):
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"]).sort_values("t").drop_duplicates("t")
    d = d[(d.bc > 0) & (d.ac >= d.bc) & (d.ao >= d.bo)].reset_index(drop=True); d["mc"] = (d.bc + d.ac) / 2; d["day"] = d.t // 86400
    return d[pd.to_datetime(d.day * 86400, unit="s").dt.dayofweek < 5].reset_index(drop=True)


def profiles(d):
    g = d.groupby("day"); D = pd.DataFrame({"o": g.mc.first(), "h": g.mc.max(), "l": g.mc.min(), "c": g.mc.last(), "n": g.size()})
    D["w"] = D.c.shift(1) * 1e-4; rows = {}
    for day, x in g:
        w = D.at[day, "w"]
        if not np.isfinite(w) or len(x) < 300: continue
        b = np.floor(x.mc.to_numpy() / w).astype(np.int64); u, cnt = np.unique(b, return_counts=True); i = int(np.argmax(cnt)); lo = hi = i; tot = cnt.sum(); acc = cnt[i]
        while acc < 0.7 * tot:
            left = cnt[lo - 1] if lo > 0 else -1; right = cnt[hi + 1] if hi < len(cnt) - 1 else -1
            if right >= left: hi += 1; acc += cnt[hi]
            else: lo -= 1; acc += cnt[lo]
        rows[day] = (u[i] * w + w / 2, u[lo] * w, (u[hi] + 1) * w)
    P = pd.DataFrame.from_dict(rows, orient="index", columns=["poc", "val", "vah"]); return D.join(P)


def trades_for(m, dry=False):
    d = load(m); D = profiles(d); days = D.index.to_numpy(); t = d.t.to_numpy(); out = []
    D["r5"] = D.c.shift(1) / D.c.shift(6) - 1.0; D["A"] = ((D.h - D.l) / D.c).rolling(20).mean().shift(1)
    hb = d.t // 3600; H = d.groupby(hb).agg(T=("t", "first"), o=("mc", "first"), h=("mc", "max"), l=("mc", "min"), c=("mc", "last"))
    H["start"] = H.index * 3600; H["day"] = H.start // 86400; H["hc"] = ((H.start + 3600) % 86400) // 3600
    Hd = {k: v for k, v in H.groupby("day")}; nsig = 0
    for k in range(3, len(days)):
        day = days[k]; p3 = D.iloc[k - 3:k]
        if p3[["poc", "val", "vah"]].isna().any().any() or day not in Hd or (days[k - 1] != day - 1 and pd.Timestamp(day * 86400, unit="s").dayofweek != 0): continue
        if not (p3.val.max() < p3.vah.min()): continue
        if (p3.poc.max() - p3.poc.min()) > 0.5 * (p3.vah - p3.val).mean(): continue
        zt, zb = p3.vah.max(), p3.val.min(); prev = D.iloc[k - 1]
        for _, b in Hd[day].iterrows():
            if not (2 <= b.hc <= 21): continue
            rng = b.h - b.l
            if rng <= 0: continue
            side = 0
            if b.h > zt and b.c < zt and (b.h - max(b.o, b.c)) >= 0.5 * rng: side = -1
            elif b.l < zb and b.c > zb and (min(b.o, b.c) - b.l) >= 0.5 * rng: side = 1
            if side == 0: continue
            nsig += 1
            if dry: break
            i0 = int(np.searchsorted(t, b.start + 3600 + 120))
            if i0 >= len(t) or t[i0] > b.start + 3600 + 420 or t[i0] // 86400 != day: break
            if side < 0: e = d.bo.iat[i0]; S = b.h * (1 + 2e-4); TP = prev.l; R = S - e; ok = R > 0 and (e - TP) >= R
            else: e = d.ao.iat[i0]; S = b.l * (1 - 2e-4); TP = prev.h; R = e - S; ok = R > 0 and (TP - e) >= R
            if not ok: break
            end = day * 86400 + 22 * 3600 + 55 * 60; j1 = int(np.searchsorted(t, end, side="right")); res = None
            for j in range(i0, max(i0 + 1, j1)):
                if side < 0:
                    if d.ah.iat[j] >= S: res = (e - max(S, d.ao.iat[j])) / R, "stop"; break
                    if d.al.iat[j] <= TP: res = (e - TP) / R, "tp"; break
                else:
                    if d.bl.iat[j] <= S: res = (min(S, d.bo.iat[j]) - e) / R, "stop"; break
                    if d.bh.iat[j] >= TP: res = (TP - e) / R, "tp"; break
            if res is None:
                j = max(i0, j1 - 1); xp = d.ac.iat[j] if side < 0 else d.bc.iat[j]; res = ((e - xp) if side < 0 else (xp - e)) / R, "time"
            trend_ok = (abs(D.at[day, "r5"]) < D.at[day, "A"]) or (np.sign(D.at[day, "r5"]) == side) if np.isfinite(D.at[day, "r5"]) and np.isfinite(D.at[day, "A"]) else False
            out.append(dict(mkt=m, date=pd.Timestamp(day * 86400, unit="s"), side=side, r=res[0], why=res[1], trend_ok=bool(trend_ok), stop_bp=R / e * 1e4, tp_mult=abs(TP - e) / R))
            break
    return (pd.DataFrame(out), nsig, len(days)) if not dry else (nsig, len(days), int(((D.val.shift(1).rolling(3).max() < D.vah.shift(1).rolling(3).min())).sum()))


def stats(X):
    n = len(X)
    if n < 5: return dict(n=n, mean=np.nan, t=np.nan, win=np.nan, pf=np.nan)
    w, l = X.r[X.r > 0].sum(), -X.r[X.r < 0].sum()
    return dict(n=n, mean=float(X.r.mean()), t=float(X.r.mean() / (X.r.std(ddof=1) / np.sqrt(n))), win=float((X.r > 0).mean()), pf=float(w / l) if l > 0 else np.nan)


def sl(T, p): return T[(T.date >= p[0]) & (T.date <= p[1])]


def run(hold=False):
    if CACHE.exists(): T = pd.read_parquet(CACHE)
    else:
        T = pd.concat([trades_for(m)[0] for m in FX + IDX], ignore_index=True); T.to_parquet(CACHE)
    res = {}
    for tr, X in (("G1", T[T.trend_ok]), ("G2", T)):
        pers = ("DEV", "VAL") + (("HOLD",) if hold else ())
        if hold and not json.loads(STATE.read_text()).get(tr, False): continue
        for p in pers:
            s = stats(sl(X, PER[p])); print(f"{tr} {p}: trades {s['n']:4d} | win {100*s['win']:4.1f}% | mean {s['mean']:+.3f} R | PF {s['pf']:.2f} | t {s['t']:+.2f}")
            with open(LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},stacked_va,{tr},{p},,{s['n']},,{s['mean']:.4f},{s['pf']:.3f},{s['t']:.2f},{s['win']:.3f},\n")
            if p == "DEV": dv = s
            if p == "VAL": vv = s
        if not hold:
            res[tr] = bool(dv["n"] >= 200 and dv["mean"] > 0 and dv["t"] >= 2.24 and vv["mean"] > 0); print(f"   {tr} acceptance 1-2: {res[tr]}")
            Y = sl(X, ("2022-01-01", "2025-12-31")); print("   by class (DEV+VAL):", {c: (round(float(g.r.mean()), 3), len(g)) for c, g in Y.groupby(np.where(Y.mkt.isin(IDX), "index", "FX"))}, "| exits:", Y.why.value_counts(normalize=True).round(2).to_dict(), "| trades/month:", round(len(Y) / 48, 1), "| median stop", round(float(Y.stop_bp.median()), 1), "bp, median target", round(float(Y.tp_mult.median()), 2), "R")
            print("   best/worst markets (DEV+VAL mean R, n>=15):", Y.groupby("mkt").r.agg(["mean", "size"]).query("size>=15").sort_values("mean").round(3).iloc[[0, 1, 2, -3, -2, -1]].to_dict("index"))
    if not hold: STATE.write_text(json.dumps(res))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--trials", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    if a.dry_run:
        for m in ("AUDUSD", "EURUSD", "SP"):
            d = load(m); D = profiles(d); r = D.iloc[-5]; print(f"{m}: days {len(D)} | sample day POC {r.poc:.5f} VA {r.val:.5f}-{r.vah:.5f} (day range {r.l:.5f}-{r.h:.5f}) | mean VA width / day range {((D.vah - D.val) / (D.h - D.l)).mean():.2f}")
            nsig, nd, nstack = trades_for(m, dry=True); print(f"   stacked-overlap days {nstack} of {nd}; days with a signal (all filters, first per day) {nsig}")
        print("no P&L computed")
    if a.trials: run()
    if a.holdout: run(True)
