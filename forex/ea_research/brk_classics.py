"""BRK-CLASSICS exactly as in PREREG_BRK_CLASSICS.md: Williams volatility breakout, 5-minute ORB, cash-gap go/fade, inside-day breakout.
   python -m forex.ea_research.brk_classics --dry | (no flag) run"""
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.breakouts import local_clock, session
from forex.ea_research.brk_exits import exits
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS, nw_t, sim
from forex.ea_research.index_oos import MKTS as MT5BROKER_IDX, load_mt5broker
from forex.ea_research.orb_refine import daily_table

END = pd.Timestamp("2026-10-03").timestamp()
H, M = 3600, 60
DEV, VAL, Y26 = ("2022-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-10-02")
INDICES = ("SP", "NSDQ", "DOW", "DAX", "NIKKEI", "ASX")


def ctrl(D, rng, a, b, kend, R):
    if b <= a:
        return np.nan
    kc = int(rng.integers(a, b)); sc = 1 if rng.random() < 0.5 else -1
    ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
    if kc >= kend or not (R > 0 and R >= 2 * (D["ao"][kc] - D["bo"][kc])):
        return np.nan
    x = exits(D, kc, kend, sc, ec, R)
    return x[3] if x else np.nan


def stop_entry(D, a, b, up_lvl, dn_lvl):
    up = np.flatnonzero(D["ah"][a:b] >= up_lvl); dn = np.flatnonzero(D["bl"][a:b] <= dn_lvl)
    ku, kd = (a + up[0] if len(up) else None), (a + dn[0] if len(dn) else None)
    if (ku is None and kd is None) or (ku is not None and ku == kd):
        return None
    side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
    k = ku if side > 0 else kd
    return k, side, (max(up_lvl, D["ao"][k]) if side > 0 else min(dn_lvl, D["bo"][k]))


