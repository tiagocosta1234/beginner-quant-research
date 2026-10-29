"""BRK-SWING exactly as in PREREG_BRK_SWING.md: session breakouts held 5 / 10 days with a 2-ATR trail, and D20-aligned intraday breakouts.
   python -m forex.ea_research.brk_swing --dry | (no flag) run"""
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.breakouts import local_clock, session
from forex.ea_research.brk_exits import exits
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS, nw_t
from forex.ea_research.orb_refine import daily_table

END = pd.Timestamp("2026-10-03").timestamp()
H, M = 3600, 60
DEV, VAL, Y26 = ("2022-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-10-02")


def swing(D, k, kend, side, e, R, atr):
    """initial stop -1R; after +1R trail 2 ATR behind the best (previous minute); exit at kend's open."""
    if kend <= k:
        return None
    if side > 0:
        lo, hi, op, x_end = D["bl"][k:kend], D["bh"][k:kend], D["bo"][k:kend], D["bo"][kend]
        best = np.maximum.accumulate(hi)
        best_prev = np.concatenate([[e], best[:-1]])
        lvl = np.where(best_prev - e >= R, np.maximum(e - R, best_prev - 2 * atr), e - R)
        hit = np.flatnonzero(lo <= lvl)
        x = min(lvl[hit[0]], op[hit[0]]) if len(hit) else x_end
    else:
        lo, hi, op, x_end = D["al"][k:kend], D["ah"][k:kend], D["ao"][k:kend], D["ao"][kend]
        best = np.minimum.accumulate(lo)
        best_prev = np.concatenate([[e], best[:-1]])
        lvl = np.where(e - best_prev >= R, np.minimum(e + R, best_prev + 2 * atr), e + R)
        hit = np.flatnonzero(hi >= lvl)
        x = max(lvl[hit[0]], op[hit[0]]) if len(hit) else x_end
    return side * (x - e) / R


