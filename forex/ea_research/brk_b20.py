"""BRK-B20 exactly as in PREREG_BRK_B20.md: buffered stop orders, tested levels, double levels.  python -m forex.ea_research.brk_b20 [--dry]"""
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


def touches(arr_hi_or_lo, edge, tol, up):
    near = (arr_hi_or_lo >= edge - tol) if up else (arr_hi_or_lo <= edge + tol)
    idx = np.flatnonzero(near)
    n, last = 0, -10**9
    for i in idx:
        if i - last >= 5:
            n += 1
        last = i
    return n


def market(args):
    sym, end = args
    D = load(sym, end); t = D["t"]
    tz, op_s, cl_s = session(sym); lc = local_clock(t, tz)
    dt = daily_table(D)
    rng = np.random.default_rng(zlib.crc32(sym.encode()) + 20)
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
        cap = np.searchsorted(t, (t[i1] // 86400) * 86400 + 22 * H + 55 * M)
        kend = min(xe, cap, len(t) - 1)
        Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
        box = Hb - Lb
        if not box > 0:
            continue
        sday = t[i0] // 86400
        pH = dt.h.shift(1).get(sday, np.nan); pL = dt.l.shift(1).get(sday, np.nan)
        day = pd.Timestamp(d * 86400, unit="s")
        for cell, b in (("U0_plain", 0.0), ("U1_buf0.10", 0.10), ("U2_buf0.25", 0.25), ("U3_buf0.50", 0.50)):
            hi_l, lo_l = Hb + b * box, Lb - b * box
            up = np.flatnonzero(D["ah"][i1:w1] >= hi_l); dn = np.flatnonzero(D["bl"][i1:w1] <= lo_l)
            ku, kd = (i1 + up[0] if len(up) else None), (i1 + dn[0] if len(dn) else None)
            if (ku is None and kd is None) or (ku is not None and ku == kd):
                continue
            side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
            k = ku if side > 0 else kd
            e = max(hi_l, D["ao"][k]) if side > 0 else min(lo_l, D["bo"][k])
            R = abs(e - (Lb if side > 0 else Hb))
            if k >= kend or not (R > 0 and R >= 2 * (D["ao"][k] - D["bo"][k])):
                continue
            x = exits(D, k, kend, side, e, R)
            if not x:
                continue
            kc = int(rng.integers(i1, w1)); sc = 1 if rng.random() < 0.5 else -1
            ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
            xc = exits(D, kc, kend, sc, ec, R) if kc < kend and R >= 2 * (D["ao"][kc] - D["bo"][kc]) else None
            row = dict(mkt=sym, day=day, cell=cell, side=side, t_entry=int(t[k]), R=x[3], C=xc[3] if xc else np.nan)
            if cell == "U0_plain":
                tol = 0.10 * box
                n_t = touches(D["bh"][i0:i1], Hb, tol, True) if side > 0 else touches(D["bl"][i0:i1], Lb, tol, False)
                dbl = (abs(Hb - pH) <= tol) if side > 0 else (abs(Lb - pL) <= tol)
                rows.append({**row, "cell": "U4_tested3"} ) if n_t >= 3 else None
                rows.append({**row, "cell": "U5_double_level"}) if (np.isfinite(pH) and dbl) else None
            rows.append(row)
    return rows


def main(dry):
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, [(s, END) for s in SYMS]))
    df = pd.DataFrame([r for rr in res for r in rr]); df = df[df.day >= DEV[0]]
    if dry:
        print(df.groupby("cell").size().to_dict())
        cut = pd.Timestamp("2024-03-13 12:00").timestamp()
        f, p = pd.DataFrame(market(("NSDQ", END))), pd.DataFrame(market(("NSDQ", cut)))
        f, p = f[f.t_entry < cut - 86400].reset_index(drop=True), p[p.t_entry < cut - 86400].reset_index(drop=True)
        print("truncation:", "PASS" if len(f) == len(p) and np.allclose(f.R, p.R) else "FAIL")
        return
    df.to_parquet("D:/finance/si_ledgers/BRK_B20.parquet")
    for cell, g in df.groupby("cell"):
        r = {}
        for lab, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)):
            s = g[(g.day >= a) & (g.day <= b)]
            r[lab] = (len(s), s.R.mean(), nw_t(s.groupby("day").R.mean().to_numpy()), s.C.mean())
        gt = [r["DEV"][1] >= 0.05 and r["DEV"][2] >= 2.58, r["VAL"][1] > 0 and r["VAL"][2] >= 1.65, r["DEV"][1] - r["DEV"][3] >= 0.05 and r["VAL"][1] - r["VAL"][3] >= 0.05]
        tag = "" if cell == "U0_plain" else f" | gates {''.join('Y' if z else 'n' for z in gt)} PASS {all(gt)}"
        print(f"{cell}: " + " | ".join(f"{k} n{v[0]} {v[1]:+.3f} (t {v[2]:+.2f}) ctl {v[3]:+.3f}" for k, v in r.items()) + tag)


if __name__ == "__main__":
    main("--dry" in sys.argv)
