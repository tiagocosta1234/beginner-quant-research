"""Free-form trader agent v6: M1 information in 15-minute decisions, price-pattern vocabulary, trained inside the MT5 broker account environment (PREREG_V6_M1.md).
   python -m forex.self_improving.freeform.ff6_agent --gens 20 --pop 2000 --seed 1 [--placebo 7] [--tag NAME]
Append-only ledger on data\\si_ledgers (outside git); compact summary files are written next to this module. 2026 data is never loaded."""
import sys
ARGV = sys.argv[1:]          # legacy mt5broker modules overwrite sys.argv at import time

import argparse
import datetime as dt
import json
import os
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from forex.self_improving import platform_v3 as P3
from forex.self_improving.freeform import ff6_data as D, acct_env as E

HERE = Path(__file__).resolve().parent
LEDGERS = Path("data/si_ledgers"); LEDGERS.mkdir(parents=True, exist_ok=True)
COLS = ["when", "stage", "gen", "hash", "rule", "op", "n", "clusters", "mean_bp", "z", "p"]
PROMO_Z, PROMO_N, PROMO_CL, PROMO_TOP, PROMO_BP = 2.5, 150, 20, 300, 1.0      # window A -> B promotion (A net mean >= 1 bp: search guidance only)
B_N, B_CL, BP_MIN, Q = 100, 20, 3.0, 0.05
VAL_N, VAL_CL, VAL_P = 100, 20, 0.20
CLS = tuple(P3.CLASSES); OPS = ("thr", "swap", "add", "drop", "hor", "flip", "cls", "cross", "random")
NF = len(D.FEATS)


def lower_priority():
    try:
        import ctypes; ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    except Exception: pass


def key(r): return f"{zlib.crc32(json.dumps(r, sort_keys=True).encode()):08x}{zlib.adler32(json.dumps(r, sort_keys=True).encode()):08x}"


def levels(f): return len(D.CATLV[f]) if f in D.CATLV else len(D.LEVELS)


def rand_cond(rng, used=()):
    fs = [f for f in D.FEATS if f not in used]; f = fs[rng.integers(len(fs))]; return [f, ">=" if rng.random() < 0.5 else "<=", int(rng.integers(levels(f)))]


def random_rule(rng):
    n = int(rng.choice([1, 2, 3], p=[0.3, 0.45, 0.25])); conds = []
    for _ in range(n): conds.append(rand_cond(rng, [c[0] for c in conds]))
    return dict(cls=CLS[rng.integers(len(CLS))], side=int(rng.choice([1, -1])), H=int(D.HS[rng.integers(len(D.HS))]), conds=conds)


def mutate(r, rng, op):
    x = json.loads(json.dumps(r)); c = x["conds"]
    if op == "thr":
        k = int(rng.integers(len(c))); c[k][2] = int(min(max(c[k][2] + rng.choice([-1, 1]), 0), levels(c[k][0]) - 1))
    elif op == "swap":
        k = int(rng.integers(len(c))); c[k] = rand_cond(rng, [q[0] for j, q in enumerate(c) if j != k])
    elif op == "add" and len(c) < 3: c.append(rand_cond(rng, [q[0] for q in c]))
    elif op == "drop" and len(c) > 1: c.pop(int(rng.integers(len(c))))
    elif op == "hor": i = D.HS.index(x["H"]); x["H"] = int(D.HS[min(max(i + int(rng.choice([-1, 1])), 0), len(D.HS) - 1)])
    elif op == "flip": x["side"] = -x["side"]
    elif op == "cls": x["cls"] = CLS[rng.integers(len(CLS))]
    return x


def cross(a, b, rng):
    conds = [list(c) for c in a["conds"]] + [list(c) for c in b["conds"]]; seen = set(); out = []
    for c in rng.permutation(len(conds)):
        if conds[c][0] not in seen and len(out) < 3: seen.add(conds[c][0]); out.append(conds[c])
    return dict(cls=a["cls"], side=a["side"] if rng.random() < 0.5 else b["side"], H=a["H"] if rng.random() < 0.5 else b["H"], conds=out)


