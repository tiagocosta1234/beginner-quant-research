"""BRK-FLAG exactly as in PREREG_BRK_FLAG.md: M5 bull/bear flag breakouts on 46 markets.  python -m forex.ea_research.brk_flag [--dry]"""
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from forex.ea_research.analog import mclass
from forex.ea_research.breakouts import local_clock, session
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS, nw_t, sim

END = pd.Timestamp("2026-10-03").timestamp()
H, M = 3600, 60
DEV, VAL, Y26 = ("2022-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-10-02")


def market(args):
    sym, end = args
    D = load(sym, end); t = D["t"]
    tz, op_s, cl_s = session(sym); lc = local_clock(t, tz)
    key = lc // 300
    st = np.flatnonzero(np.r_[True, key[1:] != key[:-1]]); en = np.r_[st[1:], len(t)]
    mh = np.maximum.reduceat((D["bh"] + D["ah"]) / 2, st); ml = np.minimum.reduceat((D["bl"] + D["al"]) / 2, st)
    mc = ((D["bc"] + D["ac"]) / 2)[en - 1]
    bt = key[st] * 300; sod = bt % 86400
    pc = np.r_[mc[0], mc[:-1]]
    atr = pd.Series(np.maximum(mh - ml, np.maximum(np.abs(mh - pc), np.abs(ml - pc)))).rolling(14).mean().to_numpy()
    rng = np.random.default_rng(zlib.crc32(sym.encode()) + 22)
    rows = []
    nb = len(st); j = 6
    busy_until = -1
    while j + 6 < nb:
        if not (op_s <= sod[j] < cl_s - 2 * H) or j <= busy_until or not np.isfinite(atr[j - 1]):
            j += 1; continue
        lo6, hi6 = ml[j - 6:j].min(), mh[j - 6:j].max()
        imp = hi6 - lo6
        if imp < 1.5 * atr[j - 1] or bt[j - 1] - bt[j - 6] > 6 * 300:
            j += 1; continue
        c6 = mc[j - 1]
        side = 1 if c6 >= hi6 - 0.25 * imp else (-1 if c6 <= lo6 + 0.25 * imp else 0)
        if side == 0:
            j += 1; continue
        # flag: bars j .. j+k (6..18 bars) inside <= 40% of the impulse, no retrace > 50%
        fhi, flo, entered = -np.inf, np.inf, False
        for kk in range(j, min(j + 18, nb)):
            fhi, flo = max(fhi, mh[kk]), min(flo, ml[kk])
            if fhi - flo > 0.4 * imp or (side > 0 and flo < hi6 - 0.5 * imp) or (side < 0 and fhi > lo6 + 0.5 * imp):
                break
            if kk - j + 1 >= 6 and kk + 1 < nb and bt[kk + 1] - bt[kk] <= 300 and sod[kk + 1] < cl_s - 2 * H:
                a, b = st[kk + 1], en[kk + 1]
                lvl = fhi if side > 0 else flo
                hit = np.flatnonzero(D["ah"][a:b] >= lvl) if side > 0 else np.flatnonzero(D["bl"][a:b] <= lvl)
                if len(hit):
                    k = a + hit[0]
                    e = max(lvl, D["ao"][k]) if side > 0 else min(lvl, D["bo"][k])
                    stop = flo if side > 0 else fhi
                    R = abs(e - stop)
                    d0 = lc[k] // 86400
                    kend = min(np.searchsorted(lc, d0 * 86400 + cl_s), np.searchsorted(t, (t[k] // 86400) * 86400 + 22 * H + 55 * M), len(t) - 1)
                    if R > 0 and R >= 2 * (D["ao"][k] - D["bo"][k]) and kend > k:
                        r1 = sim(D, k, side, e, stop, e + side * imp, kend)
                        r2 = sim(D, k, side, e, stop, e + side * 1e9, kend)
                        kc = int(rng.integers(np.searchsorted(lc, d0 * 86400 + op_s), max(kend - 1, np.searchsorted(lc, d0 * 86400 + op_s) + 1)))
                        sc = 1 if rng.random() < 0.5 else -1
                        ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
                        c1 = sim(D, kc, sc, ec, ec - sc * R, ec + sc * imp, kend) if kc < kend else None
                        c2 = sim(D, kc, sc, ec, ec - sc * R, ec + sc * 1e9, kend) if kc < kend else None
                        if r1 and r2:
                            rows.append(dict(mkt=sym, day=pd.Timestamp(int(t[k] // 86400) * 86400, unit="s"), side=side, t_entry=int(t[k]),
                                             F1=r1[0], F2=r2[0], C1=c1[0] if c1 else np.nan, C2=c2[0] if c2 else np.nan, tgtR=imp / R))
                            busy_until = int(np.searchsorted(st, kend))
                    entered = True
                    break
        j = max(j + 1, busy_until + 1) if entered else j + 1
    return rows


def main(dry):
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, [(s, END) for s in SYMS]))
    df = pd.DataFrame([r for rr in res for r in rr]); df = df[df.day >= DEV[0]]
    if dry:
        print("flags:", len(df), "| per period:", {k: int(((df.day >= a) & (df.day <= b)).sum()) for k, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26))}, "| median target in R", round(df.tgtR.median(), 2))
        cut = pd.Timestamp("2024-03-13 12:00").timestamp()
        f, p = pd.DataFrame(market(("NSDQ", END))), pd.DataFrame(market(("NSDQ", cut)))
        f, p = f[f.t_entry < cut - 86400].reset_index(drop=True), p[p.t_entry < cut - 86400].reset_index(drop=True)
        print("truncation:", "PASS" if len(f) == len(p) and np.allclose(f.F2, p.F2) else f"FAIL {len(f)} vs {len(p)}")
        return
    df.to_parquet("D:/finance/si_ledgers/BRK_FLAG.parquet")
    for col, ctl in (("F1", "C1"), ("F2", "C2")):
        r = {}
        for lab, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)):
            s = df[(df.day >= a) & (df.day <= b)]
            r[lab] = (len(s), s[col].mean(), nw_t(s.groupby("day")[col].mean().to_numpy()), s[ctl].mean())
        gt = [r["DEV"][1] >= 0.05 and r["DEV"][2] >= 2.24, r["VAL"][1] > 0 and r["VAL"][2] >= 1.65, r["DEV"][1] - r["DEV"][3] >= 0.05 and r["VAL"][1] - r["VAL"][3] >= 0.05]
        print(f"{col} {'flagpole target' if col == 'F1' else 'hold to close'}: " + " | ".join(f"{k} n{v[0]} {v[1]:+.3f} (t {v[2]:+.2f}) ctl {v[3]:+.3f}" for k, v in r.items()) + f" | gates {''.join('Y' if z else 'n' for z in gt)} PASS {all(gt)}")
        print("    by class DEV/VAL/2026: " + " | ".join(f"{c} " + "/".join(f"{x[(x.day >= a) & (x.day <= b)][col].mean():+.3f}" for a, b in (DEV, VAL, Y26)) for c, x in df.assign(c=df.mkt.map(mclass)).groupby("c")))


if __name__ == "__main__":
    main("--dry" in sys.argv)
