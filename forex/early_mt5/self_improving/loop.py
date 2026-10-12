"""The self-improving loop (PREREG_SELF_IMPROVING.md).
   python -m mt5broker.self_improving.loop --gens 6 --pop 250 --seed 1 [--placebo 7]
Append-only ledger (SI_LEDGER.csv, or SI_PLACEBO_LEDGER_<seed>.csv): one DEV row per spec, one VAL row for a spec the first time it passes S1. HOLD is never read here."""
from __future__ import annotations

import sys
ARGV = sys.argv[1:]          # legacy mt5broker modules overwrite sys.argv at import time: keep ours first

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from mt5broker.self_improving import grammar as G, platform_pit as PIT

HERE = Path(__file__).resolve().parent
COLS = ["when", "stage", "gen", "hash", "spec", "n", "days", "mean_bp", "t", "p"]
N_MIN, DAYS_MIN, BP_MIN, Q = 80, 40, 3.0, 0.10
VAL_N_MIN, VAL_P = 25, 0.20


def window_stats(T, lo_hi):
    if len(T) == 0: return dict(n=0, days=0, mean_bp=np.nan, t=np.nan, p=1.0)
    w = T[(T.date >= pd.Timestamp(lo_hi[0])) & (T.date <= pd.Timestamp(lo_hi[1]))]
    if len(w) == 0: return dict(n=0, days=0, mean_bp=np.nan, t=np.nan, p=1.0)
    d = w.groupby("date").ret.mean(); n = len(d)
    if n < 3 or d.std(ddof=1) == 0: return dict(n=len(w), days=n, mean_bp=1e4 * w.ret.mean(), t=np.nan, p=1.0)
    t = d.mean() / (d.std(ddof=1) / np.sqrt(n)); return dict(n=len(w), days=n, mean_bp=1e4 * w.ret.mean(), t=float(t), p=float(stats.t.sf(t, n - 1)))


def read(path):
    return pd.read_csv(path) if path.exists() else pd.DataFrame(columns=COLS)


def append(path, rows):
    if not rows: return
    df = pd.DataFrame(rows, columns=COLS); df.to_csv(path, mode="a", header=not path.exists(), index=False)


def bh_survivors(dev):
    """Benjamini-Hochberg over EVERY dev row ever recorded (m = cumulative trials); floors n/days/mean applied to who may be a survivor."""
    m = len(dev)
    if m == 0: return set()
    d = dev.sort_values("p").reset_index(drop=True); thr = Q * (np.arange(1, m + 1) / m); ok = np.nonzero(d.p.values <= thr)[0]
    if len(ok) == 0: return set()
    d = d.iloc[: ok.max() + 1]; d = d[(d.n >= N_MIN) & (d.days >= DAYS_MIN) & (d.mean_bp >= BP_MIN)]; return set(d.hash)


def run(gens, pop, seed, placebo):
    path = HERE / (f"SI_PLACEBO_LEDGER_V2_{placebo}.csv" if placebo is not None else "SI_LEDGER_V2.csv")
    lessons = HERE / ("SI_PLACEBO_LESSONS_V2_%s.md" % placebo if placebo is not None else "SI_LESSONS_V2.md")
    tab = PIT.tables(placebo); dr = PIT.drifts(tab); rng = np.random.default_rng(seed); led = read(path); seen = set(led.hash.astype(str)); g0 = int(led.gen.max()) + 1 if len(led) else 0
    parents = []
    for g in range(g0, g0 + gens):
        specs, keys = [], set()
        def add(s):
            k = G.key(s)
            if k not in seen and k not in keys: keys.add(k); specs.append(s)
        n_mut = int(0.6 * pop) if parents else 0
        for _ in range(n_mut * 5):
            if len(specs) >= n_mut: break
            add(G.mutate(parents[rng.integers(len(parents))], rng))
        while len(specs) < pop: add(G.sample(rng))
        rows = []; now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        for s in specs:
            st = window_stats(G.trades(tab, s, dr), PIT.DEV); rows.append([now, "dev", g, G.key(s), json.dumps(s, sort_keys=True), st["n"], st["days"], st["mean_bp"], st["t"], st["p"]])
        append(path, rows); led = read(path); seen |= set(led.hash.astype(str))
        dev = led[led.stage == "dev"]; surv = bh_survivors(dev); val_done = set(led[led.stage == "val"].hash.astype(str)); vrows = []
        for h in surv - val_done:
            s = json.loads(dev[dev.hash == h].spec.iloc[0]); st = window_stats(G.trades(tab, s, dr), PIT.VAL)
            vrows.append([now, "val", g, h, json.dumps(s, sort_keys=True), st["n"], st["days"], st["mean_bp"], st["t"], st["p"]])
        append(path, vrows); led = read(path); val = led[led.stage == "val"]
        vpass = val[(val.n >= VAL_N_MIN) & (val.mean_bp > 0) & (val.p < VAL_P)]
        this = dev[dev.gen == g].copy(); this["ok"] = (this.n >= N_MIN) & (this.days >= DAYS_MIN)
        top = this[this.ok].sort_values("t", ascending=False).head(12); parents = [json.loads(x) for x in top.spec]
        fam = pd.Series([json.loads(x)["fam"] for x in dev[dev.hash.isin(surv)].spec]).value_counts().to_dict() if surv else {}
        line = (f"gen {g}: {len(specs)} new specs, cumulative trials m={len(dev)}, best DEV t this gen {top.t.max() if len(top) else float('nan'):.2f} | "
                f"S1 survivors (BH q={Q}, cumulative) {len(surv)} {fam} | VAL passes (S2) {len(vpass)} of {len(val)} looked at")
        print(line, flush=True)
        with open(lessons, "a", encoding="utf-8") as f: f.write(f"- {now} {line}\n")
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--gens", type=int, default=6); ap.add_argument("--pop", type=int, default=250)
    ap.add_argument("--seed", type=int, default=1); ap.add_argument("--placebo", type=int, default=None); a = ap.parse_args(ARGV)
    run(a.gens, a.pop, a.seed, a.placebo)
