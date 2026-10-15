"""BRK-ROUND exactly as in PREREG_BRK_ROUND.md: breakouts through fresh round-number levels (Osler 2003) vs non-round levels.
   python -m forex.ea_research.brk_round --dry | (no flag) run"""
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.brk_hours import hold, hold_fill
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS, nw_t

END = pd.Timestamp("2026-10-03").timestamp()
H, M = 3600, 60
DEV, VAL, Y26 = ("2022-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-10-02")
CELLS = (("K1", 60 * M), ("K2", 4 * H))


def nice_step(p):
    x = 0.005 * p
    e = np.floor(np.log10(x))
    cand = np.array([1, 2, 5, 10]) * 10.0 ** e
    return cand[np.argmin(np.abs(np.log(cand / x)))]


def market(args):
    sym, end = args
    D = load(sym, end)
    t = D["t"]
    n = len(t)
    day = t // 86400
    ud, first = np.unique(day, return_index=True)
    last = np.r_[first[1:], n] - 1
    mid_close = (D["bc"] + D["ac"]) / 2
    step_day = {ud[i]: nice_step(mid_close[last[i - 1]]) for i in range(1, len(ud))}
    step = np.array([step_day.get(d, np.nan) for d in day])
    prev_hi = pd.Series(D["ah"]).rolling(1440, min_periods=1440).max().shift(1).to_numpy()
    prev_lo = pd.Series(D["bl"]).rolling(1440, min_periods=1440).min().shift(1).to_numpy()
    hr = (t % 86400) // H
    ok_hr = (hr != 23) & (hr != 0)
    rng = np.random.default_rng(zlib.crc32(sym.encode()) + 27)
    rows = []
    for kind, off in (("round", 0.0), ("offset", 0.37)):
        with np.errstate(invalid="ignore"):
            lvl_up = (np.floor((prev_hi - off * step) / step) + 1) * step + off * step
            lvl_dn = (np.ceil((prev_lo - off * step) / step) - 1) * step + off * step
            up = (D["ah"] >= lvl_up) & ok_hr & np.isfinite(lvl_up)
            dn = (D["bl"] <= lvl_dn) & ok_hr & np.isfinite(lvl_dn)
        ev = np.flatnonzero(up ^ dn)
        for cell, hold_s in CELLS:
            busy = -1
            for k in ev:
                if k <= busy:
                    continue
                side = 1 if up[k] else -1
                L = lvl_up[k] if side > 0 else lvl_dn[k]
                e = max(L, D["ao"][k]) if side > 0 else min(L, D["bo"][k])
                R = 0.5 * step[k]
                sp = D["ao"][k] - D["bo"][k]
                if not (R > 0 and R >= 2 * sp):
                    continue
                kend = min(np.searchsorted(t, min(t[k] + hold_s, day[k] * 86400 + 22 * H + 55 * M)), n - 1)
                if kend <= k:
                    continue
                sc = 1 if rng.random() < 0.5 else -1
                ec = D["ao"][k] if sc > 0 else D["bo"][k]
                rows.append((kind, cell, sym, int(day[k]) * 86400, side, int(t[k]), hold_fill(D, k, kend, side, e, R), hold(D, k, kend, sc, ec, R), hold(D, k, kend, side, e, R)))
                busy = kend
    return rows


def collect(end):
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, [(s, end) for s in SYMS]))
    df = pd.DataFrame([r for rr in res for r in rr], columns=["kind", "cell", "mkt", "d", "side", "t_entry", "R", "C", "R_v0"])
    df["day"] = pd.to_datetime(df.d, unit="s")
    df["c"] = df.mkt.map(mclass)
    return df[df.day >= DEV[0]]


def dry():
    df = collect(END)
    print("events:", df.groupby(["kind", "cell"]).size().to_dict(), "| per market-day (round K1):", round(len(df[(df.kind == "round") & (df.cell == "K1")]) / df.groupby("mkt").day.nunique().sum(), 2))
    print("steps:", {s: nice_step(p) for s, p in (("EURUSD", 1.08), ("USDJPY", 150), ("XAUUSD", 4000), ("NSDQ", 20000), ("BTCUSD", 100000), ("WTI", 70))})
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    f, p = pd.DataFrame(market(("EURUSD", END))), pd.DataFrame(market(("EURUSD", cut)))
    f, p = f[f[5] < cut - 86400].reset_index(drop=True), p[p[5] < cut - 86400].reset_index(drop=True)
    ok = len(f) == len(p) and np.allclose(f[6].to_numpy(), p[6].to_numpy(), equal_nan=True)
    print("truncation:", "PASS" if ok else f"FAIL {len(f)} {len(p)}")
    x = df[(df.mkt == "EURUSD") & (df.cell == "K1") & (df.day >= "2024-06-10") & (df.day <= "2024-06-14")]
    print("hand check EURUSD K1 2024-06-10..14:", x[["kind", "side", "t_entry", "R"]].assign(t_entry=lambda z: pd.to_datetime(z.t_entry, unit="s")).round(3).to_dict("records")[:6])


def run():
    df = collect(END)
    df.to_parquet("D:/finance/si_ledgers/BRK_ROUND.parquet")
    for cell, g0 in df.groupby("cell"):
        g, o = g0[g0.kind == "round"], g0[g0.kind == "offset"]
        r = {}
        for lab, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)):
            s = g[(g.day >= a) & (g.day <= b)]
            so = o[(o.day >= a) & (o.day <= b)]
            r[lab] = (len(s), s.R.mean(), nw_t(s.groupby("day").R.mean().to_numpy()), so.R.mean(), s.C.mean())
        gt = [r["DEV"][1] >= 0.05 and r["DEV"][2] >= 2.24, r["VAL"][1] > 0 and r["VAL"][2] >= 1.65, r["DEV"][1] - r["DEV"][3] >= 0.05 and r["VAL"][1] - r["VAL"][3] >= 0.05]
        print(f"{cell} {'hold 60 min' if cell == 'K1' else 'hold 4 h'}: " + " | ".join(f"{k} n{v[0]} {v[1]:+.3f} (t {v[2]:+.2f}) non-round {v[3]:+.3f} random {v[4]:+.3f}" for k, v in r.items()) + f" | gates {''.join('Y' if z else 'n' for z in gt)} PASS {all(gt)}")
        print("    round by class DEV/VAL/2026: " + " | ".join(f"{c} " + "/".join(f"{x[(x.day >= a) & (x.day <= b)].R.mean():+.3f}" for a, b in (DEV, VAL, Y26)) for c, x in g.groupby("c")))
        print(f"    first run (fill-minute bug) round DEV/VAL/2026: " + "/".join(f"{g[(g.day >= a) & (g.day <= b)].R_v0.mean():+.3f}" for a, b in (DEV, VAL, Y26)))
        print("    non-round by class:          " + " | ".join(f"{c} " + "/".join(f"{x[(x.day >= a) & (x.day <= b)].R.mean():+.3f}" for a, b in (DEV, VAL, Y26)) for c, x in o.groupby("c")))


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
