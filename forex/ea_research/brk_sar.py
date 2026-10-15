"""BRK-SAR exactly as in PREREG_BRK_SAR.md: stop-and-reverse on the session box, and the yesterday-won streak filter.  python -m forex.ea_research.brk_sar"""
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


def market(sym):
    D = load(sym, END); t = D["t"]
    tz, op_s, cl_s = session(sym); lc = local_clock(t, tz)
    rng = np.random.default_rng(zlib.crc32(sym.encode()) + 18)
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
        if not Hb > Lb:
            continue
        up = np.flatnonzero(D["ah"][i1:w1] >= Hb); dn = np.flatnonzero(D["bl"][i1:w1] <= Lb)
        ku, kd = (i1 + up[0] if len(up) else None), (i1 + dn[0] if len(dn) else None)
        if (ku is None and kd is None) or (ku is not None and ku == kd):
            continue
        side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
        k = ku if side > 0 else kd
        e = max(Hb, D["ao"][k]) if side > 0 else min(Lb, D["bo"][k])
        stop = Lb if side > 0 else Hb
        R = abs(e - stop)
        if k >= kend or not (R > 0 and R >= 2 * (D["ao"][k] - D["bo"][k])):
            continue
        x = exits(D, k, kend, side, e, R)
        if not x:
            continue
        row = dict(mkt=sym, day=pd.Timestamp(d * 86400, unit="s"), side=side, X4=x[3], SAR=np.nan, C=np.nan)
        hit = np.flatnonzero(D["bl"][k:kend] <= stop) if side > 0 else np.flatnonzero(D["ah"][k:kend] >= stop)
        if len(hit):
            ks = k + hit[0]
            s2 = -side
            e2 = (min(stop, D["bo"][ks]) if side > 0 else max(stop, D["ao"][ks]))          # the stop's fill level
            e2 = e2 - (D["ao"][ks] - D["bo"][ks]) if s2 < 0 else e2 + (D["ao"][ks] - D["bo"][ks])  # opposite quote for the new position
            stop2 = Hb if side > 0 else Lb
            R2 = abs(e2 - stop2)
            if ks < kend and R2 > 0 and R2 >= 2 * (D["ao"][ks] - D["bo"][ks]) and s2 * (stop2 - e2) < 0:
                x2 = exits(D, ks, kend, s2, e2, R2)
                if x2:
                    row["SAR"] = x2[3]
                    kc = int(rng.integers(ks, kend)) if kend - ks > 2 else ks
                    sc = 1 if rng.random() < 0.5 else -1
                    ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
                    xc = exits(D, kc, kend, sc, ec, R2) if kc < kend else None
                    row["C"] = xc[3] if xc else np.nan
        rows.append(row)
    df = pd.DataFrame(rows)
    if len(df):
        df["prev_won"] = df.X4.shift(1) > 0
    return df


def main():
    with ProcessPoolExecutor(8) as ex:
        df = pd.concat(list(ex.map(market, SYMS)), ignore_index=True)
    df = df[df.day >= DEV[0]]
    df.to_parquet("D:/finance/si_ledgers/BRK_SAR.parquet")
    def st(g, col, a, b):
        s = g[(g.day >= a) & (g.day <= b)].dropna(subset=[col])
        return len(s), s[col].mean(), nw_t(s.groupby("day")[col].mean().to_numpy())
    base = {p: st(df, "X4", *v) for p, v in (("DEV", DEV), ("VAL", VAL), ("2026", Y26))}
    print("base X4:", {p: f"{v[1]:+.3f}" for p, v in base.items()})
    sar = {p: st(df, "SAR", *v) + (df[(df.day >= v[0]) & (df.day <= v[1])].C.mean(),) for p, v in (("DEV", DEV), ("VAL", VAL), ("2026", Y26))}
    g = [sar["DEV"][1] >= 0.05 and sar["DEV"][2] >= 2.24, sar["VAL"][1] > 0 and sar["VAL"][2] >= 1.65, sar["DEV"][1] - sar["DEV"][3] >= 0.05 and sar["VAL"][1] - sar["VAL"][3] >= 0.05]
    print("SAR second leg: " + " | ".join(f"{p} n{v[0]} {v[1]:+.3f} (t {v[2]:+.2f}) ctl {v[3]:+.3f}" for p, v in sar.items()) + f" | gates {''.join('Y' if z else 'n' for z in g)} PASS {all(g)}")
    stk = df[df.prev_won]
    s2 = {p: st(stk, "X4", *v) for p, v in (("DEV", DEV), ("VAL", VAL), ("2026", Y26))}
    g = [s2["DEV"][1] >= 0.05 and s2["DEV"][2] >= 2.24, s2["VAL"][1] > 0 and s2["VAL"][2] >= 1.65, s2["DEV"][1] - base["DEV"][1] >= 0.05 and s2["VAL"][1] - base["VAL"][1] >= 0.05]
    print("STREAK (yesterday won): " + " | ".join(f"{p} n{v[0]} {v[1]:+.3f} (t {v[2]:+.2f})" for p, v in s2.items()) + f" | gates {''.join('Y' if z else 'n' for z in g)} PASS {all(g)}")
    print("after a losing day:", {p: f"{df[(~df.prev_won) & (df.day >= a) & (df.day <= b)].X4.mean():+.3f}" for p, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26))})


if __name__ == "__main__":
    main()
