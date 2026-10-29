"""BRK-LAG exactly as in PREREG_BRK_LAG.md: laggard entries inside groups of related markets.
   python -m forex.ea_research.brk_lag --dry | (no flag) run"""
import math
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.breakouts import local_clock, session
from forex.ea_research.brk_hours import hold
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS, nw_t

END = pd.Timestamp("2026-10-03").timestamp()
H, M = 3600, 60
DEV, VAL, Y26 = ("2022-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-10-02")
GROUPS = {
    "US_IDX": {"SP": 1, "NSDQ": 1, "DOW": 1},
    "USD_FX": {"EURUSD": 1, "GBPUSD": 1, "AUDUSD": 1, "NZDUSD": 1, "USDCHF": -1, "USDCAD": -1, "USDJPY": -1},
    "JPY": {"EURJPY": 1, "GBPJPY": 1, "AUDJPY": 1, "CADJPY": 1, "CHFJPY": 1, "NZDJPY": 1, "USDJPY": 1},
    "METAL": {"XAUUSD": 1, "XAGUSD": 1},
    "ENERGY": {"BRENT": 1, "WTI": 1},
    "CRYPTO": {"BTCUSD": 1, "ETHUSD": 1, "SOLUSD": 1, "XRPUSD": 1, "ADAUSD": 1, "LTCUSD": 1, "BCHUSD": 1, "BNBUSD": 1},
}


def day_info(D, lc, d, op_s):
    """box, first breakout (local-clock second, group-free side) for one member and local day."""
    base = d * 86400
    i0, i1 = np.searchsorted(lc, base + op_s), np.searchsorted(lc, base + op_s + 30 * M)
    w1 = np.searchsorted(lc, base + op_s + 3 * H)
    if i1 >= len(lc) or i1 - i0 < 20 or lc[i0] // 86400 != d or w1 <= i1 + 30:
        return None
    Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
    if not Hb > Lb:
        return None
    up = np.flatnonzero(D["ah"][i1:w1] >= Hb)
    dn = np.flatnonzero(D["bl"][i1:w1] <= Lb)
    ku = i1 + up[0] if len(up) else None
    kd = i1 + dn[0] if len(dn) else None
    if ku is None and kd is None:
        return dict(Hb=Hb, Lb=Lb, i1=i1, w1=w1, t_brk=np.inf, side=0)
    if ku is not None and ku == kd:
        return dict(Hb=Hb, Lb=Lb, i1=i1, w1=w1, t_brk=lc[ku], side=0)
    side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
    k = ku if side > 0 else kd
    return dict(Hb=Hb, Lb=Lb, i1=i1, w1=w1, t_brk=lc[k], side=side)


def group(args):
    gname, end = args
    mem = GROUPS[gname]
    syms = [s for s in mem if s in SYMS]
    tz, op_s, cl_s = session(syms[0])
    Ds = {s: load(s, end) for s in syms}
    lcs = {s: local_clock(Ds[s]["t"], tz) for s in syms}
    days = sorted(set.intersection(*[set(np.unique(lcs[s] // 86400)) for s in syms]))
    q = max(1, math.ceil((len(syms) - 1) / 2))
    rows = []
    for d in days:
        info = {s: day_info(Ds[s], lcs[s], d, op_s) for s in syms}
        if any(v is None for v in info.values()):
            continue
        events = sorted((v["t_brk"], s, v["side"] * mem[s]) for s, v in info.items() if np.isfinite(v["t_brk"]) and v["side"] != 0)
        for m in syms:
            D, lc, t = Ds[m], lcs[m], Ds[m]["t"]
            v = info[m]
            cnt = {1: 0, -1: 0}
            for tb, s, gdir in events:
                if s == m:
                    continue
                if tb >= v["t_brk"]:
                    break
                cnt[gdir] += 1
                if cnt[gdir] >= q:
                    k = np.searchsorted(lc, tb + 60)
                    if k >= v["w1"] or k >= len(t) or lc[k] >= v["t_brk"]:
                        break
                    if (t[k] % 86400) // H in (23, 0):
                        break
                    side = gdir * mem[m]
                    xe = np.searchsorted(lc, d * 86400 + cl_s)
                    if xe >= len(t) or lc[min(xe, len(t) - 1)] // 86400 != d:
                        xe -= 1
                    kend = min(xe, np.searchsorted(t, (t[k] // 86400) * 86400 + 22 * H + 55 * M), len(t) - 1)
                    R = v["Hb"] - v["Lb"]
                    if kend <= k or R < 2 * (D["ao"][k] - D["bo"][k]):
                        break
                    e = D["ao"][k] if side > 0 else D["bo"][k]
                    rng = np.random.default_rng(zlib.crc32(f"{m}{d}".encode()) + 31)
                    sc = 1 if rng.random() < 0.5 else -1
                    ec = D["ao"][k] if sc > 0 else D["bo"][k]
                    rows.append((gname, m, int(t[k] // 86400) * 86400, side, int(t[k]), hold(D, k, kend, side, e, R), hold(D, k, kend, sc, ec, R)))
                    break
    return rows


def collect(end):
    with ProcessPoolExecutor(6) as ex:
        res = list(ex.map(group, [(g, end) for g in GROUPS]))
    df = pd.DataFrame([r for rr in res for r in rr], columns=["grp", "mkt", "d", "side", "t_entry", "R", "C"])
    df["day"] = pd.to_datetime(df.d, unit="s")
    return df[df.day >= DEV[0]]


def dry():
    df = collect(END)
    print("laggard entries:", len(df), "| per group:", df.groupby("grp").size().to_dict())
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    f, p = pd.DataFrame(group(("US_IDX", END))), pd.DataFrame(group(("US_IDX", cut)))
    f, p = f[f[4] < cut - 86400].reset_index(drop=True), p[p[4] < cut - 86400].reset_index(drop=True)
    ok = len(f) == len(p) and np.allclose(f[5].to_numpy(), p[5].to_numpy())
    print("truncation:", "PASS" if ok else f"FAIL {len(f)} {len(p)}")
    x = df[(df.grp == "US_IDX") & (df.day >= "2024-06-10") & (df.day <= "2024-06-14")]
    print("hand check US_IDX:", x[["day", "mkt", "side", "t_entry", "R", "C"]].assign(t_entry=lambda z: pd.to_datetime(z.t_entry, unit="s")).round(3).to_dict("records")[:6])


def run():
    df = collect(END)
    df.to_parquet("data/si_ledgers/BRK_LAG.parquet")
    r = {}
    for lab, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)):
        s = df[(df.day >= a) & (df.day <= b)]
        r[lab] = (len(s), s.R.mean(), nw_t(s.groupby("day").R.mean().to_numpy()), s.C.mean())
    gt = [r["DEV"][1] >= 0.05 and r["DEV"][2] >= 1.96, r["VAL"][1] > 0 and r["VAL"][2] >= 1.65, r["DEV"][1] - r["DEV"][3] >= 0.05 and r["VAL"][1] - r["VAL"][3] >= 0.05]
    print("Z1 laggard entry: " + " | ".join(f"{k} n{v[0]} {v[1]:+.3f} (t {v[2]:+.2f}) ctl {v[3]:+.3f}" for k, v in r.items()) + f" | gates {''.join('Y' if z else 'n' for z in gt)} PASS {all(gt)}")
    for g, x in df.groupby("grp"):
        print(f"    {g}: " + " | ".join(f"{lab} n{len(s)} {s.R.mean():+.3f} ctl {s.C.mean():+.3f}" for lab, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)) for s in [x[(x.day >= a) & (x.day <= b)]]))


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
