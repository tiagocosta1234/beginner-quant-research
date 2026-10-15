"""BRK-DONCH exactly as in PREREG_BRK_DONCH.md: intraday Donchian breakouts (M15/H1, N 20/55) on 46 markets.  python -m forex.ea_research.brk_donch [--dry]"""
import sys
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
CELLS = (("M15_N20", 15, 20), ("M15_N55", 15, 55), ("H1_N20", 60, 20), ("H1_N55", 60, 55))


def bars(D, lc, minutes):
    key = lc // (minutes * 60)
    st = np.flatnonzero(np.r_[True, key[1:] != key[:-1]]); en = np.r_[st[1:], len(lc)]
    mh = np.maximum.reduceat((D["bh"] + D["ah"]) / 2, st); ml = np.minimum.reduceat((D["bl"] + D["al"]) / 2, st)
    mc = ((D["bc"] + D["ac"]) / 2)[en - 1]
    return st, en, mh, ml, mc, key[st] * minutes * 60


def run_cell(D, lc, minutes, N, tz, op_s, cl_s, sym, cell):
    st, en, mh, ml, mc, bt = bars(D, lc, minutes)
    prev_c = np.r_[mc[0], mc[:-1]]
    tr = np.maximum(mh - ml, np.maximum(np.abs(mh - prev_c), np.abs(ml - prev_c)))
    atr = pd.Series(tr).rolling(14).mean().to_numpy()
    hiN = pd.Series(mh).rolling(N).max().shift(1).to_numpy(); loN = pd.Series(ml).rolling(N).min().shift(1).to_numpy()
    hiX = pd.Series(mh).rolling(N // 2).max().shift(1).to_numpy(); loX = pd.Series(ml).rolling(N // 2).min().shift(1).to_numpy()
    t = D["t"]; rows = []
    day = bt // 86400; sod = bt % 86400
    in_sess = (sod >= op_s) & (sod < cl_s - 2 * H)
    j = 0; nb = len(st)
    while j < nb:
        if not in_sess[j] or not np.isfinite(hiN[j]) or not np.isfinite(atr[j]) or atr[j] <= 0:
            j += 1; continue
        side = 1 if mh[j] > hiN[j] else (-1 if ml[j] < loN[j] else 0)
        if side == 0:
            j += 1; continue
        lvl = hiN[j] if side > 0 else loN[j]
        a, b = st[j], en[j]
        hit = np.flatnonzero(D["ah"][a:b] >= lvl) if side > 0 else np.flatnonzero(D["bl"][a:b] <= lvl)
        if not len(hit):
            j += 1; continue
        k = a + hit[0]
        e = max(lvl, D["ao"][k]) if side > 0 else min(lvl, D["bo"][k])
        R = 2 * atr[j]
        if R < 2 * (D["ao"][k] - D["bo"][k]):
            j += 1; continue
        stop = e - side * R
        d0 = day[j]
        close_t = d0 * 86400 + cl_s
        kclose = min(np.searchsorted(lc, close_t), np.searchsorted(t, (t[k] // 86400) * 86400 + 22 * H + 55 * M), len(t) - 1)
        x, jx = None, j
        # minute stop check inside the entry bar remainder and later bars; turtle exit on bar closes
        jj = j
        while True:
            seg_a = k if jj == j else st[jj]
            seg_b = min(en[jj], kclose)
            if seg_b > seg_a:
                sl = np.flatnonzero(D["bl"][seg_a:seg_b] <= stop) if side > 0 else np.flatnonzero(D["ah"][seg_a:seg_b] >= stop)
                if len(sl):
                    m = seg_a + sl[0]
                    x = min(stop, D["bo"][m]) if side > 0 else max(stop, D["ao"][m]); jx = jj; break
            if en[jj] >= kclose or jj + 1 >= nb:
                x = D["bo"][kclose] if side > 0 else D["ao"][kclose]; jx = jj; break
            if jj > j and ((side > 0 and mc[jj] < loX[jj]) or (side < 0 and mc[jj] > hiX[jj])):
                m = min(en[jj], kclose)
                x = D["bo"][m] if side > 0 else D["ao"][m]; jx = jj; break
            jj += 1
        rows.append(dict(mkt=sym, cell=cell, day=pd.Timestamp(int(t[k] // 86400) * 86400, unit="s"), side=side, t_entry=int(t[k]), R=side * (x - e) / R))
        j = jx + 1
    return rows


def market(args):
    sym, end = args
    D = load(sym, end)
    tz, op_s, cl_s = session(sym)
    lc = local_clock(D["t"], tz)
    out = []
    for cell, mins, N in CELLS:
        out += run_cell(D, lc, mins, N, tz, op_s, cl_s, sym, cell)
    return out


def main(dry):
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, [(s, END) for s in SYMS]))
    df = pd.DataFrame([r for rr in res for r in rr]); df = df[df.day >= DEV[0]]
    if dry:
        print(df.groupby("cell").size().to_dict())
        cut = pd.Timestamp("2024-03-13 12:00").timestamp()
        f, p = pd.DataFrame(market(("NSDQ", END))), pd.DataFrame(market(("NSDQ", cut)))
        f, p = f[f.t_entry < cut - 86400].reset_index(drop=True), p[p.t_entry < cut - 86400].reset_index(drop=True)
        print("truncation:", "PASS" if len(f) == len(p) and np.allclose(f.R, p.R) else f"FAIL {len(f)} vs {len(p)}")
        return
    df.to_parquet("D:/finance/si_ledgers/BRK_DONCH.parquet")
    for cell, g in df.groupby("cell"):
        r = {}
        for lab, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)):
            s = g[(g.day >= a) & (g.day <= b)]
            r[lab] = (len(s), s.R.mean(), nw_t(s.groupby("day").R.mean().to_numpy()))
        gt = [r["DEV"][1] >= 0.05 and r["DEV"][2] >= 2.5, r["VAL"][1] > 0 and r["VAL"][2] >= 1.65]
        print(f"{cell}: " + " | ".join(f"{k} n{v[0]} {v[1]:+.3f} (t {v[2]:+.2f})" for k, v in r.items()) + f" | gates {''.join('Y' if z else 'n' for z in gt)} PASS {all(gt)}")
        print("    by class DEV/VAL/2026: " + " | ".join(f"{c} " + "/".join(f"{x[(x.day >= a) & (x.day <= b)].R.mean():+.3f}" for a, b in (DEV, VAL, Y26)) for c, x in g.assign(c=g.mkt.map(mclass)).groupby("c")))


if __name__ == "__main__":
    main("--dry" in sys.argv)
