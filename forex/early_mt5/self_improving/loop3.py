"""v3 self-improving loop: classes, carry, common-time-shift null (PREREG_SELF_IMPROVING.md Amendment 2).
   python -m mt5broker.self_improving.loop3 --gens 10 --pop 300 --seed 1 [--placebo 7]
Append-only ledger SI_LEDGER_V3.csv (or SI_PLACEBO_LEDGER_V3_<seed>.csv). HOLD 2026 is never read here."""
import sys
ARGV = sys.argv[1:]          # legacy mt5broker modules overwrite sys.argv at import time

import argparse
import datetime as dt
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from mt5broker.self_improving import grammar as G, platform_pit as PIT, platform_v3 as P3

HERE = Path(__file__).resolve().parent
COLS = ["when", "stage", "gen", "hash", "spec", "n", "days", "mean_bp", "z", "p"]
N_MIN, DAYS_MIN, BP_MIN, Q = 80, 40, 3.0, 0.10
VAL_N_MIN, VAL_P = 25, 0.20
NSHIFT = 400
CLS = tuple(P3.CLASSES)


def lower_priority():
    try:
        import ctypes; ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)   # BELOW_NORMAL
    except Exception: pass


class Null:
    """Per-class cache of the net return of 'enter at day i, hold h days' for every market and side."""
    def __init__(self, tab, carry): self.tab, self.carry, self.R = tab, carry, {}; self.S = np.random.default_rng(12345).integers(10, 10_000, size=NSHIFT)

    def arr(self, m, h, side):
        k = (m, h, side)
        if k not in self.R:
            t = self.tab[m]; b, a, tt = t.b.values, t.a.values, t.t.values; n = len(t); r = np.full(n, np.nan)
            if h < n:
                r[: n - h] = (b[h:] / a[: n - h] - 1) if side > 0 else (b[: n - h] / a[h:] - 1)
                r[: n - h] -= self.carry * 1e-4 * (tt[h:] - tt[: n - h]) / 86400.0
            self.R[k] = r
        return self.R[k]

    def stat(self, T, lo_hi):
        """T: trades of the spec (cols mkt, date, i, h, side, ret). Window = entries dated inside lo_hi. Returns n, days, mean_bp, z, p."""
        w = T[(T.date >= pd.Timestamp(lo_hi[0])) & (T.date <= pd.Timestamp(lo_hi[1]))]
        if len(w) < 3: return dict(n=len(w), days=len(w), mean_bp=np.nan if len(w) == 0 else 1e4 * w.ret.mean(), z=np.nan, p=1.0)
        total = np.zeros(NSHIFT)
        for (m, h, side), g in w.groupby(["mkt", "h", "side"]):
            idx = self.tab[m].index; lo = max(int(idx.searchsorted(pd.Timestamp(lo_hi[0]))), 200); hi = int(idx.searchsorted(pd.Timestamp(lo_hi[1]), side="right")) - 1; W = hi - lo + 1
            if W < 30: continue
            rel = (g.i.values - lo)[None, :]; ii = lo + (rel + self.S[:, None]) % W; total += np.nansum(self.arr(m, int(h), int(side))[ii], axis=1)
        null = total / len(w); sd = null.std(ddof=1); obs = w.ret.mean()
        if not np.isfinite(sd) or sd == 0: return dict(n=len(w), days=w.date.nunique(), mean_bp=1e4 * obs, z=np.nan, p=1.0)
        z = (obs - null.mean()) / sd; return dict(n=len(w), days=int(w.date.nunique()), mean_bp=1e4 * obs, z=float(z), p=float(stats.norm.sf(z)))


def read(path): return pd.read_csv(path) if path.exists() else pd.DataFrame(columns=COLS)


def append(path, rows):
    if rows: pd.DataFrame(rows, columns=COLS).to_csv(path, mode="a", header=not path.exists(), index=False)


def bh_survivors(dev):
    m = len(dev)
    if m == 0: return set()
    d = dev.sort_values("p").reset_index(drop=True); ok = np.nonzero(d.p.values <= Q * (np.arange(1, m + 1) / m))[0]
    if len(ok) == 0: return set()
    d = d.iloc[: ok.max() + 1]; d = d[(d.n >= N_MIN) & (d.days >= DAYS_MIN) & (d.mean_bp >= BP_MIN)]; return set(d.hash)


