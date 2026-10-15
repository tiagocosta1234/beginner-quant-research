"""BRK-SQUEEZE exactly as in PREREG_BRK_SQUEEZE.md: TTM-squeeze breakouts (M15 range break, M15 release, H1 range break) on 46 markets.
   python -m forex.ea_research.brk_squeeze --dry | (no flag) run"""
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.brk_hours import hold
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS, nw_t

END = pd.Timestamp("2026-10-03").timestamp()
H, M = 3600, 60
DEV, VAL, Y26 = ("2022-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-10-02")
CELLS = (("Q1", 900, 8, 4 * H), ("Q2", 900, 0, 4 * H), ("Q3", 3600, 4, 8 * H))


def bars(D, sec):
    t = D["t"]
    key = t // sec
    st = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    en = np.r_[st[1:], len(t)]
    mid_h = np.maximum.reduceat((D["bh"] + D["ah"]) / 2, st)
    mid_l = np.minimum.reduceat((D["bl"] + D["al"]) / 2, st)
    mid_c = ((D["bc"] + D["ac"]) / 2)[en - 1]
    bh = np.maximum.reduceat(D["bh"], st)
    bl = np.minimum.reduceat(D["bl"], st)
    return key[st], st, en, mid_h, mid_l, mid_c, bh, bl


def squeeze_flags(mid_h, mid_l, mid_c):
    c = pd.Series(mid_c)
    sma, sd = c.rolling(20).mean(), c.rolling(20).std(ddof=0)
    pc = c.shift(1)
    tr = pd.concat([pd.Series(mid_h - mid_l), (pd.Series(mid_h) - pc).abs(), (pd.Series(mid_l) - pc).abs()], axis=1).max(axis=1)
    atr = tr.rolling(20).mean()
    ema = c.ewm(span=20, adjust=False).mean()
    sq = (sma + 2 * sd < ema + 1.5 * atr) & (sma - 2 * sd > ema - 1.5 * atr)
    return sq.to_numpy(), sma.to_numpy(), atr.to_numpy()


