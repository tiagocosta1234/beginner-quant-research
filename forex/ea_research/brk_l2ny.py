"""BRK-L2NY exactly as in PREREG_BRK_L2NY.md: London-morning range (08:00-12:00) broken in the New York session, 46 markets.
   python -m forex.ea_research.brk_l2ny --dry | (no flag) run"""
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.breakouts import local_clock
from forex.ea_research.brk_hours import hold, hold_fill
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS, nw_t

END = pd.Timestamp("2026-10-03").timestamp()
H, M = 3600, 60
DEV, VAL, Y26 = ("2022-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-10-02")


def market(args):
    sym, end = args
    D = load(sym, end)
    t = D["t"]
    lc = local_clock(t, "Europe/London")
    rng = np.random.default_rng(zlib.crc32(sym.encode()) + 36)
    rows = []
    for d in np.unique(lc // 86400):
        base = d * 86400
        i0, i1 = np.searchsorted(lc, base + 8 * H), np.searchsorted(lc, base + 12 * H)
        w1 = np.searchsorted(lc, base + 16 * H)
        xe = np.searchsorted(lc, base + 20 * H)
        if xe >= len(t) or i1 - i0 < 150 or lc[i0] // 86400 != d or w1 <= i1 + 60:
            continue
        kend = min(xe, np.searchsorted(t, (t[i1] // 86400) * 86400 + 22 * H + 55 * M), len(t) - 1)
        Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
        if not Hb > Lb:
            continue
        up = np.flatnonzero(D["ah"][i1:w1] >= Hb)
        dn = np.flatnonzero(D["bl"][i1:w1] <= Lb)
        ku = i1 + up[0] if len(up) else None
        kd = i1 + dn[0] if len(dn) else None
        if (ku is None and kd is None) or (ku is not None and ku == kd):
            continue
        side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
        k = ku if side > 0 else kd
        if k >= kend or (t[k] % 86400) // H in (23, 0):
            continue
        e = max(Hb, D["ao"][k]) if side > 0 else min(Lb, D["bo"][k])
        sp = D["ao"][k] - D["bo"][k]
        kc = int(rng.integers(i1, w1))
        sc = 1 if rng.random() < 0.5 else -1
        ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
        row = dict(mkt=sym, day=pd.Timestamp(base, unit="s"), side=side, t_entry=int(t[k]))
        for cell, R in (("N1", abs(e - (Lb if side > 0 else Hb))), ("N2", abs(e - (Hb + Lb) / 2))):
            ok = R > 0 and R >= 2 * sp
            row[cell] = hold_fill(D, k, kend, side, e, R) if ok else np.nan
            row["C_" + cell] = hold(D, kc, kend, sc, ec, R) if ok and kc < kend else np.nan
        rows.append(row)
    return rows


def collect(end):
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, [(s, end) for s in SYMS]))
    df = pd.DataFrame([r for rr in res for r in rr])
    df["c"] = df.mkt.map(mclass)
    return df[df.day >= DEV[0]]


def dry():
    df = collect(END)
    print("events", len(df), "| N1/N2 valid", int(df.N1.notna().sum()), int(df.N2.notna().sum()))
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    f, p = pd.DataFrame(market(("NSDQ", END))), pd.DataFrame(market(("NSDQ", cut)))
    f, p = f[f.t_entry < cut - 86400].reset_index(drop=True), p[p.t_entry < cut - 86400].reset_index(drop=True)
    ok = len(f) == len(p) and np.allclose(f[["N1", "N2"]].to_numpy(float), p[["N1", "N2"]].to_numpy(float), equal_nan=True)
    print("truncation:", "PASS" if ok else f"FAIL {len(f)} {len(p)}")


def run():
    df = collect(END)
    df.to_parquet("data/si_ledgers/BRK_L2NY.parquet")
    for cell in ("N1", "N2"):
        r = {}
        for lab, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)):
            s = df[(df.day >= a) & (df.day <= b)].dropna(subset=[cell])
            r[lab] = (len(s), s[cell].mean(), nw_t(s.groupby("day")[cell].mean().to_numpy()), s["C_" + cell].mean())
        gt = [r["DEV"][1] >= 0.05 and r["DEV"][2] >= 2.24, r["VAL"][1] > 0 and r["VAL"][2] >= 1.65, r["DEV"][1] - r["DEV"][3] >= 0.05 and r["VAL"][1] - r["VAL"][3] >= 0.05]
        print(f"{cell} {'stop other side' if cell == 'N1' else 'stop at the middle'}: " + " | ".join(f"{k} n{v[0]} {v[1]:+.3f} (t {v[2]:+.2f}) ctl {v[3]:+.3f}" for k, v in r.items()) + f" | gates {''.join('Y' if z else 'n' for z in gt)} PASS {all(gt)}")
        print("    by class DEV/VAL/2026: " + " | ".join(f"{c} " + "/".join(f"{x[(x.day >= a) & (x.day <= b)][cell].mean():+.3f}" for a, b in (DEV, VAL, Y26)) for c, x in df.groupby("c")))


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
