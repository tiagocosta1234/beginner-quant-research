"""Ensemble of weak rules as one hypothesis (PREREG_ENSEMBLE.md).
   FF6_MT5ONLY=1 python -m forex.self_improving.ensemble.ens_lab [--placebo 81]"""
import sys
ARGV = sys.argv[1:]

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("FF6_MT5ONLY", "1")
import numpy as np
import pandas as pd
from scipy import stats

from forex.self_improving import platform_v3 as P3
from forex.self_improving.freeform import ff6_data as D, ff6_agent as A

LED = Path("D:/finance/si_ledgers"); HE = (4, 16, 96); CLS = tuple(P3.CLASSES); MAXM = 200; BONF = 0.05 / 12


def members(ledger, cls, H):
    a = pd.read_csv(ledger); a = a[(a.stage == "a") & (a.n >= 150) & (a.clusters >= 20) & (a.mean_bp >= 1.0) & (a.z >= 2.5)].copy()
    rules = [json.loads(x) for x in a.rule]; a["cls"] = [r["cls"] for r in rules]; a["H"] = [r["H"] for r in rules]; a["side"] = [r["side"] for r in rules]
    a["key"] = [(r["cls"], r["side"], r["H"], tuple(sorted(c[0] for c in r["conds"]))) for r in rules]; a["rule_obj"] = rules
    a = a[(a.cls == cls) & (a.H == H)].sort_values("z", ascending=False).drop_duplicates("key").head(MAXM); return list(a.rule_obj), list(a.z)


def votes(ev, st, cls, w, rules):
    win = getattr(st, w); v = np.zeros(len(win.X), np.float32); okh = ev.ok_hour(st, w, cls)
    for r in rules:
        m = okh.copy()
        for c in r["conds"]: m &= ev.mask(st, w, cls, c)
        v += r["side"] * m
    return v


def cluster(ex, week):
    n = len(ex)
    if n < 30: return n, 0, np.nan, 1.0
    m = ex.mean(); wk = week - week.min(); cnt = np.bincount(wk); res = np.bincount(wk, weights=ex - m); cl = int((cnt > 0).sum())
    if cl < 5: return n, cl, np.nan, 1.0
    se = np.sqrt((res ** 2).sum() * cl / (cl - 1)) / n
    if se == 0: return n, cl, np.nan, 1.0
    z = m / se; return n, cl, float(z), float(stats.t.sf(z, cl - 1))


def evaluate(ev, st, cls, w, vote, k, H):
    win = getattr(st, w); hi = D.HS.index(H); grid = ev.grid(st, w, cls, H); sel = grid & (np.abs(vote) >= k) & (vote != 0)
    Y = np.where(vote > 0, win.Yl[:, hi], win.Ys[:, hi]); g = win.Yg[:, hi].astype(np.float64); gs = np.where(vote > 0, g, 1.0 / (1.0 + g) - 1.0); ok = sel & np.isfinite(Y)
    if ok.sum() == 0: return dict(n=0, cl=0, net_bp=np.nan, z=np.nan, p=1.0)
    base = {}
    for s_ in (1, -1): base[s_] = ev.umean(cls, w, s_, hi)
    ex = gs[ok] - np.where(vote[ok] > 0, base[1][win.mkt[ok]], base[-1][win.mkt[ok]]); n, cl, z, p = cluster(ex, win.week[ok])
    return dict(n=int(n), cl=int(cl), net_bp=1e4 * float(Y[ok].mean()), z=z, p=p)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--placebo", type=int, default=None); a = ap.parse_args(ARGV)
    ledger = LED / (f"FF10_mt5pl{a.placebo}.csv" if a.placebo is not None else "FF10_mt5real.csv"); rows = []
    for cls in CLS:
        st = D.Stack(cls, a.placebo); ev = A.Evaluator({cls: st})
        for H in HE:
            rules, zs = members(ledger, cls, H)
            if len(rules) < 5: print(f"[{cls} H={H}] only {len(rules)} qualifying members: skipped"); rows.append(dict(cls=cls, H=H, members=len(rules), passB=False)); continue
            va = votes(ev, st, cls, "a", rules); nz = np.abs(va[va != 0]); k = float(np.quantile(nz, 0.9)) if len(nz) else 1.0
            ra = evaluate(ev, st, cls, "a", va, k, H); rb = evaluate(ev, st, cls, "b", votes(ev, st, cls, "b", rules), k, H)
            passB = bool(rb["n"] >= 100 and rb["cl"] >= 20 and rb["net_bp"] >= 3.0 and rb["p"] < BONF); rv = None
            if passB: rv = evaluate(ev, st, cls, "val", votes(ev, st, cls, "val", rules), k, H)
            rows.append(dict(cls=cls, H=H, members=len(rules), k=k, A_n=ra["n"], A_net=ra["net_bp"], A_z=ra["z"], B_n=rb["n"], B_cl=rb["cl"], B_net=rb["net_bp"], B_z=rb["z"], B_p=rb["p"], passB=passB, val=rv))
            print(f"[{cls} H={H}] members {len(rules)} k={k:.0f} | A n={ra['n']} net {ra['net_bp']:+.1f}bp z={ra['z']:.2f} | B n={rb['n']} cl={rb['cl']} net {rb['net_bp']:+.1f}bp z={rb['z']:.2f} p={rb['p']:.3f} | passB={passB}" + (f" | VAL {rv}" if rv else ""), flush=True)
        del st
    df = pd.DataFrame(rows); df.to_csv(LED / f"ENS_{'placebo' + str(a.placebo) if a.placebo is not None else 'real'}.csv", index=False)
    print(f"DONE: ensembles passing B {int(df.passB.sum())} of {len(df)} | best B z {pd.to_numeric(df.B_z, errors='coerce').max():.2f} | best B net {pd.to_numeric(df.B_net, errors='coerce').max():+.1f} bp")


if __name__ == "__main__":
    main()
