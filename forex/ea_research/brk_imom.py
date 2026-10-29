"""BRK-IMOM exactly as in PREREG_BRK_IMOM.md: intraday momentum (first half hour -> last half hour), 46 markets.
   python -m forex.ea_research.brk_imom --dry | (no flag) run"""
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


def market(args):
    sym, end = args
    D = load(sym, end)
    t = D["t"]
    tz, op, cl = session(sym)
    lc = local_clock(t, tz)
    mid = (D["bo"] + D["ao"]) / 2
    rng = np.random.default_rng(zlib.crc32(sym.encode()) + 28)
    rows, prev_close = [], None
    for d in np.unique(lc // 86400):
        base = d * 86400
        idx = {}
        for name, off in (("o30", op + 30 * M), ("l60", cl - 61 * M), ("l30", cl - 31 * M), ("cl", cl - M)):
            j = np.searchsorted(lc, base + off)
            idx[name] = j if j < len(t) and lc[j] // 86400 == d and lc[j] - (base + off) < 5 * M else None
        pc, prev_close = prev_close, (mid[idx["cl"]] if idx["cl"] is not None else None)
        if pc is None or any(v is None for v in idx.values()):
            continue
        a, b = idx["l30"], idx["cl"]
        if (t[a] % 86400) // H in (23, 0) or (t[b] % 86400) // H in (23, 0):
            continue
        r_first = mid[idx["o30"]] / pc - 1
        r_12 = mid[idx["l30"]] / mid[idx["l60"]] - 1
        side = 1 if r_first > 0 else -1
        ref = mid[a]
        long_bp = (D["bo"][b] - D["ao"][a]) / ref * 1e4
        short_bp = (D["bo"][a] - D["ao"][b]) / ref * 1e4
        g = long_bp if side > 0 else short_bp
        rs = long_bp if rng.random() < 0.5 else short_bp
        rows.append((sym, base, int(t[a]), side, r_first, r_12, g, int(np.sign(r_first) == np.sign(r_12)), long_bp, rs))
    return rows


def collect(end):
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, [(s, end) for s in SYMS]))
    df = pd.DataFrame([r for rr in res for r in rr], columns=["mkt", "d", "t_entry", "side", "r_first", "r_12", "G", "agree", "LONG", "RAND"])
    df["day"] = pd.to_datetime(df.d, unit="s")
    df["c"] = df.mkt.map(mclass)
    return df[df.day >= DEV[0]]


def dry():
    df = collect(END)
    print("days per class:", df.groupby("c").size().to_dict(), "| agree share", round(df.agree.mean(), 3))
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    f, p = pd.DataFrame(market(("NSDQ", END))), pd.DataFrame(market(("NSDQ", cut)))
    f, p = f[f[2] < cut - 86400].reset_index(drop=True), p[p[2] < cut - 86400].reset_index(drop=True)
    ok = len(f) == len(p) and np.allclose(f[6].to_numpy(), p[6].to_numpy())
    print("truncation:", "PASS" if ok else f"FAIL {len(f)} {len(p)}")
    x = df[(df.mkt == "SP") & (df.day >= "2024-06-10") & (df.day <= "2024-06-12")]
    print("hand check SP:", x[["day", "side", "r_first", "r_12", "G", "LONG"]].round(5).to_dict("records"))


def run():
    df = collect(END)
    df.to_parquet("data/si_ledgers/BRK_IMOM.parquet")
    for cls in ("index", "fx", "metal", "energy", "crypto"):
        for cell in ("G1", "G2"):
            g = df[df.c == cls]
            if cell == "G2":
                g = g[g.agree == 1]
            r = {}
            for lab, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)):
                s = g[(g.day >= a) & (g.day <= b)]
                r[lab] = (len(s), s.G.mean(), nw_t(s.groupby("day").G.mean().to_numpy()), s.LONG.mean(), s.RAND.mean())
            gt = [r["DEV"][1] > 0 and r["DEV"][2] >= 2.24, r["VAL"][1] > 0 and r["VAL"][2] >= 1.65, r["DEV"][1] > r["DEV"][3] and r["VAL"][1] > r["VAL"][3]]
            tag = "PRIMARY " if cls == "index" else "descr.  "
            print(f"{tag}{cls} {cell}: " + " | ".join(f"{k} n{v[0]} {v[1]:+.2f} bp (t {v[2]:+.2f}) long {v[3]:+.2f} rand {v[4]:+.2f}" for k, v in r.items()) + (f" | gates {''.join('Y' if z else 'n' for z in gt)} PASS {all(gt)}" if cls == "index" else ""))
    g = df[df.c == "index"]
    print("index G1 by market DEV/VAL/2026 (bp): " + " | ".join(f"{m} " + "/".join(f"{x[(x.day >= a) & (x.day <= b)].G.mean():+.1f}" for a, b in (DEV, VAL, Y26)) for m, x in g.groupby("mkt")))


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
