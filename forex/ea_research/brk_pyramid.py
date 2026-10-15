"""BRK-PYRAMID exactly as in PREREG_BRK_PYRAMID.md: adding at +1R / +2R to the session breakouts of 46 markets.
   python -m forex.ea_research.brk_pyramid --dry | (no flag) run"""
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.breakouts import local_clock, session
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS, nw_t

END = pd.Timestamp("2026-10-03").timestamp()
H, M = 3600, 60
DEV, VAL, Y26 = ("2022-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-10-02")
BIG = 10**9


def first(mask):
    i = np.flatnonzero(mask)
    return i[0] if len(i) else BIG


def pyr(D, k, kend, side, E, R):
    """(P0, P1, P2, adds) in units of R; prices mapped to a signed space so shorts follow the long logic."""
    n = kend - k
    if n < 2:
        return None
    if side > 0:
        lo, hi, o_stop, o_add, c_stop, x_end = D["bl"][k:kend], D["ah"][k:kend], D["bo"][k:kend], D["ao"][k:kend], D["bc"][k:kend], D["bo"][kend]
    else:
        lo, hi, o_stop, o_add, c_stop, x_end = -D["ah"][k:kend], -D["bl"][k:kend], -D["ao"][k:kend], -D["bo"][k:kend], -D["ac"][k:kend], -D["ao"][kend]
        E = -E
    s0 = E - R
    if c_stop[0] <= s0:
        return -1.0, -1.0, -1.0, 0
    i_s0 = first(lo[1:] <= s0) + 1
    p0 = (min(s0, o_stop[i_s0]) - E) / R if i_s0 < n else (x_end - E) / R
    i_a1 = first(hi[1:] >= E + R) + 1
    if i_a1 >= n or i_s0 <= i_a1:
        return p0, p0, p0, 0
    E2 = max(E + R, o_add[i_a1])

    def run_from(i, stop):
        if c_stop[i] <= stop:
            return stop, i
        j = first(lo[i + 1:] <= stop)
        if j == BIG:
            return x_end, BIG
        jj = i + 1 + j
        return min(stop, o_stop[jj]), jj

    px1, i_s1 = run_from(i_a1, E)
    p1 = ((px1 - E) + (px1 - E2)) / R
    i_a2 = first(hi[i_a1 + 1:] >= E + 2 * R)
    i_a2 = i_a2 + i_a1 + 1 if i_a2 != BIG else BIG
    if i_a2 >= n or i_s1 <= i_a2:
        return p0, p1, p1, 1
    E3 = max(E + 2 * R, o_add[i_a2])
    px2, _ = run_from(i_a2, E + R)
    p2 = ((px2 - E) + (px2 - E2) + (px2 - E3)) / R
    return p0, p1, p2, 2


