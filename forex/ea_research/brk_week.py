"""BRK-WEEK exactly as in PREREG_BRK_WEEK.md: Monday-range, previous-week-range and month-opening-range breakouts on 46 MT5.
   python -m forex.ea_research.brk_week --dry | (no flag) run"""
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.brk_exits import exits
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS, nw_t

END = pd.Timestamp("2026-10-03").timestamp()
H, M = 3600, 60
DEV, VAL, Y26 = ("2022-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-10-02")
INDICES = ("SP", "NSDQ", "DOW", "DAX", "NIKKEI", "ASX")


def trade(D, rng, cell, wa, wb, kend, Hb, Lb, stop_long, stop_short, start_day):
    """stop orders at Hb / Lb live on [wa, wb), exit by kend; returns rows for the trade and its control."""
    t = D["t"]
    out = []
    if wb <= wa or kend <= wa:
        return out
    up = np.flatnonzero(D["ah"][wa:wb] >= Hb)
    dn = np.flatnonzero(D["bl"][wa:wb] <= Lb)
    ku, kd = (wa + up[0] if len(up) else None), (wa + dn[0] if len(dn) else None)
    if (ku is None and kd is None) or (ku is not None and ku == kd):
        return out
    side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
    k = ku if side > 0 else kd
    e = max(Hb, D["ao"][k]) if side > 0 else min(Lb, D["bo"][k])
    R = abs(e - (stop_long if side > 0 else stop_short))
    if k >= kend or not (R > 0 and R >= 2 * (D["ao"][k] - D["bo"][k])):
        return out
    x = exits(D, k, kend, side, e, R)
    kc = int(rng.integers(wa, wb))
    sc = 1 if rng.random() < 0.5 else -1
    ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
    xc = exits(D, kc, kend, sc, ec, R) if kc < kend and R >= 2 * (D["ao"][kc] - D["bo"][kc]) else None
    if x is not None:
        out.append((cell, pd.Timestamp(start_day * 86400, unit="s"), side, int(t[k]), x[3], x[1], xc[3] if xc else np.nan, xc[1] if xc else np.nan))
    return out


def market(args):
    sym, end = args
    D = load(sym, end)
    t = D["t"]
    rng = np.random.default_rng(zlib.crc32(sym.encode()) + 99)
    day, sod = t // 86400, t % 86400
    st = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    en = np.r_[st[1:], len(t)]
    rows = []
    info = {}
    for a, b in zip(st, en):
        w = np.arange(a, b)[(sod[a:b] >= H) & (sod[a:b] < 23 * H)]
        if len(w) < 300:
            continue
        d = int(day[a])
        info[d] = dict(a=a, b=b, hi=D["bh"][w].max(), lo=D["bl"][w].min(), wd=(d + 3) % 7,
                       k_open=a + np.searchsorted(sod[a:b], H + 5 * M), k_close=a + np.searchsorted(sod[a:b], 21 * H + 55 * M),
                       k_last=a + np.searchsorted(sod[a:b], 22 * H + 55 * M))
    days = sorted(d for d in info if info[d]["wd"] < 5)
    weeks = {}
    for d in days:
        weeks.setdefault((d + 3) // 7, []).append(d)
    wkeys = sorted(weeks)
    for n_, wk in enumerate(wkeys):
        ds = weeks[wk]
        by = {info[d]["wd"]: d for d in ds}
        if 4 not in by:
            continue
        kend = min(info[by[4]]["k_close"], len(t) - 1)
        # W1 Monday range -> Tue..Thu
        if 0 in by and 1 in by:
            mon = info[by[0]]
            thu = info[by.get(3, by[max(k for k in by if k < 4)])]
            wa, wb = info[by[1]]["k_open"], thu["k_last"]
            rows += [(sym,) + r for r in trade(D, rng, "W1", wa, wb, kend, mon["hi"], mon["lo"], mon["lo"], mon["hi"], by[1])]
        # W2 previous week's range -> Mon..Thu, stop at its midpoint
        if n_ > 0 and wkeys[n_ - 1] == wk - 1:
            pw = weeks[wkeys[n_ - 1]]
            ph, pl = max(info[d]["hi"] for d in pw), min(info[d]["lo"] for d in pw)
            first = info[ds[0]]
            thu = info[by.get(3, by[max(k for k in by if k < 4)])]
            mid = (ph + pl) / 2
            rows += [(sym,) + r for r in trade(D, rng, "W2", first["k_open"], thu["k_last"], kend, ph, pl, mid, mid, ds[0])]
    months = {}
    for d in days:
        months.setdefault(pd.Timestamp(d * 86400, unit="s").to_period("M"), []).append(d)
    for mth, ds in sorted(months.items()):
        if len(ds) < 10:
            continue
        box = ds[:3]
        hb, lb = max(info[d]["hi"] for d in box), min(info[d]["lo"] for d in box)
        fifteenth = [d for d in ds[3:] if pd.Timestamp(d * 86400, unit="s").day <= 15]
        if not fifteenth:
            continue
        wa, wb = info[ds[3]]["k_open"], info[fifteenth[-1]]["k_last"]
        kend = min(info[ds[-1]]["k_close"], len(t) - 1)
        rows += [(sym,) + r for r in trade(D, rng, "W4", wa, wb, kend, hb, lb, lb, hb, ds[3])]
    return rows


COLS = ["mkt", "cell", "day", "side", "t_entry", "E_close", "E_2R", "C_close", "C_2R"]


def collect(end):
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, [(s, end) for s in SYMS]))
    df = pd.DataFrame([r for rr in res for r in rr], columns=COLS)
    return df[df.day >= DEV[0]]