class Evaluator:
    def __init__(self, stacks): self.S = stacks; self.cache = {}; self.um = {}

    def mask(self, st, w, cls, c):
        k = (cls, w, c[0], c[1], c[2])
        if k not in self.cache:
            win = getattr(st, w); thr = st.q[c[0]][c[2]]; col = win.X[:, D.FI[c[0]]]; self.cache[k] = (col >= thr) if c[1] == ">=" else (col <= thr)
            if len(self.cache) > 1500: self.cache.pop(next(k_ for k_ in self.cache if k_[-1] != 'okh' and k_[2] != 'grid'))
        return self.cache[k]

    def umean(self, cls, w, side, hi):
        """Mean GROSS (mid-to-mid, before spread and carry) return of entering at a random bar, per market, for this side/horizon/window (drift included)."""
        k = (cls, w, side, hi)
        if k not in self.um:
            win = getattr(self.S[cls], w); g = win.Yg[:, hi].astype(np.float64); Y = g if side > 0 else 1.0 / (1.0 + g) - 1.0; v = np.isfinite(Y) & self.ok_hour(self.S[cls], w, cls) & self.grid(self.S[cls], w, cls, D.HS[hi]); nm = int(win.mkt.max()) + 1
            self.um[k] = np.bincount(win.mkt, weights=np.where(v, Y, 0.0), minlength=nm) / np.maximum(np.bincount(win.mkt, weights=v, minlength=nm), 1)
        return self.um[k]

    def ok_hour(self, st, w, cls):
        k = (cls, w, "okh")
        if k not in self.cache:
            h = getattr(st, w).X[:, D.FI["hour"]]; self.cache[k] = ~((h == 23) | (h == 0))       # Amendment 5: no entries in the rollover window (server hours 23 and 0)
        return self.cache[k]

    def grid(self, st, w, cls, H):
        k = (cls, w, "grid", H)
        if k not in self.cache:
            win = getattr(st, w); pos = np.arange(len(win.X)) - np.repeat(win.seg[:-1], np.diff(win.seg)); self.cache[k] = (pos % H == 0)   # Amendment 7: entries only every H-th bar of each market segment
        return self.cache[k]

    def trades(self, r, w):
        st = self.S[r["cls"]]; win = getattr(st, w); m = self.ok_hour(st, w, r["cls"]) & self.grid(st, w, r["cls"], r["H"])
        for c in r["conds"]:
            m = m & self.mask(st, w, r["cls"], c)
        hi = D.HS.index(r["H"]); Y = (win.Yl if r["side"] > 0 else win.Ys)[:, hi]; ret = Y[m]; ok = np.isfinite(ret)
        g = win.Yg[m][:, hi][ok].astype(np.float64); g = g if r["side"] > 0 else 1.0 / (1.0 + g) - 1.0
        return ret[ok], g, win.week[m][ok], win.mkt[m][ok], hi

    def rows(self, r, w):
        """What the account would do: enter at the FIRST signal bar when the market is flat, hold H bars, then look for the next signal (no grid; the grid is only a statistics device).
        Returns market names, signal-bar times and hourly vols of those entries."""
        st = self.S[r["cls"]]; win = getattr(st, w); m = self.ok_hour(st, w, r["cls"])
        for c in r["conds"]: m = m & self.mask(st, w, r["cls"], c)
        hi = D.HS.index(r["H"]); Y = (win.Yl if r["side"] > 0 else win.Ys)[:, hi]; idx = np.nonzero(m & np.isfinite(Y))[0]; H = r["H"]; pick = []
        for mi, (a, b) in enumerate(zip(win.seg[:-1], win.seg[1:])):
            lo, hi_ = np.searchsorted(idx, a), np.searchsorted(idx, b); nxt = -1
            for q in idx[lo:hi_]:
                if q >= nxt: pick.append(q); nxt = q + H
        pick = np.array(pick, dtype=np.int64)
        return [st.markets[i] for i in win.mkt[pick]], win.t0[pick], win.sd1[pick]

    def stat(self, r, w):
        ret, gross, wk, mk, hi = self.trades(r, w); n = len(ret)
        if n < 30: return dict(n=n, clusters=0, mean_bp=np.nan if n == 0 else 1e4 * float(ret.mean()), ex_bp=np.nan, z=np.nan, p=1.0)
        ex = gross - self.umean(r["cls"], w, r["side"], hi)[mk]; me = ex.mean(); wk = wk - wk.min(); cnt = np.bincount(wk); res = np.bincount(wk, weights=ex - me); cl = int((cnt > 0).sum())
        se = np.sqrt((res ** 2).sum() * cl / (cl - 1)) / n
        if cl < 5 or se == 0: return dict(n=n, clusters=cl, mean_bp=1e4 * float(ret.mean()), ex_bp=1e4 * float(me), z=np.nan, p=1.0)
        z = me / se; return dict(n=n, clusters=cl, mean_bp=1e4 * float(ret.mean()), ex_bp=1e4 * float(me), z=float(z), p=float(stats.t.sf(z, cl - 1)))