def market(args):
    sym, end = args
    D = load(sym, end)
    tz, op_s, cl_s = session(sym)
    t = D["t"]
    lc = local_clock(t, tz)
    rng = np.random.default_rng(zlib.crc32(sym.encode()) + 29)
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
        kend = min(xe, np.searchsorted(t, (t[i1] // 86400) * 86400 + 22 * H + 55 * M), len(t) - 1)
        Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
        if not Hb > Lb:
            continue
        up = np.flatnonzero(D["ah"][i1:w1] >= Hb)
        dn = np.flatnonzero(D["bl"][i1:w1] <= Lb)
        ku = i1 + up[0] if len(up) else None
        kd = i1 + dn[0] if len(dn) else None
        day = int(t[i1] // 86400) * 86400
        if not (ku is None and kd is None) and not (ku is not None and ku == kd):
            side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
            k = ku if side > 0 else kd
            e = max(Hb, D["ao"][k]) if side > 0 else min(Lb, D["bo"][k])
            R = abs(e - (Lb if side > 0 else Hb))
            if k < kend and R >= 2 * (D["ao"][k] - D["bo"][k]):
                x = pyr(D, k, kend, side, e, R)
                if x:
                    rows.append((sym, day, "BRK", side, int(t[k]), *x))
        kc = int(rng.integers(i1, w1))
        sc = 1 if rng.random() < 0.5 else -1
        ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
        if kc < kend and (Hb - Lb) >= 2 * (D["ao"][kc] - D["bo"][kc]):
            x = pyr(D, kc, kend, sc, ec, Hb - Lb)
            if x:
                rows.append((sym, day, "CTRL", sc, int(t[kc]), *x))
    return rows


def collect(end):
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, [(s, end) for s in SYMS]))
    df = pd.DataFrame([r for rr in res for r in rr], columns=["mkt", "d", "kind", "side", "t_entry", "P0", "P1", "P2", "adds"])
    df["day"] = pd.to_datetime(df.d, unit="s")
    df["c"] = df.mkt.map(mclass)
    return df[df.day >= DEV[0]]


def dry():
    df = collect(END)
    b = df[df.kind == "BRK"]
    print("breakouts", len(b), "| adds 0/1/2 share", b.adds.value_counts(normalize=True).round(3).sort_index().to_dict(), "| P0 all years mean", round(b.P0.mean(), 3))
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    f, p = pd.DataFrame(market(("NSDQ", END))), pd.DataFrame(market(("NSDQ", cut)))
    f, p = f[f[4] < cut - 86400].reset_index(drop=True), p[p[4] < cut - 86400].reset_index(drop=True)
    ok = len(f) == len(p) and np.allclose(f[[5, 6, 7]].to_numpy(), p[[5, 6, 7]].to_numpy())
    print("truncation:", "PASS" if ok else f"FAIL {len(f)} {len(p)}")
    x = b[(b.mkt == "NSDQ") & (b.day >= "2024-06-10") & (b.day <= "2024-06-14")]
    print("hand check NSDQ:", x[["day", "side", "P0", "P1", "P2", "adds"]].round(3).to_dict("records"))


def run():
    df = collect(END)
    df.to_parquet("D:/finance/si_ledgers/BRK_PYRAMID.parquet")
    b, c = df[df.kind == "BRK"], df[df.kind == "CTRL"]
    for col in ("P0", "P1", "P2"):
        r = {}
        for lab, (a, z) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)):
            s, sc = b[(b.day >= a) & (b.day <= z)], c[(c.day >= a) & (c.day <= z)]
            r[lab] = (len(s), s[col].mean(), nw_t(s.groupby("day")[col].mean().to_numpy()), s.P0.mean(), sc[col].mean(), s[col].quantile(0.95))
        gt = [r["DEV"][1] >= 0.05 and r["DEV"][2] >= 2.24, r["VAL"][1] > 0 and r["VAL"][2] >= 1.65, r["DEV"][1] - r["DEV"][3] >= 0.05 and r["VAL"][1] - r["VAL"][3] >= 0.05]
        print(f"{col}: " + " | ".join(f"{k} n{v[0]} {v[1]:+.3f} (t {v[2]:+.2f}) P0 {v[3]:+.3f} random {v[4]:+.3f} p95 {v[5]:+.2f}" for k, v in r.items()) + ("" if col == "P0" else f" | gates {''.join('Y' if z else 'n' for z in gt)} PASS {all(gt)}"))
        print("    by class DEV/VAL/2026: " + " | ".join(f"{cl} " + "/".join(f"{x[(x.day >= a) & (x.day <= z)][col].mean():+.3f}" for a, z in (DEV, VAL, Y26)) for cl, x in b.groupby("c")))
    for m in ("NSDQ", "XAUUSD", "USDJPY"):
        x = b[b.mkt == m]
        print(f"{m}: " + " | ".join(f"{col} " + "/".join(f"{x[(x.day >= a) & (x.day <= z)][col].mean():+.3f}" for a, z in (DEV, VAL, Y26)) for col in ("P0", "P1", "P2")))


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
