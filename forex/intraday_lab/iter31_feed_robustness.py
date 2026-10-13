"""Iteration 31 (pre-registered in intraday_lab/PREREG.md): is the SDB edge independent of the price feed?
   python -m forex.intraday_lab.iter31_feed_robustness --dry-run     (counts only)
   python -m forex.intraday_lab.iter31_feed_robustness               (the pre-registered run)"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from forex.forward_test import config
from forex.intraday_lab import sdb

ROOT = Path(__file__).resolve().parents[2]
GC = ROOT / "futures" / "data" / "databento" / "futures_GC.F_1m.parquet"
HALF = 0.085          # half of MT5 XAUUSD's median spread (17 points x 0.01)
OUT = Path("D:/finance/scratch/lab")


def gc_m1():
    g = pd.read_parquet(GC)
    ny = g.ts.dt.tz_convert("America/New_York").dt.tz_localize(None) + pd.Timedelta(hours=7)        # MT5 broker server clock
    t = ((ny - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)).values.astype(np.int64)
    o, h, l, c = (g[k].values.astype(np.float64) for k in ("open", "high", "low", "close"))
    return {"bo": o - HALF, "bh": h - HALF, "bl": l - HALF, "bc": c - HALF, "ao": o + HALF, "ah": h + HALF, "al": l + HALF, "ac": c + HALF, "t": t}


def run(m1, start, end):
    t = sdb.simulate("XAUUSD", m1, start=start, end=end, **config.RULE)
    if len(t):
        t["when"] = pd.to_datetime(t.t_entry, unit="s")
    return t


def stat(r):
    r = np.asarray(r, dtype=float); n = len(r)
    if n < 3:
        return dict(n=n, mean=np.nan, t=np.nan, pf=np.nan)
    pf = r[r > 0].sum() / -r[r < 0].sum() if (r < 0).any() else np.inf
    return dict(n=n, mean=r.mean(), t=r.mean() / (r.std(ddof=1) / np.sqrt(n)), pf=pf)


def fmt(s):
    return f"n {s['n']:4d}  mean R {s['mean']:+.3f}  t {s['t']:+.2f}  PF {s['pf']:.2f}"


def stress(m1, spread_k=1.0, noise=0.0, seed=0):
    x = {k: v.copy() for k, v in m1.items()}
    if spread_k != 1.0:
        for a, b in (("ao", "bo"), ("ah", "bh"), ("al", "bl"), ("ac", "bc")):
            x[a] = x[b] + (x[a] - x[b]) * spread_k
    if noise > 0:
        n = np.random.default_rng(seed).normal(0.0, noise, len(x["t"]))
        for k in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"):
            x[k] = x[k] + n
    return x


def main():
    dry = "--dry-run" in sys.argv
    gc = gc_m1()
    print(f"GC minutes {len(gc['t']):,}, {pd.to_datetime(gc['t'][0], unit='s')} .. {pd.to_datetime(gc['t'][-1], unit='s')} (server clock)", flush=True)
    full = run(gc, "2019-06-19", "2026-09-25")
    if dry:
        print("GC SDB trade counts by entry year:", full.when.dt.year.value_counts().sort_index().to_dict(), "| total", len(full))
        ft = run(sdb.load_m1("XAUUSD"), "2021-10-01", "2026-10-02"); print("MT5 XAUUSD trades:", len(ft))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    pre = full[full.when < "2021-10-01"]; ov = full[full.when >= "2021-10-01"]
    print("== (A) INDEPENDENT FEED: Databento GC front month, MT5 broker server clock, spread 0.17 USD, no swap")
    print("GC FULL   ", fmt(stat(full.R))); print("GC OVERLAP", fmt(stat(ov.R))); print("GC PRE    ", fmt(stat(pre.R)))
    print("GC by year:", {int(y): round(float(g.R.mean()), 3) for y, g in full.groupby(full.when.dt.year)}, "| trades a month", round(len(full) / ((full.when.max() - full.when.min()).days / 30.4), 1))
    fm = sdb.load_m1("XAUUSD"); ft = run(fm, "2021-10-01", "2026-10-02")
    print("MT5 XAUUSD", fmt(stat(ft.R)))
    ge = ov.when.values; gside = ov.side.values; matched = 0
    for w, s in zip(ft.when.values, ft.side.values):
        d = np.abs((ge - w) / np.timedelta64(1, "h")); matched += bool(((gside == s) & (d <= 24)).any())
    share = matched / len(ft); print(f"MT5 broker trades with a same-side GC trade within 24 h: {matched} of {len(ft)} = {share * 100:.0f}%")
    sa = stat(ov.R)
    se = np.sqrt(ov.R.var(ddof=1) / len(ov) + ft.R.var(ddof=1) / len(ft)); d_ = sa["mean"] - stat(ft.R)["mean"]
    print(f"GC minus MT5 broker mean R: {d_:+.3f}  (95% interval {d_ - 1.96 * se:+.3f} .. {d_ + 1.96 * se:+.3f})")
    print("PASS A (feed independence):", bool(sa["mean"] > 0 and sa["t"] >= 2.0 and share >= 0.60), flush=True)
    print("== (B) STRESS on the MT5 broker feed (baseline above)")
    res = {}
    for k in (2.0, 3.0):
        res[f"spread x{k:g}"] = stat(run(stress(fm, spread_k=k), "2021-10-01", "2026-10-02").R); print(f"spread x{k:g}:", fmt(res[f'spread x{k:g}']), flush=True)
    for s in (0.5, 1.0, 2.0):
        rows = [stat(run(stress(fm, noise=s, seed=sd), "2021-10-01", "2026-10-02").R) for sd in (1, 2, 3)]
        res[f"noise {s}"] = dict(n=np.mean([x["n"] for x in rows]), mean=np.mean([x["mean"] for x in rows]), t=np.mean([x["t"] for x in rows]))
        print(f"noise {s} USD (3 seeds): n {res[f'noise {s}']['n']:.0f}  mean R {res[f'noise {s}']['mean']:+.3f}  t {res[f'noise {s}']['t']:+.2f}  per seed {[round(x['mean'], 3) for x in rows]}", flush=True)
    print("PASS B (robust to spread x2 and 1 USD noise):", bool(res["spread x2"]["mean"] > 0 and res["spread x2"]["t"] >= 2.0 and res["noise 1.0"]["mean"] > 0 and res["noise 1.0"]["t"] >= 2.0))
    full.to_csv(OUT / "iter31_gc_trades.csv", index=False)


if __name__ == "__main__":
    main()
