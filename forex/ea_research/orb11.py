"""ORB11 (PREREG_ORB11.md): the trader's 30-minute London / New York opening-range breakout, first touch, stop at the other side, 1:1 target, all MT5 broker symbols.
   python -m forex.ea_research.orb11 --dry | (run)"""
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.brk_exits import exits
from forex.ea_research.breakouts import local_clock
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS

H, M = 3600, 60
END = pd.Timestamp("2026-10-03").timestamp()
SESS = {"LON": ("Europe/London", 8 * H, 17 * H), "NY": ("America/New_York", 9 * H + 30 * M, 15 * H + 55 * M)}
PER = {"DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "Y26": ("2026-01-01", "2026-10-02")}


def market(args):
    sym, end = args
    D = load(sym, end); t = D["t"]; rows = []
    rng = np.random.default_rng(zlib.crc32(sym.encode()))
    for sess, (tz, op_s, cl_s) in SESS.items():
        lc = local_clock(t, tz)
        for d in np.unique(lc // 86400):
            base = d * 86400
            i0, i1 = np.searchsorted(lc, base + op_s), np.searchsorted(lc, base + op_s + 30 * M)
            xe = np.searchsorted(lc, base + cl_s)
            if i1 >= len(t) or i1 - i0 < 20 or lc[i0] // 86400 != d or xe <= i1 + 1:
                continue
            cap = np.searchsorted(t, (t[i1] // 86400) * 86400 + 22 * H + 55 * M)
            kend = min(xe, cap, len(t) - 1)
            if kend <= i1 + 1: continue
            Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
            if not Hb > Lb: continue
            up = np.flatnonzero(D["ah"][i1:kend] >= Hb); dn = np.flatnonzero(D["bl"][i1:kend] <= Lb)
            ku, kd = (i1 + up[0] if len(up) else None), (i1 + dn[0] if len(dn) else None)
            day = pd.Timestamp(d * 86400, unit="s")
            if not (ku is None and kd is None) and not (ku is not None and ku == kd):
                side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
                k = ku if side > 0 else kd
                e = max(Hb, D["ao"][k]) if side > 0 else min(Lb, D["bo"][k])
                R = abs(e - (Lb if side > 0 else Hb))
                if k < kend - 1 and R >= 2 * (D["ao"][k] - D["bo"][k]):
                    pes = exits(D, k, kend, side, e, R); opt = exits(D, k + 1, kend, side, e, R)
                    if pes is not None and opt is not None:
                        rows.append((sym, sess, day, "ORB", side, int(t[k]), R, pes[0], opt[0], pes[3]))
            kc = int(rng.integers(i1, kend - 1)); sc = 1 if rng.random() < 0.5 else -1
            ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
            if Hb - Lb >= 2 * (D["ao"][kc] - D["bo"][kc]):
                x = exits(D, kc, kend, sc, ec, Hb - Lb)
                if x is not None:
                    rows.append((sym, sess, day, "CTRL", sc, int(t[kc]), Hb - Lb, x[0], x[0], x[3]))
    return rows


COLS = ["mkt", "sess", "day", "kind", "side", "t_entry", "Rpx", "R11", "R11_opt", "R_hold"]


def collect():
    with ProcessPoolExecutor(8) as ex:
        out = [r for rr in ex.map(market, [(s, END) for s in SYMS]) for r in rr]
    return pd.DataFrame(out, columns=COLS)


def tstat(x):
    x = x.dropna(); n = len(x)
    return x.mean() / x.std() * np.sqrt(n) if n > 2 and x.std() > 0 else np.nan


def main():
    if "--dry" in sys.argv:
        D = load("EURUSD", END); r = market(("EURUSD", END)); T = pd.DataFrame(r, columns=COLS)
        print(T.groupby(["sess", "kind"]).size().to_string()); print(T[T.kind == "ORB"].head(4).to_string())
        # truncation: rerun with the data cut at 2024-06-01 -> the trades before the cut are identical
        cut = pd.Timestamp("2024-06-01").timestamp(); Tc = pd.DataFrame(market(("EURUSD", cut)), columns=COLS)
        a = T[(T.t_entry < cut - 86400) & (T.kind == "ORB")].reset_index(drop=True); b = Tc[(Tc.t_entry < cut - 86400) & (Tc.kind == "ORB")].reset_index(drop=True)
        print("truncation:", len(a), len(b), "identical" if a[["t_entry", "R11"]].equals(b[["t_entry", "R11"]]) else "DIFFERENT")
        return
    T = collect(); T.to_parquet("D:/finance/si_ledgers/ORB11.parquet")
    T["yr"] = T.day.dt.year
    def per(df, p): a, b = PER[p]; return df[(df.day >= a) & (df.day <= b)]
    o = T[T.kind == "ORB"]; c = T[T.kind == "CTRL"]
    print(f"trades {len(o)}, control {len(c)}; win rate (1:1) {np.mean(o.R11 > 0):.1%}")
    for s in SESS:
        oo, cc = o[o.sess == s], c[c.sess == s]
        line = []
        for p in PER:
            x = per(oo, p); y = per(cc, p)
            line.append(f"{p} {x.R11.mean():+.3f} R (opt {x.R11_opt.mean():+.3f}, ctrl {y.R11.mean():+.3f}, n {len(x)})")
        dv = pd.concat([per(oo, 'DEV'), per(oo, 'VAL')]); daily = dv.groupby('day').R11.mean()
        print(f"POOLED {s}: " + " | ".join(line) + f" | DEV+VAL daily t {tstat(daily):+.2f}")
        print(f"   by year: {oo.groupby('yr').R11.mean().round(3).to_dict()}  win {np.mean(oo.R11 > 0):.1%}")
    rows = []
    for (m, s), g in o.groupby(["mkt", "sess"]):
        r = dict(mkt=m, sess=s, n=len(g))
        for p in PER:
            x = per(g, p); r[p] = x.R11.mean(); r[p + "_opt"] = x.R11_opt.mean()
        dv = pd.concat([per(g, 'DEV'), per(g, 'VAL')]); r["t"] = tstat(dv.R11); r["win"] = np.mean(g.R11 > 0)
        r["pass"] = bool(r["t"] >= 3.06 and r["DEV"] > 0 and r["VAL"] > 0 and r["Y26"] > 0)
        rows.append(r)
    S = pd.DataFrame(rows).sort_values("t", ascending=False); S.to_csv("D:/finance/si_ledgers/ORB11_cells.csv", index=False)
    pd.set_option("display.width", 250)
    print("\nTop 15 cells by DEV+VAL t (bar 3.06; mean > 0 in DEV, VAL, 2026):")
    print(S.head(15)[["mkt", "sess", "n", "DEV", "VAL", "Y26", "t", "win", "pass"]].round(3).to_string(index=False))
    print(f"\ncells positive in all three periods: {int(((S.DEV > 0) & (S.VAL > 0) & (S.Y26 > 0)).sum())} of {len(S)}; passing: {int(S['pass'].sum())}")
    print(f"cells with DEV+VAL mean > 0: {int(((S.DEV + S.VAL) > 0).sum())} of {len(S)}; median cell DEV {S.DEV.median():+.3f} R")


if __name__ == "__main__":
    main()
