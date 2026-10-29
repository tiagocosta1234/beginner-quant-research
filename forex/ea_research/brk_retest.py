"""BRK-RETEST exactly as in PREREG_BRK_RETEST.md: retest-limit, retest-confirmed and failed-breakout entries on the session box of 46 markets.
   python -m forex.ea_research.brk_retest --dry | (no flag) run"""
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
from forex.ea_research.ict2 import SYMS, fix_minute, nw_t

END = pd.Timestamp("2026-10-03").timestamp()
H, M = 3600, 60
DEV, VAL, Y26 = ("2022-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-10-02")
CELLS = ("R1", "R2", "R3")


def m5_close_after(lc, mc, a, b, cond):
    """index of the last M1 bar of the first completed M5 bucket (session clock) in [a, b) whose close satisfies cond."""
    if b <= a:
        return None
    key = lc[a:b] // 300
    last = np.flatnonzero(np.r_[key[1:] != key[:-1], True]) + a
    ok = np.flatnonzero(cond(mc[last]))
    return int(last[ok[0]]) if len(ok) else None


def market(args):
    sym, end = args
    D = load(sym, end)
    tz, op_s, cl_s = session(sym)
    lc = local_clock(D["t"], tz)
    t = D["t"]
    mc = (D["bc"] + D["ac"]) / 2                                       # mid closes, computed once (speed only)
    rng = np.random.default_rng(zlib.crc32(sym.encode()) + 7)
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
        mid = (Hb + Lb) / 2
        if not Hb > Lb:
            continue
        up = np.flatnonzero(D["ah"][i1:w1] >= Hb)
        dn = np.flatnonzero(D["bl"][i1:w1] <= Lb)
        ku, kd = (i1 + up[0] if len(up) else None), (i1 + dn[0] if len(dn) else None)
        if (ku is None and kd is None) or (ku is not None and ku == kd):
            continue
        side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
        kb = ku if side > 0 else kd
        day = pd.Timestamp(d * 86400, unit="s")
        trades = []
        # R1 retest limit at the broken level, 60 minutes, stop at the box middle
        a, b = kb + 1, min(kb + 61, kend)
        if b > a:
            hit = np.flatnonzero(D["al"][a:b] <= Hb) if side > 0 else np.flatnonzero(D["bh"][a:b] >= Lb)
            if len(hit):
                k = a + hit[0]
                e = min(Hb, D["ao"][k]) if side > 0 else max(Lb, D["bo"][k])
                trades.append(("R1", k, side, e, abs(e - mid)))
        # R2 retest (bid back to the level) then an M5 close back beyond it
        if b > a:
            rt = np.flatnonzero(D["bl"][a:b] <= Hb) if side > 0 else np.flatnonzero(D["ah"][a:b] >= Lb)
            if len(rt):
                j = a + rt[0]
                c = m5_close_after(lc, mc, j, min(j + 60, kend), (lambda v: v > Hb) if side > 0 else (lambda v: v < Lb))
                if c is not None and c + 1 < kend:
                    k = fix_minute(D, c + 1)
                    e = D["ao"][k] if side > 0 else D["bo"][k]
                    sp = D["ao"][k] - D["bo"][k]
                    stop = (D["bl"][kb:k].min() - sp) if side > 0 else (D["ah"][kb:k].max() + sp)
                    trades.append(("R2", k, side, e, abs(e - stop)))
        # R3 failed breakout: an M5 close back beyond the box middle within 90 minutes -> the other way
        c = m5_close_after(lc, mc, kb, min(kb + 90, kend), (lambda v: v < mid) if side > 0 else (lambda v: v > mid))
        if c is not None and c + 1 < kend:
            k = fix_minute(D, c + 1)
            e = D["bo"][k] if side > 0 else D["ao"][k]
            sp = D["ao"][k] - D["bo"][k]
            stop = (D["ah"][kb:k].max() + sp) if side > 0 else (D["bl"][kb:k].min() - sp)
            trades.append(("R3", k, -side, e, abs(e - stop)))
        for cell, k, sd, e, R in trades:
            if k >= kend or not (R > 0 and R >= 2 * (D["ao"][k] - D["bo"][k])):
                continue
            x = exits(D, k, kend, sd, e, R)
            if x is None:
                continue
            kc = int(rng.integers(i1, w1))
            sc = 1 if rng.random() < 0.5 else -1
            ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
            xc = exits(D, kc, kend, sc, ec, R) if kc < kend and R >= 2 * (D["ao"][kc] - D["bo"][kc]) else None
            rows.append((sym, day, cell, sd, int(t[k]), x[3], x[1], xc[3] if xc else np.nan, xc[1] if xc else np.nan))
    return rows