def bh(p, m_total):
    """Benjamini-Hochberg over m_total tests; p is the array of ALL evaluated p-values. Returns a boolean mask of rejections."""
    o = np.argsort(p); ok = np.nonzero(p[o] <= Q * (np.arange(1, len(p) + 1) / m_total))[0]; out = np.zeros(len(p), bool)
    if len(ok): out[o[: ok.max() + 1]] = True
    return out


def env_eval(frames, ev, r, w, wstart, wend):
    nm, t0, sd = ev.rows(r, w)
    if len(t0) == 0: return 0, 0.0, 0.0
    paths = E.trade_paths(frames[r["cls"]], nm, t0, sd, r["side"], r["H"]); s = E.build_series(paths, wstart, wend); pp, pb = E.pass_stats(s, 44, 8000)
    return len(paths), pp, pb


def run(gens, pop, seed, placebo, tag):
    lower_priority(); name = tag or (f"placebo{placebo}" if placebo is not None else "real"); ledger = LEDGERS / f"FF10_{name}.csv"; envled = LEDGERS / f"FF10_{name}_env.csv"; summary = HERE / f"FF10_{name}_SUMMARY.md"
    stacks = {c: D.Stack(c, placebo) for c in CLS}; ev = Evaluator(stacks); frames = {c: E.Frames(stacks[c]) for c in CLS}; rng = np.random.default_rng(seed + (0 if placebo is None else 1000 + placebo))
    led = pd.read_csv(ledger) if ledger.exists() else pd.DataFrame(columns=COLS); la = led[led.stage == "a"]; lb = led[led.stage == "b"]
    seen = set(la.hash.astype(str)); ruleof = {h: json.loads(r) for h, r in zip(la.hash.astype(str), la.rule)}; zA = dict(zip(la.hash.astype(str), la.z)); okA = {}
    for h, n, c, bp in zip(la.hash.astype(str), la.n, la.clusters, la.mean_bp): okA[h] = bool(n >= PROMO_N and c >= PROMO_CL and bp >= PROMO_BP)
    PB = {h: (p, n, c, bp, z) for h, p, n, c, bp, z in zip(lb.hash.astype(str), lb.p, lb.n, lb.clusters, lb.mean_bp, lb.z)}
    valdone = set(led[led.stage == "val"].hash.astype(str)); g0 = int(la.gen.max()) + 1 if len(la) else 0; m_a = len(la)
    envs = {}
    if envled.exists():
        el = pd.read_csv(envled); envs = dict(zip(el.hash.astype(str), el.score))
    ema = {o: 0.2 for o in OPS}
    def rank_key(h): return (1, envs[h] + 1e-3 * (zA[h] if np.isfinite(zA.get(h, np.nan)) else -9)) if h in envs else (0, zA[h] if np.isfinite(zA.get(h, np.nan)) else -9)
    def elite_pool(): return [ruleof[h] for h in sorted([h for h in ruleof if okA.get(h)], key=rank_key, reverse=True)[:60]]
    elites = elite_pool()

    def append(rows): pd.DataFrame(rows, columns=COLS).to_csv(ledger, mode="a", header=not ledger.exists(), index=False)

    for g in range(g0, g0 + gens):
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M"); new = []
        probs = np.array([0.05 + ema[o] for o in OPS]); probs /= probs.sum(); tries = 0
        while len(new) < pop and tries < pop * 6:
            tries += 1
            if not elites: r, op = random_rule(rng), "random"
            else:
                op = OPS[rng.choice(len(OPS), p=probs)]
                if op == "random": r = random_rule(rng)
                elif op == "cross": r = cross(elites[rng.integers(len(elites))], elites[rng.integers(len(elites))], rng)
                else: r = mutate(elites[rng.integers(len(elites))], rng, op)
            k = key(r)
            if k in seen: continue
            seen.add(k); new.append((k, r, op))
        rows = []; res = {}
        for k, r, op in new:
            st = ev.stat(r, "a"); res[k] = st; ruleof[k] = r; zA[k] = st["z"]; okA[k] = bool(st["n"] >= PROMO_N and st["clusters"] >= PROMO_CL and st["mean_bp"] >= PROMO_BP)
            rows.append([now, "a", g, k, json.dumps(r, sort_keys=True), op, st["n"], st["clusters"], st["mean_bp"], st["z"], st["p"]])
        append(rows); m_a += len(new)
        # the environment: the 40 best qualifying new rules are traded in the MT5 broker account on window A; the score drives the elites and the operator credit
        qual = sorted([k for k, _, _ in new if okA[k] and np.isfinite(res[k]["z"]) and res[k]["z"] >= PROMO_Z], key=lambda k: -res[k]["z"])[:40]; erows = []; gscore = {}
        for k in qual:
            n_tr, pp, pb = env_eval(frames, ev, ruleof[k], "a", D.WA[0], D.WA[1]); sc = pp - 3.0 * pb; envs[k] = sc; gscore[k] = sc
            erows.append([now, g, k, "A", n_tr, pp, pb, sc])
        if erows: pd.DataFrame(erows, columns=["when", "gen", "hash", "window", "trades", "p_pass", "p_breach", "score"]).to_csv(envled, mode="a", header=not envled.exists(), index=False)
        # promotion to B (statistical error control unchanged)
        cand = sorted([k for k, _, _ in new if okA[k] and np.isfinite(res[k]["z"]) and res[k]["z"] >= PROMO_Z], key=lambda k: -res[k]["z"])[:PROMO_TOP]; brow = []
        for k in cand:
            st = ev.stat(ruleof[k], "b"); PB[k] = (st["p"], st["n"], st["clusters"], st["mean_bp"], st["z"])
            brow.append([now, "b", g, k, json.dumps(ruleof[k], sort_keys=True), "", st["n"], st["clusters"], st["mean_bp"], st["z"], st["p"]])
        S1 = []
        if PB:
            hs = list(PB); pv = np.array([PB[h][0] for h in hs]); rej = bh(pv, len(pv))
            S1 = [h for h, f in zip(hs, rej) if f and PB[h][1] >= B_N and PB[h][2] >= B_CL and PB[h][3] >= BP_MIN]
        vrow = []
        for k in S1:
            if k not in valdone:
                st = ev.stat(ruleof[k], "val"); valdone.add(k); vrow.append([now, "val", g, k, json.dumps(ruleof[k], sort_keys=True), "", st["n"], st["clusters"], st["mean_bp"], st["z"], st["p"]])
        append(brow + vrow); lv = pd.read_csv(ledger); lv = lv[lv.stage == "val"]
        vpass = lv[(lv.n >= VAL_N) & (lv.clusters >= VAL_CL) & (lv.mean_bp >= BP_MIN) & (lv.p < VAL_P)]
        elites = elite_pool()
        sc_list = np.array(list(gscore.values())); thr = np.percentile(sc_list, 75) if len(sc_list) >= 8 else None
        zs = np.array([res[k]["z"] for k, _, _ in new]); valid = np.array([okA[k] for k, _, _ in new]) & np.isfinite(zs)
        for o in OPS:
            if thr is not None:
                sel = [k for k, _, oo in new if oo == o and k in gscore]
                if sel: ema[o] = 0.8 * ema[o] + 0.2 * float(np.mean([gscore[k] > thr for k in sel]))
            else:
                zt = np.nanpercentile(zs[valid], 90) if valid.any() else 0.0; sel = [i for i, (_, _, oo) in enumerate(new) if oo == o and valid[i]]
                if sel: ema[o] = 0.8 * ema[o] + 0.2 * float(np.mean(zs[sel] > zt))
        best = np.nanmax(np.where(valid, zs, np.nan)) if valid.any() else float("nan")
        bsc = max(gscore.values()) if gscore else float("nan"); bpp = float("nan")
        line = (f"gen {g}: {len(new)} rules (A total {m_a}), best A z {best:.2f}, env-scored {len(gscore)} (best score {bsc:.3f}), promoted to B {len(cand)} (B tests {len(PB)}), S1 {len(S1)}, VAL looked {len(lv)}, S2 passes {len(vpass)} | "
                + "ops: " + " ".join(f"{o}={ema[o]:.2f}" for o in OPS))
        print(line, flush=True)
        with open(summary, "a", encoding="utf-8") as f: f.write(f"- {now} {line}\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--gens", type=int, default=20); ap.add_argument("--pop", type=int, default=2000); ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--placebo", type=int, default=None); ap.add_argument("--tag", default=None); a = ap.parse_args(ARGV); run(a.gens, a.pop, a.seed, a.placebo, a.tag)
