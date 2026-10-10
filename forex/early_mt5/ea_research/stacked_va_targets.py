"""Family G-T: target study on the stacked-value-area entries, as registered in PREREG_STACKED_VA_TARGETS.md.
   python -m mt5broker.ea_research.stacked_va_targets --dev | --holdout"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.ea_research import stacked_va as G

HERE = Path(__file__).resolve().parent
STATE = HERE / "STACKED_VA_TARGETS_STATE.json"
CACHE = Path("D:/finance/tmp/stacked_va_targets.parquet")
TARGETS = ("T1", "T2", "T3", "T4", "T5", "T6", "T7")


def trades_for(m):
    d = G.load(m); D = G.profiles(d); days = D.index.to_numpy(); t = d.t.to_numpy(); out = []
    D["r5"] = D.c.shift(1) / D.c.shift(6) - 1.0; D["A"] = ((D.h - D.l) / D.c).rolling(20).mean().shift(1)
    hb = d.t // 3600; H = d.groupby(hb).agg(o=("mc", "first"), h=("mc", "max"), l=("mc", "min"), c=("mc", "last")); H["start"] = H.index * 3600; H["day"] = H.start // 86400; H["hc"] = ((H.start + 3600) % 86400) // 3600
    Hd = {k: v for k, v in H.groupby("day")}
    ah, al, ao, bh, bl, bo, ac, bc = (d[k].to_numpy() for k in ("ah", "al", "ao", "bh", "bl", "bo", "ac", "bc"))
    for k in range(3, len(days)):
        day = days[k]; p3 = D.iloc[k - 3:k]
        if p3[["poc", "val", "vah"]].isna().any().any() or day not in Hd: continue
        if not (p3.val.max() < p3.vah.min()) or (p3.poc.max() - p3.poc.min()) > 0.5 * (p3.vah - p3.val).mean(): continue
        zt, zb, mag = p3.vah.max(), p3.val.min(), p3.poc.mean(); prev = D.iloc[k - 1]
        for _, b in Hd[day].iterrows():
            if not (2 <= b.hc <= 21): continue
            rng = b.h - b.l
            if rng <= 0: continue
            side = -1 if (b.h > zt and b.c < zt and (b.h - max(b.o, b.c)) >= 0.5 * rng) else (1 if (b.l < zb and b.c > zb and (min(b.o, b.c) - b.l) >= 0.5 * rng) else 0)
            if side == 0: continue
            i0 = int(np.searchsorted(t, b.start + 3600 + 120))
            if i0 >= len(t) or t[i0] > b.start + 3600 + 420 or t[i0] // 86400 != day: break
            e = bo[i0] if side < 0 else ao[i0]; S = b.h * (1 + 2e-4) if side < 0 else b.l * (1 - 2e-4); R = (S - e) * -side
            if R <= 0: break
            lv = {"T1": e - side * -1 * 1.0 * R if False else e + side * 1.0 * R, "T2": e + side * 1.5 * R, "T3": e + side * 2.0 * R, "T4": e + side * 3.0 * R, "T5": mag, "T6": zb if side < 0 else zt, "T7": prev.l if side < 0 else prev.h}
            end = day * 86400 + 22 * 3600 + 55 * 60; j1 = max(i0 + 1, int(np.searchsorted(t, end, side="right"))); res = {}; mfe = 0.0
            hit_stop = None
            for j in range(i0, j1):
                stop_now = (ah[j] >= S) if side < 0 else (bl[j] <= S)
                if stop_now: hit_stop = j; break
                fav = (e - al[j]) if side < 0 else (bh[j] - e); mfe = max(mfe, fav / R)
                for nm, L in lv.items():
                    if nm in res: continue
                    if (L - e) * side <= 0: res[nm] = None; continue
                    if (side < 0 and al[j] <= L) or (side > 0 and bh[j] >= L): res[nm] = (L - e) * side / R
            if hit_stop is not None: stop_r = ((e - max(S, ao[hit_stop])) if side < 0 else (min(S, bo[hit_stop]) - e)) / R
            else: jj = j1 - 1; tx = ((e - ac[jj]) if side < 0 else (bc[jj] - e)) / R
            row = dict(mkt=m, date=pd.Timestamp(day * 86400, unit="s"), side=side, mfe=mfe, stopped=hit_stop is not None,
                       trend_ok=bool((abs(D.at[day, "r5"]) < D.at[day, "A"]) or (np.sign(D.at[day, "r5"]) == side)) if np.isfinite(D.at[day, "r5"]) and np.isfinite(D.at[day, "A"]) else False)
            for nm, L in lv.items():
                if (L - e) * side <= 0: row[nm] = np.nan
                elif res.get(nm) is not None: row[nm] = res[nm]
                else: row[nm] = stop_r if hit_stop is not None else tx
            out.append(row); break
    return pd.DataFrame(out)


def build():
    if CACHE.exists(): return pd.read_parquet(CACHE)
    T = pd.concat([trades_for(m) for m in G.FX + G.IDX], ignore_index=True); T.to_parquet(CACHE); return T


def st(x):
    x = x.dropna(); n = len(x)
    return dict(n=n, mean=float(x.mean()), t=float(x.mean() / (x.std(ddof=1) / np.sqrt(n))) if n > 2 else np.nan, win=float((x > 0).mean()), pf=float(x[x > 0].sum() / -x[x < 0].sum()) if (x < 0).any() else np.nan)


def dev():
    T = build(); res = {}
    for es, X in (("G1", T[T.trend_ok]), ("G2", T)):
        d, v = G.sl(X, G.PER["DEV"]), G.sl(X, G.PER["VAL"])
        print(f"== entries {es}: DEV {len(d)} trades | max favourable excursion before the stop (R): median {d.mfe.median():.2f}, P(>=1R) {100*(d.mfe >= 1).mean():.0f}%, P(>=2R) {100*(d.mfe >= 2).mean():.0f}%, P(>=3R) {100*(d.mfe >= 3).mean():.0f}% | stopped {100*d.stopped.mean():.0f}%")
        best = None
        for nm in TARGETS:
            a, b = st(d[nm]), st(v[nm])
            print(f"   {nm}: DEV n {a['n']:4d} win {100*a['win']:4.1f}% mean {a['mean']:+.3f} R PF {a['pf']:.2f} t {a['t']:+.2f} | VAL n {b['n']:4d} win {100*b['win']:4.1f}% mean {b['mean']:+.3f} R PF {b['pf']:.2f}")
            with open(G.LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},stacked_va_targets,{es}-{nm},DEV,,{a['n']},,{a['mean']:.4f},{a['pf']:.3f},{a['t']:.2f},{a['win']:.3f},VAL mean {b['mean']:+.3f}\n")
            if best is None or a["mean"] > best[1]["mean"]: best = (nm, a, b)
        ok = best[1]["t"] >= 2.7 and best[1]["mean"] > 0 and best[1]["n"] >= 200 and best[2]["mean"] > 0; res[es] = dict(target=best[0], passed=bool(ok))
        print(f"   best DEV target {best[0]}: accepted for the hold-out = {ok}")
    STATE.write_text(json.dumps(res))


def holdout():
    res = json.loads(STATE.read_text()); T = None
    for es, r in res.items():
        if not r["passed"]: print(f"{es}: not accepted, hold-out stays closed"); continue
        T = T if T is not None else pd.concat([trades_for(m) for m in G.FX + G.IDX], ignore_index=True)
        X = T[T.trend_ok] if es == "G1" else T; h = st(G.sl(X, G.PER["HOLD"])[r["target"]]); print(f"{es} {r['target']} HOLD 2026: n {h['n']} win {100*h['win']:.1f}% mean {h['mean']:+.3f} R t {h['t']:+.2f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dev", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    if a.dev: dev()
    if a.holdout: holdout()