def dry():
    t0 = time.time()
    df = collect(END)
    print(f"{time.time() - t0:.0f}s")
    print(df.assign(per=np.where(df.day <= DEV[1], "DEV", np.where(df.day <= VAL[1], "VAL", "2026"))).groupby(["cell", "per"]).size().unstack())
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    bad = 0
    for s in ("EURUSD", "XAUUSD", "NSDQ"):
        f = pd.DataFrame(market((s, END)), columns=COLS); p = pd.DataFrame(market((s, cut)), columns=COLS)
        f, p = f[f.t_entry < cut - 40 * 86400].reset_index(drop=True), p[p.t_entry < cut - 40 * 86400].reset_index(drop=True)
        bad += int(not (len(f) == len(p) and np.allclose(f[["E_close", "E_2R"]].to_numpy(), p[["E_close", "E_2R"]].to_numpy(), equal_nan=True)))
    print("truncation test:", "PASS" if bad == 0 else f"FAIL {bad}")
    x = df[(df.mkt == "XAUUSD") & (df.cell == "W1")].iloc[40]
    print("hand check XAUUSD W1:", x.day.date(), "side", x.side, "entry", pd.Timestamp(x.t_entry, unit="s"), "E_close", round(x.E_close, 3))


def run():
    df = collect(END)
    df.to_parquet("D:/finance/si_ledgers/BRK_WEEK.parquet")
    df["wk"] = df.day.dt.to_period("W")
    rows = []
    for cell in ("W1", "W2", "W4"):
        g = df[df.cell == cell]
        for ex, ctl in (("E_close", "C_close"), ("E_2R", "C_2R")):
            r = dict(cell=f"{cell}-{ex}")
            for lab, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)):
                s = g[(g.day >= a) & (g.day <= b)]
                r[f"n {lab}"], r[f"R {lab}"], r[f"t {lab}"], r[f"ctl {lab}"] = len(s), s[ex].mean(), nw_t(s.groupby("wk")[ex].mean().to_numpy()), s[ctl].mean()
            gate = [r["R DEV"] >= 0.05 and r["t DEV"] >= 2.4, r["R VAL"] > 0 and r["t VAL"] >= 1.65, r["R DEV"] - r["ctl DEV"] >= 0.05 and r["R VAL"] - r["ctl VAL"] >= 0.05]
            r["gates"], r["PASS"] = "".join("Y" if v else "n" for v in gate), all(gate)
            ix = g[g.mkt.isin(INDICES)]
            r["indices"] = " / ".join(f"{ix[(ix.day >= a) & (ix.day <= b)][ex].mean():+.3f}" for a, b in (DEV, VAL, Y26))
            rows.append(r)
    R = pd.DataFrame(rows)
    pd.set_option("display.width", 260)
    print(R.round(3).to_string(index=False))
    R.to_csv("D:/finance/si_ledgers/BRK_WEEK_cells.csv", index=False)
    print("\nby class, E_close (DEV / VAL / 2026):")
    for cell in ("W1", "W2", "W4"):
        g = df[df.cell == cell].assign(c=lambda z: z.mkt.map(mclass))
        print(f"  {cell}: " + " | ".join(f"{c} {x[x.day <= DEV[1]].E_close.mean():+.3f}/{x[(x.day >= VAL[0]) & (x.day <= VAL[1])].E_close.mean():+.3f}/{x[x.day >= Y26[0]].E_close.mean():+.3f}" for c, x in g.groupby("c")))


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
