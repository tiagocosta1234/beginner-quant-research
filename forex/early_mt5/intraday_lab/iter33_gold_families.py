"""Iteration 33 (pre-registered in intraday_lab/PREREG.md): six frozen intraday families on MT5 broker gold, 15-minute bars.
   python -m mt5broker.intraday_lab.iter33_gold_families --dry-run     (counts only)
   python -m mt5broker.intraday_lab.iter33_gold_families               (the pre-registered run)"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from mt5broker.intraday_lab import lab

TF = 15
H = 3600


def prep(b):
    d = pd.DataFrame({"t": b.t, "day": b.day, "tod": b.t % 86400, "h": b.bh, "l": b.bl, "c": b.bc})
    g = d.groupby("day").agg(dh=("h", "max"), dl=("l", "min"))
    prev = g.shift(1)
    b.pdh = d.day.map(prev.dh).values; b.pdl = d.day.map(prev.dl).values; b.tod = d.tod.values
    b.atr14 = b.atr(14)
    c = pd.Series(b.bc)
    b.ema50 = c.ewm(span=50, adjust=False).mean().values; b.ema200 = c.ewm(span=200, adjust=False).mean().values
    dlt = c.diff(); up = dlt.clip(lower=0).ewm(alpha=1 / 3, adjust=False).mean(); dn = (-dlt.clip(upper=0)).ewm(alpha=1 / 3, adjust=False).mean()
    b.rsi3 = (100 - 100 / (1 + up / dn)).values
    ma = c.rolling(20).mean(); sd = c.rolling(20).std(ddof=0)
    b.bbu = (ma + 2 * sd).values; b.bbl = (ma - 2 * sd).values; b.bw = ((4 * sd) / ma).values
    b.bwq = pd.Series(b.bw).rolling(480).quantile(0.10).values
    return b


def first_per_day(idx, dirs, stops, extra, days):
    seen = set(); keep = []
    for k, i in enumerate(idx):
        if days[i] in seen:
            continue
        seen.add(days[i]); keep.append(k)
    keep = np.array(keep, dtype=int)
    return idx[keep], dirs[keep], stops[keep], extra[keep]


def orb(b, r0, r1, w0, w1, t_exit, tp):
    """range of bars with tod in [r0, r1), first close beyond it with tod in [w0, w1)."""
    idx, dirs, stops, mbs = [], [], [], []
    price = b.mid
    order = np.argsort(b.t, kind="stable")
    days = np.unique(b.day)
    # group indices by day
    start = np.searchsorted(b.day, days, side="left"); end = np.searchsorted(b.day, days, side="right")
    for s, e in zip(start, end):
        tod = b.tod[s:e]; m = (tod >= r0) & (tod < r1)
        if m.sum() < 2:
            continue
        rh = b.bh[s:e][m].max(); rl = b.bl[s:e][m].min(); rng = rh - rl; px = price[s:e][m].mean()
        if rng / px < 0.0015 or rng / px > 0.015:
            continue
        for k in range(s, e):
            if w0 <= b.tod[k] < w1:
                if b.bc[k] > rh or b.bc[k] < rl:
                    idx.append(k); dirs.append(1 if b.bc[k] > rh else -1); stops.append(rng); mbs.append(max(2, int((t_exit - b.tod[k]) // (TF * 60)) - 1)); break
    return np.array(idx, dtype=int), np.array(dirs, dtype=int), np.array(stops, dtype=float), np.array(mbs, dtype=int)


def f_lon(b):
    i, d, s, mb = orb(b, 3 * H, 10 * H, 10 * H, 14 * H, 18 * H, 1.5); return i, d, s, 1.5, mb


def f_ny(b):
    i, d, s, mb = orb(b, int(16.5 * H), 17 * H, 17 * H, 20 * H, 22 * H, 1.5); return i, d, s, 1.5, mb


def f_pd(b):
    long_ = (b.bc > b.pdh) & (b.tod >= 10 * H) & (b.tod < 20 * H); short = (b.bc < b.pdl) & (b.tod >= 10 * H) & (b.tod < 20 * H)
    sig = np.flatnonzero((long_ | short) & np.isfinite(b.atr14)); dirs = np.where(long_[sig], 1, -1); stops = 2 * b.atr14[sig]
    i, d, s, _ = first_per_day(sig, dirs, stops, stops, b.day); return i, d, s, 2.0, 48


def f_sq(b):
    prevsq = np.r_[False, (b.bw[:-1] <= b.bwq[:-1])]
    long_ = prevsq & (b.bc > b.bbu); short = prevsq & (b.bc < b.bbl)
    sig = np.flatnonzero((long_ | short) & np.isfinite(b.atr14)); dirs = np.where(long_[sig], 1, -1)
    return sig, dirs, 1.5 * b.atr14[sig], 2.0, 32


def f_pb(b):
    long_ = (b.ema50 > b.ema200) & (b.rsi3 < 10); short = (b.ema50 < b.ema200) & (b.rsi3 > 90)
    sig = np.flatnonzero((long_ | short) & np.isfinite(b.atr14) & (b.t > b.t[0] + 200 * TF * 60)); dirs = np.where(long_[sig], 1, -1)
    return sig, dirs, 2 * b.atr14[sig], 1.0, 16


def f_fb(b):
    idx, dirs, stops = [], [], []; n = b.n
    for i in range(1, n - 6):
        if not (np.isfinite(b.pdh[i]) and np.isfinite(b.atr14[i])):
            continue
        for side, level, ext in ((-1, b.pdh[i], b.bh[i]), (1, b.pdl[i], b.bl[i])):
            broke = ext > level if side < 0 else ext < level
            if not broke:
                continue
            hi = b.bh[i]; lo = b.bl[i]
            for j in range(i + 1, i + 5):
                hi = max(hi, b.bh[j]); lo = min(lo, b.bl[j])
                if (side < 0 and b.bc[j] < level) or (side > 0 and b.bc[j] > level):
                    px = b.bc[j]; stp = (hi + 0.5 * b.atr14[j] - px) if side < 0 else (px - (lo - 0.5 * b.atr14[j]))
                    if stp > 0:
                        idx.append(j); dirs.append(side); stops.append(stp)
                    break
    idx = np.array(idx, dtype=int); o = np.argsort(idx, kind="stable")
    return idx[o], np.array(dirs, dtype=int)[o], np.array(stops, dtype=float)[o], 1.5, 24


FAMS = {"F1 LON_ORB": f_lon, "F2 NY_ORB30": f_ny, "F3 PD_BREAK": f_pd, "F4 SQUEEZE": f_sq, "F5 PULLBACK": f_pb, "F6 FAILED_BREAK": f_fb}


def tstat(r):
    return lab.stats(r)["t"]


def main():
    dry = "--dry-run" in sys.argv
    b = prep(lab.Bars("XAUUSD", TF)); months = (b.t[-1] - b.t[0]) / 86400 / 30.4
    print(f"XAUUSD M{TF} bars {b.n:,}, {pd.to_datetime(b.t[0], unit='s')} .. {pd.to_datetime(b.t[-1], unit='s')}, months {months:.1f}", flush=True)
    hits = []
    for name, fn in FAMS.items():
        idx, dirs, stops, tp, mb = fn(b)
        rows = {}
        for ph in ("dev", "val", "hold"):
            mask = np.zeros(b.n, bool); mask[b.slice_idx(ph)] = True
            R, ent, ext, yrs, cst = lab.run(b, idx, dirs, stops, tp, mb, phase_mask=mask); rows[ph] = (R, yrs, cst, ent)
        n_all = sum(len(rows[p][0]) for p in rows)
        if dry:
            print(f"{name}: signals {len(idx)}, trades dev {len(rows['dev'][0])} val {len(rows['val'][0])} hold {len(rows['hold'][0])} ({n_all / months:.1f} a month)")
            continue
        Rd, Rv = rows["dev"][0], rows["val"][0]
        Rall = np.concatenate([rows[p][0] for p in rows]); Yall = np.concatenate([rows[p][1] for p in rows])
        sd, sv = lab.stats(Rd, rows["dev"][1], rows["dev"][2]), lab.stats(Rv, rows["val"][1], rows["val"][2])
        ypos = int(sum(Rall[Yall == y].mean() > 0 for y in range(2022, 2027) if (Yall == y).sum() > 0))
        print(f"{name}: n {n_all} ({n_all / months:.1f}/mo) | DEV n {sd['n']} mean {sd['mean']:+.3f} t {sd['t']:+.2f} cost {sd['cost']:.3f}R | VAL n {sv['n']} mean {sv['mean']:+.3f} t {sv['t']:+.2f} | years positive {ypos}/5 | by year {({int(y): round(float(Rall[Yall == y].mean()), 3) for y in np.unique(Yall)})}", flush=True)
        if sd["n"] >= 100 and sd["mean"] > 0 and sd["t"] >= 3.0 and sv["mean"] > 0 and sv["t"] >= 2.0 and ypos >= 4:
            hits.append((name, n_all / months, rows["hold"][0]))
    if not dry:
        print(f"PRE-REGISTERED HITS (k = 6): {len(hits)}")
        for name, pm, Rh in hits:
            st = lab.stats(Rh); print("HOLD (printed because DEV and VAL passed):", name, f"n {st['n']} mean {st['mean']:+.3f} t {st['t']:+.2f}", "| trades a month", round(pm, 1), "(too sparse)" if pm < 8 else "")


if __name__ == "__main__":
    main()
