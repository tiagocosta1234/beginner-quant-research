"""Regime layer on the installed system (PREREG_REGIME.md).
   python -m forex.self_improving.regime.regime_lab --policies 100000 [--placebo 41] [--tag NAME]"""
import sys
ARGV = sys.argv[1:]          # legacy mt5broker modules overwrite sys.argv at import time

import argparse
import datetime as dt
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from forex.ea_research import combo_grid as G, pass70 as P, dip_addon as DA
from forex.self_improving.freeform import ff5_data as F5, ff6_data as D6

HERE = Path(__file__).resolve().parent
LEDGERS = Path("D:/finance/si_ledgers"); LEDGERS.mkdir(parents=True, exist_ok=True)
CACHE = Path("D:/finance/scratch/si_cache/regime_data.pkl")
FS = (0.0, 0.5, 1.0, 1.5); GUARD = 1500.0; HZ = 44
WIN = {"a": ("2022-01-01", "2023-06-30"), "b": ("2023-07-01", "2024-12-31"), "val": ("2025-01-01", "2025-12-31")}
LV = (0.10, 0.25, 0.50, 0.75, 0.90)
FEATS = ["vix_rank", "vix_chg5", "curve_chg5", "dxy_chg5", "vix9r", "skew_rank", "cpi_today", "nfp_today", "fomc_today", "any_today", "cpi_tom", "nfp_tom", "fomc_tom", "any_tom",
         "gvr", "gret20", "gpos60", "grng1", "gvol5", "pl1", "tr5", "tr20", "dow"]
BIN = {"cpi_today", "nfp_today", "fomc_today", "any_today", "cpi_tom", "nfp_tom", "fomc_tom", "any_tom"}
NSHIFT = 300


