"""BRK-B12 exactly as in PREREG_BRK_B12.md: overnight-range, initial-balance, intermarket-confirmed and DAX-led breakouts.
   python -m forex.ea_research.brk_b12 --dry | (no flag) run"""
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.breakouts import local_clock, session
from forex.ea_research.brk_exits import exits
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS, nw_t

END = pd.Timestamp("2026-10-03").timestamp()
H, M = 3600, 60
DEV, VAL, Y26 = ("2022-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-10-02")
US = ("SP", "NSDQ", "DOW")


def ctrl(D, rng, a, b, kend, R):
    if b <= a:
        return np.nan
    kc = int(rng.integers(a, b)); sc = 1 if rng.random() < 0.5 else -1
    ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
    if kc >= kend or not (R > 0 and R >= 2 * (D["ao"][kc] - D["bo"][kc])):
        return np.nan
    x = exits(D, kc, kend, sc, ec, R)
    return x[3] if x else np.nan


def first_fill(D, a, b, hi, lo):
    up = np.flatnonzero(D["ah"][a:b] >= hi); dn = np.flatnonzero(D["bl"][a:b] <= lo)
    ku, kd = (a + up[0] if len(up) else None), (a + dn[0] if len(dn) else None)
    if (ku is None and kd is None) or (ku is not None and ku == kd):
        return None
    side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
    k = ku if side > 0 else kd
    return k, side, (max(hi, D["ao"][k]) if side > 0 else min(lo, D["bo"][k]))


def market(args):
    """per market: O2 rows for every market; session-30 breakouts (side, fill time) for US + DAX; O1 rows for US indices."""
    sym, end = args
    D = load(sym, end)
    t = D["t"]
    tz, op_s, cl_s = session(sym)
    lc = local_clock(t, tz)
    rng = np.random.default_rng(zlib.crc32(sym.encode()) + 12)
    o2, s30, o1 = [], [], []
    for d in np.unique(lc // 86400):
        base = d * 86400
        i0 = np.searchsorted(lc, base + op_s)
        xe = np.searchsorted(lc, base + cl_s)
        if xe >= len(t) or lc[min(xe, len(t) - 1)] // 86400 != d:
            xe -= 1
        if i0 >= len(t) or lc[i0] // 86400 != d or xe <= i0 + 90:
            continue
        cap = np.searchsorted(t, (t[i0] // 86400) * 86400 + 22 * H + 55 * M)
        kend = min(xe, cap, len(t) - 1)
        day = pd.Timestamp(d * 86400, unit="s")
        w1 = np.searchsorted(lc, base + op_s + 3 * H)
        for L, store in ((60, "o2"), (30, "s30")):
            i1 = np.searchsorted(lc, base + op_s + L * M)
            if i1 - i0 < L * 0.6 or w1 <= i1 + 20:
                continue
            Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
            sp = np.median(D["ao"][i0:i1] - D["bo"][i0:i1])
            f = first_fill(D, i1, w1, Hb, Lb)
            if not f or not Hb > Lb:
                continue
            k, side, e = f
            R = abs(e - (Lb if side > 0 else Hb))
            if k >= kend or not (R > 0 and R >= 2 * (D["ao"][k] - D["bo"][k])):
                continue
            x = exits(D, k, kend, side, e, R)
            if not x:
                continue
            row = dict(mkt=sym, day=day, side=side, t_fill=int(t[k]), R=x[3], C=ctrl(D, rng, i1, w1, kend, R), box_spreads=(Hb - Lb) / sp if sp > 0 else np.nan)
            (o2 if store == "o2" else s30).append(row)
        if sym in US:                                                  # O1 overnight range 18:00 prev -> 09:30 NY
            a, b = np.searchsorted(lc, base - 6 * H + 18 * H - 24 * H + 24 * H - 6 * H), np.searchsorted(lc, base + 9 * H + 30 * M)
            a = np.searchsorted(lc, base - 6 * H)                      # 18:00 NY the previous evening
            if b - a < 300:
                continue
            Ho, Lo = D["bh"][a:b].max(), D["bl"][a:b].min()
            wb = np.searchsorted(lc, base + 12 * H)
            kx = min(np.searchsorted(lc, base + 15 * H + 55 * M), cap, len(t) - 1)
            f = first_fill(D, b, wb, Ho, Lo)
            if f:
                k, side, e = f
                R = abs(e - (Ho + Lo) / 2)
                if k < kx and R > 0 and R >= 2 * (D["ao"][k] - D["bo"][k]):
                    x = exits(D, k, kx, side, e, R)
                    if x:
                        o1.append(dict(mkt=sym, day=day, side=side, t_fill=int(t[k]), R=x[3], C=ctrl(D, rng, b, wb, kx, R)))
    return sym, o2, s30, o1


def collect(end):
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, [(s, end) for s in SYMS]))
    O2 = pd.DataFrame([r for _, o2, _, _ in res for r in o2])
    S30 = pd.DataFrame([r for s, _, s30, _ in res if s in US + ("DAX",) for r in s30])
    O1 = pd.DataFrame([r for _, _, _, o1 in res for r in o1])
    # O3 intermarket confirmation and O4 DAX lead, built from the 30-minute session breakouts
    piv = {m: S30[S30.mkt == m].set_index("day") for m in US + ("DAX",)}
    o3, o4 = [], []
    for m, partner in (("SP", "NSDQ"), ("NSDQ", "SP"), ("DOW", "SP")):
        a, p = piv[m], piv[partner]
        for d, r in a.iterrows():
            if d in p.index and p.at[d, "side"] == r.side and p.at[d, "t_fill"] <= r.t_fill:
                o3.append({**r.to_dict(), "mkt": m, "day": d})
    dax = piv["DAX"]
    for m in US:
        for d, r in piv[m].iterrows():
            if d in dax.index and dax.at[d, "side"] == r.side and dax.at[d, "t_fill"] < r.t_fill:
                o4.append({**r.to_dict(), "mkt": m, "day": d})
    cells = {"O1_overnight_range": O1, "O2_initial_balance_60": O2, "O3_intermarket_confirm": pd.DataFrame(o3), "O4_dax_lead": pd.DataFrame(o4)}
    base_us = S30[S30.mkt.isin(US)]
    return {k: v[v.day >= DEV[0]] for k, v in cells.items()}, base_us[base_us.day >= DEV[0]]


def dry():
    cells, base_us = collect(END)
    for k, v in cells.items():
        print(k, {p: int(((v.day >= a) & (v.day <= b)).sum()) for p, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26))})
    print("US base (30-min session breakouts):", len(base_us))
    x = cells["O1_overnight_range"]; x = x[(x.mkt == "NSDQ") & (x.day == "2024-06-12")]
    print("hand check O1 NSDQ 2024-06-12:", x[["side", "t_fill", "R"]].assign(t_fill=pd.to_datetime(x.t_fill, unit="s").astype(str)).round(3).to_dict("records"))