COLS = ["mkt", "day", "cell", "side", "t_entry", "E_close", "E_2R", "C_close", "C_2R"]


def collect(end):
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, [(s, end) for s in SYMS]))
    df = pd.DataFrame([r for rr in res for r in rr], columns=COLS)
    return df[df.day >= DEV[0]]


def dry():
    t0 = time.time()
    df = collect(END)
    print(f"{time.time() - t0:.0f}s | trades per cell and period:")
    print(df.assign(per=np.where(df.day <= DEV[1], "DEV", np.where(df.day <= VAL[1], "VAL", "2026"))).groupby(["cell", "per"]).size().unstack())
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    bad = 0
    for s in ("EURUSD", "XAUUSD", "NSDQ", "BTCUSD"):
        f = pd.DataFrame(market((s, END)), columns=COLS); p = pd.DataFrame(market((s, cut)), columns=COLS)
        f, p = f[f.t_entry < cut - 86400].reset_index(drop=True), p[p.t_entry < cut - 86400].reset_index(drop=True)
        bad += int(not (len(f) == len(p) and np.allclose(f[["E_close", "E_2R"]].to_numpy(), p[["E_close", "E_2R"]].to_numpy())))
    print("truncation test:", "PASS" if bad == 0 else f"FAIL {bad}")
    x = df[(df.mkt == "NSDQ") & (df.day == "2024-06-12")]
    print("hand check NSDQ 2024-06-12:", x[["cell", "side", "t_entry", "E_close", "E_2R"]].assign(t_entry=pd.to_datetime(x.t_entry, unit="s")).round(2).to_dict("records"))


def run():
    df = collect(END)
    df.to_parquet("data/si_ledgers/BRK_RETEST.parquet")
    rows = []
    for cell in CELLS:
        g = df[df.cell == cell]
        for ex, ctl in (("E_close", "C_close"), ("E_2R", "C_2R")):
            r = dict(cell=f"{cell}-{ex}")
            for lab, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)):
                s = g[(g.day >= a) & (g.day <= b)]
                r[f"n {lab}"], r[f"R {lab}"], r[f"t {lab}"], r[f"ctl {lab}"] = len(s), s[ex].mean(), nw_t(s.groupby("day")[ex].mean().to_numpy()), s[ctl].mean()
            gate = [r["R DEV"] >= 0.05 and r["t DEV"] >= 2.4, r["R VAL"] > 0 and r["t VAL"] >= 1.65, r["R DEV"] - r["ctl DEV"] >= 0.05 and r["R VAL"] - r["ctl VAL"] >= 0.05]
            r["gates"], r["PASS"] = "".join("Y" if v else "n" for v in gate), all(gate)
            ix = g[g.mkt.isin(["SP", "NSDQ", "DOW", "DAX", "NIKKEI", "ASX"])]
            r["indices DEV/VAL/2026"] = " / ".join(f"{ix[(ix.day >= a) & (ix.day <= b)][ex].mean():+.3f}" for a, b in (DEV, VAL, Y26))
            rows.append(r)
    R = pd.DataFrame(rows)
    pd.set_option("display.width", 260)
    print(R.round(3).to_string(index=False))
    R.to_csv("data/si_ledgers/BRK_RETEST_cells.csv", index=False)
    print("\nby class, E_close (DEV / VAL):")
    for cell in CELLS:
        g = df[df.cell == cell].assign(c=lambda z: z.mkt.map(mclass))
        print(f"  {cell}: " + " | ".join(f"{c} {x[x.day <= DEV[1]].E_close.mean():+.3f}/{x[(x.day >= VAL[0]) & (x.day <= VAL[1])].E_close.mean():+.3f}" for c, x in g.groupby("c")))


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