def build():
    if CACHE.exists(): return pickle.load(open(CACHE, "rb"))
    G.EV = F5.events()["CPI"]; DA.RISK = 500.0; Tk, bb = DA.trades(); Tk, Dd = DA.day_arrays(Tk, bb); Dd = Dd * 0.75; S = {}
    for f in FS: S[f] = G.add_dip(G.pair_series("FT", 1.5 * f, 1.5 * f, GUARD), Dd * f, GUARD)
    days = np.asarray(S[1.0]["days"]); keep = days * 86400 < F5.ts("2025-12-31") + 86400; days = days[keep]
    ser = {f: {k: np.asarray(S[f][k], dtype=float)[keep] for k in ("V", "B", "Hi")} for f in FS}
    dates = pd.DatetimeIndex(pd.to_datetime(days * 86400, unit="s").normalize()); out = pd.DataFrame(index=days)
    dm = D6.daily_macro(); lagd = dates - pd.Timedelta(days=2); lag = dm.reindex(dm.index.union(lagd).sort_values()).ffill().reindex(lagd)
    for f in ("vix_rank", "vix_chg5", "curve_chg5", "dxy_chg5", "vix9r", "skew_rank"): out[f] = lag[f].values
    ev = F5.events()
    for k, nm in (("CPI", "cpi"), ("NFP", "nfp"), ("FOMC", "fomc"), ("ANY", "any")):
        E = ev[k]; lo = days * 86400; out[f"{nm}_today"] = (np.searchsorted(E, lo + 86400) - np.searchsorted(E, lo) > 0).astype(float); out[f"{nm}_tom"] = (np.searchsorted(E, lo + 172800) - np.searchsorted(E, lo + 86400) > 0).astype(float)
    b = D6.bars15("XAUUSD"); gd = b.groupby(b.t0 // 86400).agg(hi=("bh", "max"), lo=("bl", "min"), cl=("bc", "last"), rv=("rv", "sum")); gd.index = gd.index.astype(np.int64)
    gv5 = np.sqrt(gd.rv.rolling(5).mean()); gv60 = np.sqrt(gd.rv.rolling(60).mean()); rg = (gd.hi - gd.lo) / gd.cl
    g = pd.DataFrame({"gvr": gv5 / gv60, "gret20": np.log(gd.cl / gd.cl.shift(20)), "gpos60": (gd.cl - gd.cl.rolling(60).min()) / (gd.cl.rolling(60).max() - gd.cl.rolling(60).min()), "grng1": rg / rg.rolling(60).median(), "gvol5": gv5}, index=gd.index)
    j = np.searchsorted(g.index.values, days, side="left") - 1
    for c in g.columns: out[c] = np.where(j >= 0, g[c].values[np.maximum(j, 0)], np.nan)                    # gold state of the last gold day BEFORE the day
    V1 = pd.Series(ser[1.0]["V"], index=days); out["pl1"] = V1.shift(1).values; out["tr5"] = V1.rolling(5).sum().shift(1).values; out["tr20"] = V1.rolling(20).sum().shift(1).values
    out["dow"] = (days + 3) % 7; out = out[FEATS]; res = dict(days=days, ser=ser, feat=out); pickle.dump(res, open(CACHE, "wb")); return res


class Window:
    def __init__(self, data, w, placebo_roll=0):
        lo, hi = F5.ts(WIN[w][0]), F5.ts(WIN[w][1]) + 86400; days = data["days"]; m = (days * 86400 >= lo) & (days * 86400 < hi); self.n = int(m.sum()); self.ser = {f: {k: data["ser"][f][k][m] for k in ("V", "B", "Hi")} for f in FS}
        F = data["feat"].copy()
        if placebo_roll: F = pd.DataFrame(np.roll(F.values, placebo_roll, axis=0), index=F.index, columns=F.columns)         # break every link between the regime and the series (calibration)
        self.F = F.values[m]; self.starts = np.arange(0, self.n - HZ + 1)


def tables(wa):
    q = {}
    for i, f in enumerate(FEATS):
        v = wa.F[:, i]; v = v[np.isfinite(v)]
        q[f] = [0.5] if f in BIN else [0.0, 1.0, 2.0, 3.0] if f == "dow" else [float(x) for x in np.quantile(v, LV)]
    return q


def masks(win, q):
    out = {}
    for i, f in enumerate(FEATS):
        for k, thr in enumerate(q[f]):
            col = win.F[:, i]; out[(f, ">=", k)] = np.nan_to_num(col >= thr, nan=False).astype(bool) & np.isfinite(col); out[(f, "<=", k)] = np.nan_to_num(col <= thr, nan=False).astype(bool) & np.isfinite(col)
    return out


def replay(win, cond, fon, foff):
    on, off = win.ser[fon], win.ser[foff]; st0 = win.starts; n = len(st0); cnt = np.zeros(n); st = np.zeros(n, np.int8)
    for j in range(HZ):
        idx = st0 + j; c = cond[idx]; V = np.where(c, on["V"][idx], off["V"][idx]); B = np.where(c, on["B"][idx], off["B"][idx])
        act = st == 0; br = act & ((B <= -0.025 * P.A) | (P.A + cnt + B <= 0.92 * P.A)); st = np.where(br, 2, st); act = st == 0
        cnt = np.where(act, P.counted(cnt, V), cnt); ps = act & (cnt >= P.TARGET); st = np.where(ps, 1, st)
    return float(np.mean(st == 1)), float(np.mean(st == 2))


def score(pb): return pb[0] - 3.0 * pb[1]


def policy_cond(policy, M):
    c = None
    for f, op, k in policy["conds"]:
        x = M[(f, op, k)]; c = x if c is None else (c & x)
    return c


def random_policy(rng, q):
    n = int(rng.choice([1, 2])); conds = []
    for _ in range(n):
        f = FEATS[rng.integers(len(FEATS))]; conds.append([f, ">=" if rng.random() < 0.5 else "<=", int(rng.integers(len(q[f])))])
    fo = rng.choice(len(FS), size=2, replace=False); return dict(conds=conds, fon=FS[fo[0]], foff=FS[fo[1]])


def shift_null(win, policy, M, obs_delta, base, rng):
    cond = policy_cond(policy, M); sh = rng.integers(20, max(win.n - 20, 40), size=NSHIFT); d = np.empty(NSHIFT)
    for i, s in enumerate(sh): d[i] = score(replay(win, np.roll(cond, int(s)), policy["fon"], policy["foff"])) - base
    sd = d.std(ddof=1); z = (obs_delta - d.mean()) / sd if sd > 0 else np.nan
    return z, float(stats.norm.sf(z)) if np.isfinite(z) else 1.0


def bh(p, q=0.05):
    o = np.argsort(p); ok = np.nonzero(np.asarray(p)[o] <= q * (np.arange(1, len(p) + 1) / len(p)))[0]; out = np.zeros(len(p), bool)
    if len(ok): out[o[: ok.max() + 1]] = True
    return out


def run(npol, placebo, tag):
    name = tag or (f"placebo{placebo}" if placebo is not None else "real"); led = LEDGERS / f"REG_{name}.csv"; rng = np.random.default_rng(11 + (0 if placebo is None else 1000 + placebo))
    data = build(); roll = 0 if placebo is None else int(np.random.default_rng(placebo).integers(300, 900))
    W = {w: Window(data, w, roll) for w in WIN}; q = tables(W["a"]); M = {w: masks(W[w], q) for w in WIN}; one = {w: np.ones(W[w].n, bool) for w in WIN}
    base = {w: replay(W[w], one[w], 1.0, 1.0) for w in WIN}; bs = {w: score(base[w]) for w in WIN}
    print(f"baseline f=1.0: " + " | ".join(f"{w}: P(pass44) {100*base[w][0]:.1f}% breach {100*base[w][1]:.1f}% ({len(W[w].starts)} starts)" for w in WIN), flush=True)
    rows = []
    for k in range(npol):
        p = random_policy(rng, q); r = replay(W["a"], policy_cond(p, M["a"]), p["fon"], p["foff"]); rows.append((score(r) - bs["a"], r[0] - base["a"][0], r[1] - base["a"][1], p))
    cand = sorted([x for x in rows if x[1] > 0 and x[2] <= 0], key=lambda x: -x[0])[:200]
    print(f"stage A: {npol} policies, {len(cand)} with delta pass > 0 and delta breach <= 0 (best delta score {max(x[0] for x in rows):+.3f}); promoting {len(cand)}", flush=True)
    bres = []
    for dA, dpA, dbA, p in cand:
        r = replay(W["b"], policy_cond(p, M["b"]), p["fon"], p["foff"]); d = score(r) - bs["b"]; z, pv = shift_null(W["b"], p, M["b"], d, bs["b"], rng); bres.append((p, dA, d, r[0] - base["b"][0], r[1] - base["b"][1], z, pv))
    S1 = []
    if bres:
        rej = bh(np.array([x[6] for x in bres]))
        for (p, dA, d, dp, db, z, pv), f in zip(bres, rej):
            if f and dp >= 0.02 and db <= 0: S1.append((p, dA, d, dp, db, z, pv))
    print(f"stage B: {len(bres)} tested, best B z {max([x[5] for x in bres if np.isfinite(x[5])] or [float('nan')]):.2f}, smallest p {min([x[6] for x in bres] or [float('nan')]):.1e}, BH survivors with floors: {len(S1)}", flush=True)
    S2 = []
    for p, dA, dB, dpB, dbB, zB, pB in S1:
        r = replay(W["val"], policy_cond(p, M["val"]), p["fon"], p["foff"]); d = score(r) - bs["val"]; z, pv = shift_null(W["val"], p, M["val"], d, bs["val"], rng)
        ok = (r[0] - base["val"][0] >= 0.02) and (r[1] - base["val"][1] <= 0) and pv < 0.2; S2.append((p, dB, d, r[0] - base["val"][0], r[1] - base["val"][1], pv, ok))
    print(f"stage VAL: {len(S2)} looked at, passing: {sum(x[6] for x in S2)}", flush=True)
    pd.DataFrame([dict(when=dt.datetime.now().strftime("%Y-%m-%d %H:%M"), stage="b", policy=json.dumps(x[0], sort_keys=True), dA=x[1], dB=x[2], dpassB=x[3], dbreachB=x[4], zB=x[5], pB=x[6]) for x in bres]).to_csv(led, index=False)
    for p, dB, d, dp, db, pv, ok in S2: print("  VAL:", json.dumps(p), f"delta B {dB:+.3f}, delta VAL {d:+.3f}, dpass {100*dp:+.1f} pts, dbreach {100*db:+.1f} pts, p {pv:.2f}, pass={ok}")
    return len(S1), sum(x[6] for x in S2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--policies", type=int, default=100000); ap.add_argument("--placebo", type=int, default=None); ap.add_argument("--tag", default=None); a = ap.parse_args(ARGV)
    run(a.policies, a.placebo, a.tag)
