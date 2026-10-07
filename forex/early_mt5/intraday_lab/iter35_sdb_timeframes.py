"""Iteration 35 (pre-registered in intraday_lab/PREREG.md): the frozen SDB rule on other chart periods (M30, H2, H4) of MT5 broker gold, checked on the Databento GC feed.
   python -m mt5broker.intraday_lab.iter35_sdb_timeframes --selftest    (tf = 3600 must reproduce sdb.simulate exactly)
   python -m mt5broker.intraday_lab.iter35_sdb_timeframes --dry-run     (counts only)
   python -m mt5broker.intraday_lab.iter35_sdb_timeframes               (the pre-registered run)"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from mt5broker.forward_test import config
from mt5broker.intraday_lab import iter31_feed_robustness as it31
from mt5broker.intraday_lab import sdb

TFS = {"M30": 1800, "H1": 3600, "H2": 7200, "H4": 14400}


def bars_tf(m1, tf):
    g = (m1["t"] // tf) * tf
    df = pd.DataFrame({"g": g, "bo": m1["bo"], "bh": m1["bh"], "bl": m1["bl"], "bc": m1["bc"]})
    a = df.groupby("g").agg(o=("bo", "first"), h=("bh", "max"), l=("bl", "min"), c=("bc", "last"))
    return a.index.values.astype(np.int64), a.o.values, a.h.values, a.l.values, a.c.values


def simulate_tf(sym, m1, tf, pct=1.9, expiry=9, K=23, D=3, S=7, bp=9, start="2021-10-01", end="2026-10-02"):
    """sdb.simulate with the chart period as a parameter (everything else identical)."""
    t1 = m1["t"]
    ht, ho, hh, hl, hc = bars_tf(m1, tf); sig = sdb.stoch_signal(hc, K, D, S); up, lo_b = sdb.bands(ho, hh, hl, hc, bp)
    dd, dH, dL = sdb.daily_hl(m1); dr = pd.Series(dH - dL).rolling(20).mean().shift(1).values
    t_lo, t_hi = int(pd.Timestamp(start).timestamp()), int(pd.Timestamp(end).timestamp()) + 86400
    comm = sdb.commission_price(sym, float(np.nanmedian(m1["bc"]))); trades = []
    pend = {1: None, -1: None}; busy_until = -1
    i0 = int(np.searchsorted(ht, t_lo)); n = len(ht)
    for i in range(max(i0, 30), n):
        t0 = int(ht[i])
        if t0 > t_hi:
            break
        for sd_ in (1, -1):
            if pend[sd_] is not None and i - pend[sd_]["i"] >= expiry:
                pend[sd_] = None
        if t0 >= busy_until and i >= 5:
            s3, s2, s1 = sig[i - 3], sig[i - 2], sig[i - 1]
            turn_down = s3 < s2 and s2 > s1; turn_up = s3 > s2 and s2 < s1; open3 = ho[i - 3]
            buy = open3 < up[i - 4] and turn_down; sell = open3 > lo_b[i - 4] and turn_up
            if buy or sell:
                d = int(np.searchsorted(dd, t0 // 86400)) - 1
                if d >= 0:
                    j0 = int(np.searchsorted(t1, t0))
                    if buy and dH[d] > m1["ao"][j0]:
                        pend[1] = dict(i=i, side=1, level=float(dH[d]), atr=float(dr[d]))
                    elif sell and not buy and dL[d] < m1["bo"][j0]:
                        pend[-1] = dict(i=i, side=-1, level=float(dL[d]), atr=float(dr[d]))
        j0 = int(np.searchsorted(t1, t0)); j1 = int(np.searchsorted(t1, t0 + tf))
        for side in (1, -1):
            pd_ = pend[side]
            if pd_ is None or j1 <= j0:
                continue
            L = pd_["level"]
            hit = (m1["ah"][j0:j1] >= L) if side > 0 else (m1["bl"][j0:j1] <= L)
            if not hit.any():
                continue
            jf = j0 + int(np.argmax(hit)); pend[side] = None
            p_fill = max(L, m1["ao"][jf]) if side > 0 else min(L, m1["bo"][jf])
            sd = L * pct / 100.0
            if not np.isfinite(sd) or sd <= 0:
                continue
            sl = L - side * sd; tp = L + side * sd
            if side > 0:
                stop_hit = m1["bl"][jf:] <= sl; tp_hit = m1["bh"][jf:] >= tp
            else:
                stop_hit = m1["ah"][jf:] >= sl; tp_hit = m1["al"][jf:] <= tp
            a = int(np.argmax(stop_hit)) if stop_hit.any() else 10**12; b = int(np.argmax(tp_hit)) if tp_hit.any() else 10**12
            if a == b == 10**12:
                busy_until = int(t1[-1]) + 1; continue
            if a <= b:
                je = jf + a; op = m1["bo"][je] if side > 0 else m1["ao"][je]; px = min(sl, op) if side > 0 else max(sl, op)
            else:
                je = jf + b; px = tp
            pnl = (px - p_fill) * side - comm
            trades.append(dict(t_entry=int(t1[jf]), t_exit=int(t1[je]), side=side, level=L, entry=p_fill, exit=px, stop=sd, R=pnl / sd, pnl=pnl))
            busy_until = max(busy_until, int(t1[je]) + 60)
    t = pd.DataFrame(trades)
    if len(t):
        t["when"] = pd.to_datetime(t.t_entry, unit="s")
    return t


def tstat(r):
    r = np.asarray(r, dtype=float)
    return float(r.mean() / (r.std(ddof=1) / np.sqrt(len(r)))) if len(r) > 2 and r.std(ddof=1) > 0 else float("nan")


def main():
    fm = sdb.load_m1("XAUUSD")
    if "--selftest" in sys.argv:
        a = sdb.simulate("XAUUSD", fm, **config.RULE); b = simulate_tf("XAUUSD", fm, 3600, **config.RULE)
        print("selftest tf=3600:", len(a), "vs", len(b), "| identical R:", bool(len(a) == len(b) and np.allclose(a.R.values, b.R.values)), "| identical entries:", bool((a.t_entry.values == b.t_entry.values).all()) if len(a) == len(b) else False)
        return
    gm = it31.gc_m1(); months = 60.0
    res = {}
    for name, tf in TFS.items():
        f = simulate_tf("XAUUSD", fm, tf, **config.RULE); g = simulate_tf("XAUUSD", gm, tf, start="2019-06-19", end="2026-09-25", **config.RULE)
        res[name] = (f, g)
        if "--dry-run" in sys.argv:
            print(f"{name}: MT5 broker trades {len(f)} ({len(f) / months:.1f} a month), GC trades {len(g)}")
    if "--dry-run" in sys.argv:
        return
    print("tf | MT5 DEV n mean (t) | VAL n mean (t) | years positive | a month | GC overlap n mean (t) | GC PRE n mean (t)")
    hits = []
    for name, (f, g) in res.items():
        ph = np.where(f.when < "2024-01-01", "dev", np.where(f.when < "2025-01-01", "val", "hold")); f = f.assign(ph=ph, y=f.when.dt.year)
        dv, vl = f[f.ph == "dev"], f[f.ph == "val"]; yrs = f[f.y >= 2022].groupby("y").R.mean(); ypos = int((yrs > 0).sum())
        go, gp = g[g.when >= "2021-10-01"], g[g.when < "2021-10-01"]
        print(f"{name:<3} | {len(dv):3d} {dv.R.mean():+.3f} ({tstat(dv.R):+.2f}) | {len(vl):3d} {vl.R.mean():+.3f} ({tstat(vl.R):+.2f}) | {ypos}/5 {({int(k): round(float(v), 3) for k, v in yrs.items()})} | {len(f) / months:.1f} | {len(go):3d} {go.R.mean():+.3f} ({tstat(go.R):+.2f}) | {len(gp):3d} {gp.R.mean():+.3f} ({tstat(gp.R):+.2f})", flush=True)
        if name != "H1" and dv.R.mean() > 0 and tstat(dv.R) >= 1.5 and vl.R.mean() > 0 and ypos >= 3 and go.R.mean() > 0:
            hits.append(name)
        f.to_csv(f"D:/finance/scratch/lab/iter35_{name}_mt5broker.csv", index=False)
    print("PRE-REGISTERED HITS (new timeframes only):", hits)
    for name in hits:
        h = res[name][0]; h = h[h.when >= "2025-01-01"]; print("HOLD (printed because the hit rule passed):", name, f"n {len(h)} mean {h.R.mean():+.3f} t {tstat(h.R):+.2f}")
    h1 = res["H1"][0]
    for name in TFS:
        if name == "H1":
            continue
        o = res[name][0]; ge = h1.when.values; m = 0
        for w, s in zip(o.when.values, o.side.values):
            m += bool(((h1.side.values == s) & (np.abs((ge - w) / np.timedelta64(1, "h")) <= 24)).any())
        print(f"overlap: {m} of {len(o)} {name} trades have a same-side H1 trade within 24 h ({m / max(len(o), 1) * 100:.0f}%)")


if __name__ == "__main__":
    main()