def market(args):
    sym, end = args
    D = load(sym, end)
    t = D["t"]
    rng = np.random.default_rng(zlib.crc32(sym.encode()) + 26)
    rows = []
    for cell, sec, nwin, hold_s in CELLS:
        key, st, en, mh, ml, mc, bh, bl = bars(D, sec)
        sq, sma, atr = squeeze_flags(mh, ml, mc)
        hr = (key * sec % 86400) // H
        bad = (hr == 23) | (hr == 0) | np.r_[True, np.diff(key) != 1]
        run = np.zeros(len(key), int)
        for j in range(len(key)):
            run[j] = 0 if (bad[j] or not sq[j]) else (run[j - 1] + 1 if j else 1)
        busy = -1
        nb = len(key)
        for j in range(nb - 1):
            k = None
            if cell in ("Q1", "Q3"):
                if run[j] != 6 or j + nwin >= nb or st[j + 1] <= busy:
                    continue
                hi, lo = bh[j - 5:j + 1].max(), bl[j - 5:j + 1].min()
                a, b = st[j + 1], en[min(j + nwin, nb - 1)]
                if key[min(j + nwin, nb - 1)] - key[j] != nwin:
                    continue
                up = np.flatnonzero(D["ah"][a:b] >= hi)
                dn = np.flatnonzero(D["bl"][a:b] <= lo)
                ku = a + up[0] if len(up) else None
                kd = a + dn[0] if len(dn) else None
                if (ku is None and kd is None) or (ku is not None and ku == kd):
                    continue
                side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
                k = ku if side > 0 else kd
                e = max(hi, D["ao"][k]) if side > 0 else min(lo, D["bo"][k])
                R = abs(e - (lo if side > 0 else hi))
                kc = int(rng.integers(a, b))
            else:
                if not (j >= 1 and run[j - 1] >= 6 and run[j] == 0 and not bad[j]) or key[j + 1] - key[j] != 1 or st[j + 1] <= busy:
                    continue
                if not np.isfinite(atr[j]):
                    continue
                side = 1 if mc[j] > sma[j] else -1
                k = st[j + 1]
                e = D["ao"][k] if side > 0 else D["bo"][k]
                R = 1.5 * atr[j]
                kc = k
            if (t[k] % 86400) // H in (23, 0):
                continue
            sp = D["ao"][k] - D["bo"][k]
            if not (R > 0 and R >= 2 * sp):
                continue
            kend = min(np.searchsorted(t, min(t[k] + hold_s, (t[k] // 86400) * 86400 + 22 * H + 55 * M)), len(t) - 1)
            if kend <= k:
                continue
            sc = 1 if rng.random() < 0.5 else -1
            ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
            rows.append((cell, sym, int(t[k] // 86400) * 86400, side, int(t[k]), hold(D, k, kend, side, e, R), hold(D, kc, kend, sc, ec, R) if kc < kend else np.nan))
            busy = kend
    return rows


def collect(end):
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, [(s, end) for s in SYMS]))
    df = pd.DataFrame([r for rr in res for r in rr], columns=["cell", "mkt", "d", "side", "t_entry", "R", "C"])
    df["day"] = pd.to_datetime(df.d, unit="s")
    df["c"] = df.mkt.map(mclass)
    return df[df.day >= DEV[0]]


def dry():
    df = collect(END)
    print("events per cell:", df.groupby("cell").size().to_dict(), "| DEV/VAL/2026:", {c: [int(((g.day >= a) & (g.day <= b)).sum()) for a, b in (DEV, VAL, Y26)] for c, g in df.groupby("cell")})
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    f, p = pd.DataFrame(market(("NSDQ", END))), pd.DataFrame(market(("NSDQ", cut)))
    f, p = f[f[4] < cut - 86400].reset_index(drop=True), p[p[4] < cut - 86400].reset_index(drop=True)
    ok = len(f) == len(p) and np.allclose(f[5].to_numpy(), p[5].to_numpy(), equal_nan=True)
    print("truncation:", "PASS" if ok else f"FAIL {len(f)} {len(p)}")
    x = df[(df.mkt == "XAUUSD") & (df.day >= "2024-06-10") & (df.day <= "2024-06-12")]
    print("hand check XAUUSD 2024-06-10..12:", x[["cell", "side", "t_entry", "R", "C"]].assign(t_entry=lambda z: pd.to_datetime(z.t_entry, unit="s")).round(3).to_dict("records")[:6])


def run():
    df = collect(END)
    df.to_parquet("D:/finance/si_ledgers/BRK_SQUEEZE.parquet")
    names = {"Q1": "M15 squeeze range break", "Q2": "M15 squeeze release (TTM)", "Q3": "H1 squeeze range break"}
    for cell, g in df.groupby("cell"):
        r = {}
        for lab, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)):
            s = g[(g.day >= a) & (g.day <= b)]
            r[lab] = (len(s), s.R.mean(), nw_t(s.groupby("day").R.mean().to_numpy()), s.C.mean())
        gt = [r["DEV"][1] >= 0.05 and r["DEV"][2] >= 2.39, r["VAL"][1] > 0 and r["VAL"][2] >= 1.65, r["DEV"][1] - r["DEV"][3] >= 0.05 and r["VAL"][1] - r["VAL"][3] >= 0.05]
        print(f"{cell} {names[cell]}: " + " | ".join(f"{k} n{v[0]} {v[1]:+.3f} (t {v[2]:+.2f}) ctl {v[3]:+.3f}" for k, v in r.items()) + f" | gates {''.join('Y' if z else 'n' for z in gt)} PASS {all(gt)}")
        print("    by class DEV/VAL/2026: " + " | ".join(f"{c} " + "/".join(f"{x[(x.day >= a) & (x.day <= b)].R.mean():+.3f}" for a, b in (DEV, VAL, Y26)) for c, x in g.groupby("c")))


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