def market(args):
    sym, end, mt5broker = args
    if mt5broker:
        D = load_mt5broker(sym, end); tz, op_s, cl_s = MT5BROKER_IDX[sym]; is_idx = True
    else:
        D = load(sym, end); tz, op_s, cl_s = session(sym); is_idx = sym in INDICES
    t = D["t"]
    lc = local_clock(t, tz)
    dt = daily_table(D)
    rngd = (dt.h - dt.l)
    prev_rng = rngd.shift(1)
    inside_prev = (dt.h.shift(1) <= dt.h.shift(2)) & (dt.l.shift(1) >= dt.l.shift(2))
    rng = np.random.default_rng(zlib.crc32(sym.encode()) + 3)
    mid_o = (D["bo"] + D["ao"]) / 2
    mid_c = (D["bc"] + D["ac"]) / 2
    rows = []
    days = np.unique(lc // 86400)
    prev_close = None
    for d in days:
        base = d * 86400
        i0 = np.searchsorted(lc, base + op_s)
        w1 = np.searchsorted(lc, base + op_s + 3 * H)
        xe = np.searchsorted(lc, base + cl_s)
        if xe >= len(t) or lc[min(xe, len(t) - 1)] // 86400 != d:
            xe -= 1
        ok_day = i0 < len(t) and lc[i0] // 86400 == d and lc[i0] < base + op_s + 5 * M and xe > i0 + 60 and w1 > i0 + 30
        pc = prev_close
        if xe > 0 and xe < len(t) and lc[xe] // 86400 == d:
            prev_close = mid_c[xe - 1] if lc[xe] >= base + cl_s - M else prev_close
        if not ok_day:
            continue
        cap = np.searchsorted(t, (t[i0] // 86400) * 86400 + 22 * H + 55 * M)
        kend = min(xe, cap, len(t) - 1)
        sday = t[i0] // 86400
        if sday not in dt.index or not np.isfinite(dt.at[sday, "atr_prev"]):
            continue
        atr, pr = dt.at[sday, "atr_prev"], prev_rng.get(sday, np.nan)
        O = mid_o[i0]
        day = pd.Timestamp(d * 86400, unit="s")
        def add(cell, k, side, e, R, a, b, x4=None):
            if k is None or k >= kend or not (R > 0 and R >= 2 * (D["ao"][k] - D["bo"][k])):
                return
            r = x4 if x4 is not None else exits(D, k, kend, side, e, R)
            val = r if np.isscalar(r) else (r[3] if r else None)
            if val is None or not np.isfinite(val):
                return
            rows.append(dict(mkt=sym, cell=cell, day=day, side=side, t_entry=int(t[k]), R=val, C=ctrl(D, rng, a, b, kend, R)))
        if not mt5broker and np.isfinite(pr) and pr > 0:
            for cell, kf in (("C1_williams_0.5", 0.5), ("C2_williams_0.25", 0.25)):
                se = stop_entry(D, i0, w1, O + kf * pr, O - kf * pr)
                if se:
                    k, side, e = se
                    add(cell, k, side, e, abs(e - O), i0, w1)
        if is_idx and i0 + 5 < kend:
            o5, c5 = mid_o[i0], mid_c[i0 + 4]
            sp = D["ao"][i0 + 4] - D["bo"][i0 + 4]
            if abs(c5 - o5) >= sp:
                side = 1 if c5 > o5 else -1
                k = i0 + 5
                e = D["ao"][k] if side > 0 else D["bo"][k]
                stop = D["bl"][i0:i0 + 5].min() if side > 0 else D["ah"][i0:i0 + 5].max()
                add("C3_5min_orb", k, side, e, abs(e - stop), i0 + 5, min(i0 + 65, kend))
        if is_idx and not mt5broker and pc is not None and atr > 0:
            gap = (O - pc) / atr
            k = i0 + 5
            if abs(gap) >= 0.3 and k < kend:
                side = int(np.sign(gap))
                e = D["ao"][k] if side > 0 else D["bo"][k]
                add("C4_gap_go", k, side, e, 0.5 * atr, i0 + 5, min(i0 + 65, kend))
                fs = -side
                ef = D["ao"][k] if fs > 0 else D["bo"][k]
                tgt = pc
                if fs * (tgt - ef) > 0:
                    r = sim(D, k, fs, ef, ef - fs * 0.5 * atr, tgt, kend)
                    if r is not None:
                        add("C5_gap_fade", k, fs, ef, 0.5 * atr, i0 + 5, min(i0 + 65, kend), x4=r[0])
    if not mt5broker:                                                     # C6 inside day (server days)
        day_, sod = t // 86400, t % 86400
        st = np.flatnonzero(np.r_[True, day_[1:] != day_[:-1]]); en = np.r_[st[1:], len(t)]
        for a, b in zip(st, en):
            sd = int(day_[a])
            if sd not in dt.index or not bool(inside_prev.get(sd, False)):
                continue
            ph, pl = dt.h.shift(1).get(sd), dt.l.shift(1).get(sd)
            wa, wb = a + np.searchsorted(sod[a:b], H + 5 * M), a + np.searchsorted(sod[a:b], 20 * H)
            ke = min(a + np.searchsorted(sod[a:b], 22 * H + 55 * M), len(t) - 1)
            if wb <= wa or ke <= wa:
                continue
            se = stop_entry(D, wa, wb, ph, pl)
            if se:
                k, side, e = se
                R = abs(e - (pl if side > 0 else ph))
                if k < ke and R > 0 and R >= 2 * (D["ao"][k] - D["bo"][k]):
                    x = exits(D, k, ke, side, e, R)
                    if x:
                        rows.append(dict(mkt=sym, cell="C6_inside_day", day=pd.Timestamp(sd * 86400, unit="s"), side=side, t_entry=int(t[k]), R=x[3], C=ctrl(D, rng, wa, wb, ke, R)))
    return rows


def collect(end):
    jobs = [(s, end, False) for s in SYMS] + [(s, end, True) for s in MT5BROKER_IDX]
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, jobs))
    df = pd.DataFrame([r for rr in res for r in rr])
    return df[df.day >= DEV[0]]


def dry():
    t0 = time.time()
    df = collect(END)
    print(f"{time.time() - t0:.0f}s")
    df["per"] = np.where(df.day <= DEV[1], "DEV", np.where(df.day <= VAL[1], "VAL", "2026"))
    df["src"] = np.where(df.mkt.isin(list(MT5BROKER_IDX)), "MT5", "MT5")
    print(df.groupby(["cell", "src", "per"]).size().unstack().fillna(0).astype(int))
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    bad = 0
    for s in ("NSDQ", "EURUSD"):
        f, p = pd.DataFrame(market((s, END, False))), pd.DataFrame(market((s, cut, False)))
        f, p = f[f.t_entry < cut - 2 * 86400].reset_index(drop=True), p[p.t_entry < cut - 2 * 86400].reset_index(drop=True)
        bad += int(not (len(f) == len(p) and np.allclose(f.R, p.R)))
    print("truncation test:", "PASS" if bad == 0 else f"FAIL {bad}")
    x = df[(df.mkt == "NSDQ") & (df.day == "2024-06-12")]
    print("hand check NSDQ 2024-06-12:", x[["cell", "side", "t_entry", "R"]].assign(t_entry=pd.to_datetime(x.t_entry, unit="s").astype(str)).round(3).to_dict("records"))


def run():
    df = collect(END)
    df.to_parquet("data/si_ledgers/BRK_CLASSICS.parquet")
    mt5 = df[~df.mkt.isin(list(MT5BROKER_IDX))]
    for cell, g in forex.groupby("cell"):
        r = {}
        for lab, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)):
            s = g[(g.day >= a) & (g.day <= b)]
            r[lab] = (len(s), s.R.mean(), nw_t(s.groupby("day").R.mean().to_numpy()), s.C.mean())
        gate = [r["DEV"][1] >= 0.05 and r["DEV"][2] >= 2.6, r["VAL"][1] > 0 and r["VAL"][2] >= 1.65, r["DEV"][1] - r["DEV"][3] >= 0.05 and r["VAL"][1] - r["VAL"][3] >= 0.05]
        print(f"{cell}: " + " | ".join(f"{k} n{v[0]} {v[1]:+.3f} (t {v[2]:+.2f}) ctl {v[3]:+.3f}" for k, v in r.items()) + f" | gates {''.join('Y' if x else 'n' for x in gate)} PASS {all(gate)}")
        if not g.mkt.isin(INDICES).all():
            print("    by class DEV/VAL/2026: " + " | ".join(f"{c} " + "/".join(f"{x[(x.day >= a) & (x.day <= b)].R.mean():+.3f}" for a, b in (DEV, VAL, Y26)) for c, x in g.assign(c=g.mkt.map(mclass)).groupby("c")))
        else:
            print("    by index (all years): " + ", ".join(f"{m} {x.R.mean():+.3f}" for m, x in g.groupby("mkt")) + " | by year: " + ", ".join(f"{y} {x.R.mean():+.3f}" for y, x in g.groupby(g.day.dt.year)))
    f = df[df.mkt.isin(list(MT5BROKER_IDX)) & (df.cell == "C3_5min_orb")]
    print(f"C3 out-of-sample (FTSE/CAC/Russell): n {len(f)} {f.R.mean():+.3f} (t {nw_t(f.groupby('day').R.mean().to_numpy()):+.2f}) ctl {f.C.mean():+.3f} | "
          + ", ".join(f"{m} {x.R.mean():+.3f}" for m, x in f.groupby("mkt")) + " | by year " + ", ".join(f"{y} {x.R.mean():+.3f}" for y, x in f.groupby(f.day.dt.year)))


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