def market(args):
    sym, end = args
    D = load(sym, end)
    t = D["t"]
    tz, op_s, cl_s = session(sym)
    lc = local_clock(t, tz)
    dt = daily_table(D)
    hi20, lo20 = dt.h.rolling(20).max().shift(1), dt.l.rolling(20).min().shift(1)
    brk_up = (dt.c > hi20).astype(int); brk_dn = (dt.c < lo20).astype(int)
    fresh = (brk_up.rolling(3).max() - brk_dn.rolling(3).max()).shift(1)            # +1 / -1 / 0 known at the day start
    sdays = np.array(sorted(dt.index))
    sday_t = {}
    day_, sod = t // 86400, t % 86400
    rng = np.random.default_rng(zlib.crc32(sym.encode()) + 21)
    rows = []
    for d in np.unique(lc // 86400):
        base = d * 86400
        i0, i1 = np.searchsorted(lc, base + op_s), np.searchsorted(lc, base + op_s + 30 * M)
        w1 = np.searchsorted(lc, base + op_s + 3 * H)
        xe = np.searchsorted(lc, base + cl_s)
        if xe >= len(t) or lc[min(xe, len(t) - 1)] // 86400 != d:
            xe -= 1
        if i1 >= len(t) or i1 - i0 < 20 or lc[i0] // 86400 != d or w1 <= i1 + 30 or xe <= i1:
            continue
        sday = t[i0] // 86400
        if sday not in dt.index or not np.isfinite(dt.at[sday, "atr_prev"]):
            continue
        atr = dt.at[sday, "atr_prev"]
        cap = np.searchsorted(t, (t[i1] // 86400) * 86400 + 22 * H + 55 * M)
        kday = min(xe, cap, len(t) - 1)
        pos = np.searchsorted(sdays, sday)
        ends = {}
        for n in (5, 10):
            if pos + n - 1 < len(sdays):
                last = sdays[pos + n - 1]
                ends[n] = min(np.searchsorted(t, last * 86400 + 21 * H + 55 * M), len(t) - 1)
        Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
        if not Hb > Lb:
            continue
        up = np.flatnonzero(D["ah"][i1:w1] >= Hb); dn = np.flatnonzero(D["bl"][i1:w1] <= Lb)
        ku, kd = (i1 + up[0] if len(up) else None), (i1 + dn[0] if len(dn) else None)
        if (ku is None and kd is None) or (ku is not None and ku == kd):
            continue
        side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
        k = ku if side > 0 else kd
        e = max(Hb, D["ao"][k]) if side > 0 else min(Lb, D["bo"][k])
        R = abs(e - (Lb if side > 0 else Hb))
        if k >= kday or not (R > 0 and R >= 2 * (D["ao"][k] - D["bo"][k])):
            continue
        kc = int(rng.integers(i1, w1)); sc = 1 if rng.random() < 0.5 else -1
        ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
        okc = kc < kday and R >= 2 * (D["ao"][kc] - D["bo"][kc])
        row = dict(mkt=sym, day=pd.Timestamp(d * 86400, unit="s"), side=side, t_entry=int(t[k]), fresh=fresh.get(sday, 0))
        x = exits(D, k, kday, side, e, R)
        row["X4"] = x[3] if x else np.nan
        xc = exits(D, kc, kday, sc, ec, R) if okc else None
        row["C_X4"] = xc[3] if xc else np.nan
        for n, ke in ends.items():
            row[f"S{n}"] = swing(D, k, ke, side, e, R, atr)
            row[f"C_S{n}"] = swing(D, kc, ke, sc, ec, R, atr) if okc else np.nan
        rows.append(row)
    return rows


def collect(end):
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, [(s, end) for s in SYMS]))
    df = pd.DataFrame([r for rr in res for r in rr])
    return df[df.day >= DEV[0]]


def dry():
    df = collect(END)
    print("events", len(df), "| S5/S10 coverage", round(df.S5.notna().mean(), 3), round(df.S10.notna().mean(), 3), "| D20-aligned share", round((df.side == df.fresh).mean(), 3))
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    f, p = pd.DataFrame(market(("NSDQ", END))), pd.DataFrame(market(("NSDQ", cut)))
    f, p = f[f.t_entry < cut - 20 * 86400].reset_index(drop=True), p[p.t_entry < cut - 20 * 86400].reset_index(drop=True)
    print("truncation:", "PASS" if len(f) == len(p) and np.allclose(f[["X4", "S5", "S10"]].to_numpy(), p[["X4", "S5", "S10"]].to_numpy(), equal_nan=True) else "FAIL")
    x = df[(df.mkt == "NSDQ") & (df.day == "2024-06-12")]
    print("hand check NSDQ 2024-06-12:", x[["side", "X4", "S5", "S10", "fresh"]].round(3).to_dict("records"))


def run():
    df = collect(END)
    df.to_parquet("data/si_ledgers/BRK_SWING.parquet")
    for cell, col, ctl, lag, sel in (("S5 hold 5 days", "S5", "C_S5", 5, None), ("S10 hold 10 days", "S10", "C_S10", 5, None), ("D20 aligned, hold to close", "X4", "C_X4", 1, "d20")):
        g = df[df.side == df.fresh] if sel else df
        r = {}
        for lab, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)):
            s = g[(g.day >= a) & (g.day <= b)].dropna(subset=[col])
            r[lab] = (len(s), s[col].mean(), nw_t(s.groupby("day")[col].mean().to_numpy(), lag), s[ctl].mean())
        gt = [r["DEV"][1] >= 0.05 and r["DEV"][2] >= 2.4, r["VAL"][1] > 0 and r["VAL"][2] >= 1.65, r["DEV"][1] - r["DEV"][3] >= 0.05 and r["VAL"][1] - r["VAL"][3] >= 0.05]
        print(f"{cell}: " + " | ".join(f"{k} n{v[0]} {v[1]:+.3f} (t {v[2]:+.2f}) ctl {v[3]:+.3f}" for k, v in r.items()) + f" | gates {''.join('Y' if z else 'n' for z in gt)} PASS {all(gt)}")
        from forex.ea_research.analog import mclass
        print("    by class DEV/VAL/2026: " + " | ".join(f"{c} " + "/".join(f"{x[(x.day >= a) & (x.day <= b)][col].mean():+.3f}" for a, b in (DEV, VAL, Y26)) for c, x in g.assign(c=g.mkt.map(mclass)).groupby("c")))


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