def sample(rng):
    s = G.sample(rng); s["cls"] = CLS[rng.integers(len(CLS))]; return s


def mutate(s, rng):
    x = G.mutate({k: v for k, v in s.items() if k != "cls"}, rng); x["cls"] = s["cls"] if rng.random() > 0.15 else CLS[rng.integers(len(CLS))]; return x


def run(gens, pop, seed, placebo):
    lower_priority()
    path = HERE / (f"SI_PLACEBO_LEDGER_V3_{placebo}.csv" if placebo is not None else "SI_LEDGER_V3.csv")
    lessons = HERE / (f"SI_PLACEBO_LESSONS_V3_{placebo}.md" if placebo is not None else "SI_LESSONS_V3.md")
    tabs = {c: P3.tables(c, placebo) for c in CLS}; nulls = {c: Null(tabs[c], P3.CLASSES[c]["carry"]) for c in CLS}
    rng = np.random.default_rng(seed + (0 if placebo is None else 1000 + placebo)); led = read(path); seen = set(led.hash.astype(str)); g0 = int(led.gen.max()) + 1 if len(led) else 0
    def evaluate(s, win):
        c = s["cls"]; T = G.trades(tabs[c], {k: v for k, v in s.items() if k != "cls"}, None, P3.CLASSES[c]["carry"]); return nulls[c].stat(T, win) if len(T) else dict(n=0, days=0, mean_bp=np.nan, z=np.nan, p=1.0)
    parents = []
    if len(led):                      # resume: parents = the best specs of the last generation
        last = led[(led.stage == "dev") & (led.gen == led.gen.max()) & (led.n >= N_MIN) & (led.days >= DAYS_MIN)].sort_values("z", ascending=False).head(12); parents = [json.loads(x) for x in last.spec]
    for g in range(g0, g0 + gens):
        specs, keys = [], set()
        def add(s):
            k = G.key(s)
            if k not in seen and k not in keys: keys.add(k); specs.append(s)
        n_mut = int(0.6 * pop) if parents else 0
        for _ in range(n_mut * 5):
            if len(specs) >= n_mut: break
            add(mutate(parents[rng.integers(len(parents))], rng))
        while len(specs) < pop: add(sample(rng))
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M"); rows = []
        for s in specs:
            st = evaluate(s, PIT.DEV); rows.append([now, "dev", g, G.key(s), json.dumps(s, sort_keys=True), st["n"], st["days"], st["mean_bp"], st["z"], st["p"]])
        append(path, rows); led = read(path); seen |= set(led.hash.astype(str))
        dev = led[led.stage == "dev"]; surv = bh_survivors(dev); done = set(led[led.stage == "val"].hash.astype(str)); vrows = []
        for h in surv - done:
            s = json.loads(dev[dev.hash == h].spec.iloc[0]); st = evaluate(s, PIT.VAL); vrows.append([now, "val", g, h, json.dumps(s, sort_keys=True), st["n"], st["days"], st["mean_bp"], st["z"], st["p"]])
        append(path, vrows); led = read(path); val = led[led.stage == "val"]; vpass = val[(val.n >= VAL_N_MIN) & (val.mean_bp > 0) & (val.p < VAL_P)]
        this = dev[dev.gen == g]; ok = this[(this.n >= N_MIN) & (this.days >= DAYS_MIN)].sort_values("z", ascending=False).head(12); parents = [json.loads(x) for x in ok.spec]
        sd = dev[dev.hash.isin(surv)]; fam = pd.Series([json.loads(x)["cls"] + "/" + json.loads(x)["fam"] for x in sd.spec]).value_counts().to_dict() if len(sd) else {}
        line = (f"gen {g}: {len(specs)} new specs, cumulative m={len(dev)}, best DEV z this gen {ok.z.max() if len(ok) else float('nan'):.2f} | "
                f"S1 survivors {len(surv)} {fam} | VAL passes (S2) {len(vpass)} of {len(val)} looked at")
        print(line, flush=True)
        with open(lessons, "a", encoding="utf-8") as f: f.write(f"- {now} {line}\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--gens", type=int, default=10); ap.add_argument("--pop", type=int, default=300)
    ap.add_argument("--seed", type=int, default=1); ap.add_argument("--placebo", type=int, default=None); a = ap.parse_args(ARGV)
    run(a.gens, a.pop, a.seed, a.placebo)
