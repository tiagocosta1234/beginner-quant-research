"""Scoring harness (local replica of a 'who is the best AI trader' bench): 8 gates per lane, 70% train / 30% sealed holdout (by time), controls = buy-and-hold and coin flips,
real bid/ask costs, rollover rule enforced, causality (truncation) test, placebo (circular shifts of the model's own positions)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path("D:/finance/llm_bench/data")
HERE = Path(__file__).resolve().parent
SLIP = 1e-5
SPLIT = 0.70
LANES = {"MULTI": sorted(p.name for p in DATA.glob("MULTI__*.parquet")), "TICK": sorted(p.name for p in DATA.glob("TICK__*.parquet"))}
_cache = {}


def load(fname):
    if fname not in _cache:
        _cache[fname] = pd.read_parquet(DATA / fname)
    return _cache[fname]


def split_idx(fname):
    return int(len(load(fname)) * SPLIT)


def net_returns(df, p):
    """per-bar net return (additive, 1x notional). p[i] is decided at the close of bar i and held over bar i+1 (entered at its open at bid/ask);
    no position change is allowed when the open of bar i+1 is in server hours 23/0 (rollover rule)."""
    n = len(df)
    o, bo, ao = df.open.to_numpy(), df.bo.to_numpy(), df.ao.to_numpy()
    hr = (df.t.to_numpy() // 3600) % 24
    q = np.zeros(n)
    q[1:] = p[:-1].astype(float)
    blocked = np.isin(hr, (23, 0))
    if blocked.any():
        for j in np.nonzero(blocked)[0]:
            if j > 0:
                q[j] = q[j - 1]
    dq = np.abs(np.diff(q, prepend=0.0))
    hs = (ao - bo) / (2 * o)
    r = np.zeros(n)
    r[:-1] = q[:-1] * (o[1:] / o[:-1] - 1)
    return r - dq * (hs + SLIP), int((dq > 0).sum())


def sandbox(code, spec):
    with tempfile.TemporaryDirectory(dir="D:/finance/llm_bench") as td:
        cp, sp, op = Path(td) / "c.py", Path(td) / "s.json", str(Path(td) / "o.npz")
        cp.write_text(code, encoding="utf-8")
        sp.write_text(json.dumps(spec))
        try:
            r = subprocess.run([sys.executable, "-E", "-P", str(HERE / "sandbox.py"), str(cp), str(sp), op], capture_output=True, text=True, timeout=240,
                               creationflags=0x08000000 if sys.platform == "win32" else 0)
        except subprocess.TimeoutExpired:
            return {}, {"_all": "timeout (240 s)"}
        if r.returncode != 0:
            return {}, {"_all": (r.stderr.strip().splitlines() or ["crash"])[-1][:300]}
        with np.load(op) as z:
            out = {k: z[k] for k in z.files}
        with open(op + ".err.json") as fh:
            errs = json.load(fh)
        return out, errs


def run(code, lane, upto="train"):
    """upto='train': the strategy only ever receives the TRAIN rows. 'full': it receives all rows (history for warm-up); metrics are then taken on the holdout slice."""
    spec = [{"name": f, "path": str(DATA / f), "n": split_idx(f) if upto == "train" else len(load(f))} for f in LANES[lane]]
    return sandbox(code, spec)


def bpy(fname):
    return 24 * 365 if "H1" in fname else 60 * 24 * 365


def metrics(df, p, lo, hi, bars_per_year):
    r, _ = net_returns(df, p)
    x = r[lo:hi]
    eq = np.cumsum(x)
    sh = x.mean() / x.std() * np.sqrt(bars_per_year) if len(x) and x.std() > 0 else 0.0
    return dict(net=float(eq[-1]) if len(eq) else 0.0, sharpe=float(sh), trades=int((np.abs(np.diff(np.r_[0, p[lo:hi]])) > 0).sum()),
                mdd=float((np.maximum.accumulate(eq) - eq).max()) if len(eq) else 0.0)


def train_report(code):
    """what a model sees after a dev round: per-source TRAIN metrics only."""
    out = {}
    for lane in LANES:
        pos, errs = run(code, lane, "train")
        rows = []
        for f in LANES[lane]:
            if f not in pos:
                rows.append((f, errs.get(f) or errs.get("_all") or "no output"))
                continue
            df = load(f).iloc[: split_idx(f)].reset_index(drop=True)
            rows.append((f, metrics(df, pos[f], 0, len(df), bpy(f))))
        out[lane] = rows
    return out


def score(code, seed=0):
    """the full evaluation on the sealed holdout, 8 gates per lane."""
    rng = np.random.default_rng(seed)
    res = {}
    for lane, files in LANES.items():
        pos, errs = run(code, lane, "full")
        det, g = {}, {}
        ok = [f for f in files if f in pos]
        g["G1_valid"] = bool(not errs and len(ok) == len(files))
        caus = bool(ok)
        for f in ok[:3]:
            n = len(load(f))
            cut = split_idx(f) + (n - split_idx(f)) // 2
            p2, _ = sandbox(code, [{"name": f, "path": str(DATA / f), "n": cut}])
            if f not in p2 or not np.array_equal(p2[f][: cut - 1], pos[f][: cut - 1]):
                caus = False
        g["G2_causal"] = caus
        nets, bh, trs, trn, plac = [], [], [], [], []
        for f in ok:
            df = load(f)
            lo, n = split_idx(f), len(df)
            m, mt = metrics(df, pos[f], lo, n, bpy(f)), metrics(df, pos[f], 0, lo, bpy(f))
            b = metrics(df, np.ones(n, np.int8), lo, n, bpy(f))
            nets.append(m["net"]); bh.append(b["net"]); trs.append(m["trades"]); trn.append(mt["net"])
            base = net_returns(df, pos[f])[0][lo:].sum()
            k = 0
            for _ in range(60):
                ps = np.roll(pos[f], int(rng.integers(500, n - 500)))
                k += net_returns(df, ps)[0][lo:].sum() < base
            plac.append(k / 60)
            det[f] = dict(holdout_net=round(m["net"], 4), train_net=round(mt["net"], 4), buyhold=round(b["net"], 4), trades=m["trades"], sharpe=round(m["sharpe"], 2), placebo_pct=round(plac[-1], 2))
        if ok:
            per_bar = [det[f]["trades"] / (len(load(f)) - split_idx(f)) for f in ok]
            nn, bb, tn = np.array(nets), np.array(bh), np.array(trn)
            g["G3_active"] = bool(np.median(trs) >= 20 and np.median(per_bar) < 0.2)
            g["G4_profitable"] = bool(np.median(nn) > 0)
            g["G5_breadth"] = bool(np.mean(nn > 0) >= 0.6)
            g["G6_beats_buyhold"] = bool(np.mean(nn > bb) >= 0.6)
            g["G7_placebo"] = bool(np.median(plac) >= 0.9)
            g["G8_stable"] = bool(np.mean((nn > 0) & (tn > 0)) >= 0.6)   # profitable on BOTH the train and the sealed period in >= 60% of sources
        else:
            for k in ("G3_active", "G4_profitable", "G5_breadth", "G6_beats_buyhold", "G7_placebo", "G8_stable"):
                g[k] = False
        res[lane] = dict(gates=g, passed=int(sum(g.values())), detail=det, errors=errs, sources=len(files),
                         sources_positive=int((np.array(nets) > 0).sum()) if nets else 0, buyhold_positive=int((np.array(bh) > 0).sum()) if bh else 0)
    return res