def run():
    cells, base_us = collect(END)
    pd.concat([v.assign(cell=k) for k, v in cells.items()]).to_parquet("data/si_ledgers/BRK_B12.parquet")
    print("US 30-min session breakouts, no filter: " + " | ".join(f"{p} {base_us[(base_us.day >= a) & (base_us.day <= b)].R.mean():+.3f}" for p, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26))))
    for k, v in cells.items():
        r = {}
        for p, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)):
            s = v[(v.day >= a) & (v.day <= b)]
            r[p] = (len(s), s.R.mean(), nw_t(s.groupby("day").R.mean().to_numpy()), s.C.mean())
        g = [r["DEV"][1] >= 0.05 and r["DEV"][2] >= 2.5, r["VAL"][1] > 0 and r["VAL"][2] >= 1.65, r["DEV"][1] - r["DEV"][3] >= 0.05 and r["VAL"][1] - r["VAL"][3] >= 0.05]
        extra = f" | box>=25sp DEV/VAL/2026 " + "/".join(f"{v[(v.day >= a) & (v.day <= b) & (v.box_spreads >= 25)].R.mean():+.3f}" for a, b in (DEV, VAL, Y26)) if "box_spreads" in v and v.box_spreads.notna().any() else ""
        print(f"{k}: " + " | ".join(f"{p} n{x[0]} {x[1]:+.3f} (t {x[2]:+.2f}) ctl {x[3]:+.3f}" for p, x in r.items()) + f" | gates {''.join('Y' if z else 'n' for z in g)} PASS {all(g)}" + extra)


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
