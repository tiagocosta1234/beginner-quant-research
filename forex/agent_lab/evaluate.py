"""Honest evaluation for the research agent.
DEV markets (8): the agent sees TRAIN-period feedback on these only.  VAL markets (8): never shown to the agent in any form.
A strategy is validated ONCE per hypothesis on three checks, each a timing-skill z-score (real net return minus the mean of 20 circular shifts of its own positions, Newey-West, Stouffer-combined over markets with correlation 0.3):
  A = DEV markets, sealed later period | B = VAL markets, sealed later period | C = VAL markets, early period (never seen at all).
All three must clear the bar, which rises with every validation ever run (alpha spending: alpha_i = 0.05 * 6/(pi^2 i^2), z_bar = norm.isf(alpha_i / 2))."""
from __future__ import annotations

import math

import numpy as np

from forex.self_improving.llm_bench import harness as H

DEV_MKTS = ["EURUSD", "USDJPY", "USDCAD", "EURJPY", "XAUUSD", "SP", "DAX", "BTCUSD"]
VAL_MKTS = ["GBPUSD", "AUDUSD", "USDCHF", "GBPJPY", "XAGUSD", "NSDQ", "NIKKEI", "ETHUSD"]
K_SHIFTS, RHO, NW_LAG = 20, 0.3, 24


def fname(m):
    return f"MULTI__{m}_H1.parquet"


def run_group(code, group, upto):
    spec = [{"name": fname(m), "path": str(H.DATA / fname(m)), "n": H.split_idx(fname(m)) if upto == "train" else len(H.load(fname(m)))} for m in group]
    return H.sandbox(code, spec)


def nw_t(x, lag=NW_LAG):
    x = np.asarray(x, float)
    n = len(x)
    if n < 100 or x.std() == 0:
        return 0.0
    m = x.mean()
    e = x - m
    v = (e * e).mean()
    for l in range(1, lag + 1):
        v += 2 * (1 - l / (lag + 1)) * (e[l:] * e[:-l]).mean()
    return float(m / math.sqrt(max(v, 1e-30) / n))


def skill_z(df, p, lo, hi, rng):
    """timing skill: net return of the positions minus the mean over K circular shifts of the same positions (same exposure and turnover, wrong timing)."""
    r, _ = H.net_returns(df, p)
    n = len(df)
    sh = np.zeros(n)
    for _ in range(K_SHIFTS):
        sh += H.net_returns(df, np.roll(p, int(rng.integers(500, n - 500))))[0]
    d = (r - sh / K_SHIFTS)[lo:hi]
    return nw_t(d), float(r[lo:hi].sum())


def combine(zs):
    n = len(zs)
    return float(sum(zs) / math.sqrt(n + n * (n - 1) * RHO)) if n else 0.0


def z_bar(i):
    from statistics import NormalDist
    alpha = 0.05 * 6 / (math.pi ** 2 * i ** 2)
    return NormalDist().inv_cdf(1 - alpha / 2)


def dev_feedback(code):
    """what the agent may see: TRAIN-period metrics on the DEV markets."""
    pos, errs = run_group(code, DEV_MKTS, "train")
    rows = []
    for m in DEV_MKTS:
        f = fname(m)
        if f not in pos:
            rows.append((m, errs.get(f) or errs.get("_all") or "no output"))
            continue
        df = H.load(f).iloc[: H.split_idx(f)].reset_index(drop=True)
        rows.append((m, H.metrics(df, pos[f], 0, len(df), H.bpy(f))))
    return rows


def causal_and_active(code, group, pos):
    ok = True
    for m in group[:2]:
        f = fname(m)
        if f not in pos:
            return False, False
        n = len(H.load(f))
        cut = H.split_idx(f) + (n - H.split_idx(f)) // 2
        p2, _ = H.sandbox(code, [{"name": f, "path": str(H.DATA / f), "n": cut}])
        if f not in p2 or not np.array_equal(p2[f][: cut - 1], pos[f][: cut - 1]):
            ok = False
    per_bar = [np.abs(np.diff(pos[fname(m)])).astype(bool).mean() for m in group if fname(m) in pos]
    active = bool(per_bar) and float(np.median(per_bar)) < 0.2 and float(np.median(per_bar)) > 0
    return ok, active


def validate(code, trial_no, seed=0):
    rng = np.random.default_rng(seed)
    posA, eA = run_group(code, DEV_MKTS, "full")
    posB, eB = run_group(code, VAL_MKTS, "full")
    out = dict(trial=trial_no, z_bar=z_bar(trial_no))
    if eA or eB or len(posA) < len(DEV_MKTS) or len(posB) < len(VAL_MKTS):
        out.update(valid=False, error=str((eA or eB))[:200], promoted=False)
        return out
    out["valid"] = True
    out["causal"], out["active"] = causal_and_active(code, DEV_MKTS, posA)
    cA, cB, cC, nA, nB, nC = [], [], [], [], [], []
    for m in DEV_MKTS:
        f = fname(m); df = H.load(f); lo = H.split_idx(f)
        z, net = skill_z(df, posA[f], lo, len(df), rng); cA.append(z); nA.append(net)
    for m in VAL_MKTS:
        f = fname(m); df = H.load(f); lo = H.split_idx(f)
        z, net = skill_z(df, posB[f], lo, len(df), rng); cB.append(z); nB.append(net)
        z, net = skill_z(df, posB[f], 0, lo, rng); cC.append(z); nC.append(net)
    out.update(zA=combine(cA), zB=combine(cB), zC=combine(cC), netA=float(np.mean(nA)), netB=float(np.mean(nB)), netC=float(np.mean(nC)))
    out["promoted"] = bool(out["causal"] and out["active"] and min(out["zA"], out["zB"], out["zC"]) >= out["z_bar"] and min(out["netA"], out["netB"], out["netC"]) > 0)
    return out
