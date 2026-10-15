"""ICT3 (PREREG_ICT3.md): Judas / PO3, silver bullet to the draw on liquidity, OTE, breaker, turtle soup, CBDR, with midnight-open and DOL filters.
   python -m forex.ea_research.ict3 --dry | (run)"""
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.breakouts import local_clock
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS
from forex.ea_research.ict_grid import exits, daily_levels, KZ, EXIT_NY, tstat
from forex.ea_research.orb11 import END, H, M, PER
from forex.ea_research.orb11_ictstop import m5

MODELS = {"JUDAS": ("LKZ", "NYAM"), "SBDOL": ("SB",), "OTE": ("LKZ", "NYAM", "SB", "NYPM"), "BREAKER": ("LKZ", "NYAM", "SB", "NYPM"),
          "TURTLE": ("LKZ", "NYAM", "SB", "NYPM"), "CBDR": ("LKZ",)}
FILTS = ["NONE", "MO", "DOL"]
TG = ["1R", "2R", "3R", "LIQ", "TIME"]


def candidates(D, Bm, j0, j1, nb, kend, lv, kz):
    st, o, c, h, l = Bm["st"], Bm["o"], Bm["c"], Bm["h"], Bm["l"]
    out = []; kmax = kend - 1; k_kz = st[j0]

    def limit_fill(side, level, ja, jb):
        if ja >= nb: return None
        a = st[ja]; b = min(st[jb] if jb < nb else len(D["t"]), kmax)
        if b <= a: return None
        w = np.flatnonzero(D["al"][a:b] <= level) if side > 0 else np.flatnonzero(D["bh"][a:b] >= level)
        if not len(w): return None
        k = a + w[0]
        return k, (min(level, D["ao"][k]) if side > 0 else max(level, D["bo"][k]))

    pdl = {1: lv["pdh"], -1: lv["pdl"]}
    # JUDAS
    if kz in MODELS["JUDAS"] and np.isfinite(lv["mo"]):
        km0 = lv["k_mo"]
        for j in range(max(j0, 1), j1):
            if j + 1 >= nb: break
            k = st[j + 1]
            if k >= kmax: break
            for side in (1, -1):
                if side > 0 and c[j] > lv["mo"] >= c[j - 1] and D["bl"][km0:k].min() < lv["mo"]:
                    out.append((k, "JUDAS", side, D["ao"][k], D["bl"][km0:k].min(), pdl[1]))
                if side < 0 and c[j] < lv["mo"] <= c[j - 1] and D["ah"][km0:k].max() > lv["mo"]:
                    out.append((k, "JUDAS", side, D["bo"][k], D["ah"][km0:k].max(), pdl[-1]))
    # SBDOL
    if kz == "SB":
        p10 = (D["bo"][k_kz] + D["ao"][k_kz]) / 2
        dside = 1 if (lv["pdh"] - p10) < (p10 - lv["pdl"]) else -1
        for cc in range(max(j0 + 2, 2), j1):
            if cc + 1 >= nb: break
            ok = (l[cc] > h[cc - 2]) if dside > 0 else (h[cc] < l[cc - 2])
            if not ok: continue
            stop = D["bl"][st[cc - 2]:st[cc - 1]].min() if dside > 0 else D["ah"][st[cc - 2]:st[cc - 1]].max()
            f = limit_fill(dside, l[cc] if dside > 0 else h[cc], cc + 1, cc + 13)
            if f: out.append((f[0], "SBDOL", dside, f[1], stop, pdl[dside]))
            break
    # sweep + MSS -> OTE and BREAKER; TURTLE
    if kz in MODELS["OTE"]:
        for j in range(j0, j1):
            if j + 1 >= nb: break
            for side in (1, -1):
                swept = False
                for lo_, hi_ in ((lv["pdl"], lv["pdh"]), (lv["asl"], lv["ash"])):
                    if not np.isfinite(lo_): continue
                    if (side > 0 and l[j] < lo_ < c[j]) or (side < 0 and h[j] > hi_ > c[j]): swept = True
                tl, th = lv["l20"], lv["h20"]
                if np.isfinite(tl) and ((side > 0 and l[j] < tl < c[j]) or (side < 0 and h[j] > th > c[j])):
                    k = st[j + 1]
                    if k < kmax:
                        ext = D["bl"][k_kz:k].min() if side > 0 else D["ah"][k_kz:k].max()
                        out.append((k, "TURTLE", side, D["ao"][k] if side > 0 else D["bo"][k], ext, pdl[side]))
                if not swept: continue
                base = max(j - 6, 0)
                if j - base < 2: continue
                ref = h[base:j].max() if side > 0 else l[base:j].min()
                for jm in range(j + 1, min(j + 13, j1)):
                    if jm + 1 >= nb: break
                    if (side > 0 and c[jm] > ref) or (side < 0 and c[jm] < ref):
                        km = st[jm + 1]
                        if km >= kmax: break
                        ext = D["bl"][k_kz:km].min() if side > 0 else D["ah"][k_kz:km].max()
                        leg = h[j:jm + 1].max() if side > 0 else l[j:jm + 1].min()
                        ote = leg - 0.705 * (leg - ext) if side > 0 else leg + 0.705 * (ext - leg)
                        f = limit_fill(side, ote, jm + 1, jm + 13)
                        if f: out.append((f[0], "OTE", side, f[1], ext, pdl[side]))
                        bb = None
                        for jj in range(j - 1, base - 1, -1):
                            if (side > 0 and c[jj] > o[jj]) or (side < 0 and c[jj] < o[jj]): bb = jj; break
                        if bb is not None:
                            f = limit_fill(side, h[bb] if side > 0 else l[bb], jm + 1, jm + 13)
                            if f: out.append((f[0], "BREAKER", side, f[1], ext, pdl[side]))
                        break
    # CBDR
    if kz == "LKZ" and np.isfinite(lv["cbh"]):
        W = lv["cbh"] - lv["cbl"]; mid = (lv["cbh"] + lv["cbl"]) / 2
        if W > 0:
            for side, lvl, stp in ((1, lv["cbl"] - 2 * W, lv["cbl"] - 3 * W), (-1, lv["cbh"] + 2 * W, lv["cbh"] + 3 * W)):
                f = limit_fill(side, lvl, j0, j1)
                if f: out.append((f[0], "CBDR", side, f[1], stp, mid))
    return out


def market(args):
    sym, end = args
    D = load(sym, end); t = D["t"]; Bm = m5(D); nb = len(Bm["st"])
    rng = np.random.default_rng(zlib.crc32(sym.encode()) + 31)
    lcny = local_clock(t, "America/New_York"); bny = lcny[Bm["st"]]
    ud, do, dh, dl, dc = daily_levels(D)
    bsec, bday = bny % 86400, bny // 86400
    am = bsec >= 19 * H
    asia = pd.DataFrame({"d": bday[am], "h": Bm["h"][am], "l": Bm["l"][am]}).groupby("d").agg(h=("h", "max"), l=("l", "min"), n=("h", "size"))
    asia = asia[asia.n >= 30]
    cm = (bsec >= 14 * H) & (bsec < 20 * H)
    cb = pd.DataFrame({"d": bday[cm], "h": Bm["h"][cm], "l": Bm["l"][cm]}).groupby("d").agg(h=("h", "max"), l=("l", "min"), n=("h", "size"))
    cb = cb[cb.n >= 60]
    mid = (D["bo"] + D["ao"]) / 2
    rows = []
    for D_ny in np.unique(bday):
        k_mo = int(np.searchsorted(lcny, D_ny * 86400))
        mo = mid[k_mo] if k_mo < len(t) and lcny[k_mo] // 86400 == D_ny else np.nan
        for kz, (a, b) in KZ.items():
            j0, j1 = int(np.searchsorted(bny, D_ny * 86400 + a)), int(np.searchsorted(bny, D_ny * 86400 + b))
            if j1 - j0 < 6 or j1 >= nb: continue
            k0 = Bm["st"][j0]; sday = t[k0] // 86400
            kend = min(int(np.searchsorted(lcny, D_ny * 86400 + EXIT_NY)), int(np.searchsorted(t, sday * 86400 + 22 * H + 55 * M)), len(t) - 1)
            if kend <= Bm["st"][j1 - 1]: continue
            p = int(np.searchsorted(ud, sday)) - 1
            if p < 19: continue
            lv = dict(pdh=dh[p], pdl=dl[p], mo=mo, k_mo=k_mo, h20=dh[p - 19:p + 1].max(), l20=dl[p - 19:p + 1].min(),
                      ash=asia.h.get(D_ny - 1, np.nan), asl=asia.l.get(D_ny - 1, np.nan), cbh=cb.h.get(D_ny - 1, np.nan), cbl=cb.l.get(D_ny - 1, np.nan))
            cands = sorted(candidates(D, Bm, j0, j1, nb, kend, lv, kz), key=lambda x: x[0])
            day = pd.Timestamp(sday * 86400, unit="s"); cache = {}
            for mdl, kzs in MODELS.items():
                if kz not in kzs: continue
                cmod = [x for x in cands if x[1] == mdl]
                for flt in FILTS:
                    for x in cmod:
                        k, _, side, e, stop, liq = x
                        if flt == "MO" and not (np.isfinite(mo) and ((side > 0 and e < mo) or (side < 0 and e > mo))): continue
                        if flt == "DOL" and not ((side > 0) == ((lv["pdh"] - e) < (e - lv["pdl"]))): continue
                        spr = D["ao"][k] - D["bo"][k]; R = side * (e - stop)
                        if not (R > 0 and R >= 2 * spr and k < kend - 1): continue
                        if x not in cache:
                            lm = side * (liq - e) / R if np.isfinite(liq) else np.nan
                            lm = lm if lm >= 0.5 else np.nan
                            r = exits(D, k, kend, side, e, R, lm)
                            kc = int(rng.integers(k0, min(Bm["st"][j1], kend - 1))); sc = 1 if rng.random() < 0.5 else -1
                            cr = exits(D, kc, kend, sc, D["ao"][kc] if sc > 0 else D["bo"][kc], R, lm)
                            cache[x] = (r, cr, R / spr if spr > 0 else np.nan)
                        r, cr, rs = cache[x]
                        rows.append((sym, kz, day, mdl, flt, side, int(t[k]), rs, *r, *cr))
                        break
    return rows


COLS = ["mkt", "kz", "day", "model", "filt", "side", "t_entry", "Rsp"] + [f"r_{g}" for g in TG] + [f"c_{g}" for g in TG]


def collect():
    with ProcessPoolExecutor(8) as ex:
        out = [r for rr in ex.map(market, [(s, END) for s in SYMS]) for r in rr]
    return pd.DataFrame(out, columns=COLS)


def main():
    pd.set_option("display.width", 250)
    if "--dry" in sys.argv:
        T = pd.DataFrame(market(("EURUSD", END)), columns=COLS)
        print(T[T.filt == "NONE"].groupby(["model", "kz"]).size().unstack().to_string())
        print("median stop in spreads:", T[T.filt == "NONE"].groupby("model").Rsp.median().round(1).to_dict(), "| LIQ available", round(T.r_LIQ.notna().mean(), 2))
        x = T[T.model == "JUDAS"].head(2); print(x[COLS[:8]].to_string())
        cut = pd.Timestamp("2024-06-01").timestamp(); Tc = pd.DataFrame(market(("EURUSD", cut)), columns=COLS)
        sel = lambda X: X[X.t_entry < cut - 2 * 86400].sort_values(["t_entry", "model", "filt", "kz"]).reset_index(drop=True)[["t_entry", "model", "filt", "kz", "r_2R", "r_TIME"]]
        a, b = sel(T), sel(Tc)
        print("truncation:", len(a), len(b), "identical" if a.equals(b) else "DIFFERENT")
        return
    T = collect(); T.to_parquet("D:/finance/si_ledgers/ICT3.parquet"); T["cls"] = T.mkt.map(mclass)
    L = pd.concat([T[["mkt", "cls", "kz", "day", "model", "filt", f"r_{g}", f"c_{g}"]].rename(columns={f"r_{g}": "r", f"c_{g}": "c"}).assign(tg=g) for g in TG], ignore_index=True)
    L = L[L.r.notna()].reset_index(drop=True)
    L["per"] = np.select([((L.day >= a) & (L.day <= b)).to_numpy() for a, b in PER.values()], list(PER.keys()), "PRE")
    L["rule"] = L.model + " " + L.kz + " " + L.filt + " " + L.tg
    dvL = L[L.per.isin(["DEV", "VAL"])]
    print(f"{len(T)} rule-trades; by model (filter NONE): {T[T.filt == 'NONE'].model.value_counts().to_dict()}")
    print("\n0. All symbols, 2022-25, R per trade (rows model, columns target):\n" + dvL.groupby(["model", "tg"]).r.mean().unstack()[TG].round(3).to_string()
          + "\n   matched random null:\n" + dvL.groupby(["model", "tg"]).c.mean().unstack()[TG].round(3).to_string())
    print("   by filter:", dvL.groupby("filt").r.mean().round(3).to_dict(), " by killzone:", dvL.groupby("kz").r.mean().round(3).to_dict())
    print("   by year:", L.groupby(L.day.dt.year).r.mean().round(3).to_dict(), " null:", L.groupby(L.day.dt.year).c.mean().round(3).to_dict())
    g = L.groupby(["mkt", "rule", "per"]).agg(m=("r", "mean"), n=("r", "size")).unstack("per")
    tt = dvL.groupby(["mkt", "rule"]).agg(t=("r", tstat), t_rnd=("c", tstat), n_dv=("r", "size"), c_dv=("c", "mean"))
    S = pd.DataFrame({"DEV": g["m"]["DEV"], "VAL": g["m"]["VAL"], "Y26": g["m"].get("Y26"), "nDEV": g["n"]["DEV"]}).join(tt).reset_index()
    S = S[S.n_dv >= 30]
    S["pass"] = (S.t >= 4.67) & (S.DEV > 0) & (S.VAL > 0) & (S.Y26 > 0) & ((3 * S.DEV + S.VAL) / 4 > S.c_dv)
    S.to_csv("D:/finance/si_ledgers/ICT3_cells.csv", index=False)
    print(f"\n1. CELLS: {len(S)} with >= 30 trades in 2022-25; passing (t >= 4.67, > 0 DEV/VAL/2026, above null): {int(S['pass'].sum())}")
    print(S.sort_values("t", ascending=False).head(15)[["mkt", "rule", "n_dv", "DEV", "VAL", "Y26", "c_dv", "t"]].round(3).to_string(index=False))
    print(f"   highest t {S.t.max():.2f}; matched null highest {S.t_rnd.max():.2f}; 99th pct real {np.nanpercentile(S.t, 99):.2f} vs null {np.nanpercentile(S.t_rnd, 99):.2f}; positive in all 3 periods {int(((S.DEV > 0) & (S.VAL > 0) & (S.Y26 > 0)).sum())}")
    rows = []
    for (cl, rule), q in L.groupby(["cls", "rule"]):
        qd = q[q.per.isin(["DEV", "VAL"])]
        if len(qd) < 50: continue
        rows.append(dict(cls=cl, rule=rule, n=len(qd), DEV=q[q.per == "DEV"].r.mean(), VAL=q[q.per == "VAL"].r.mean(), Y26=q[q.per == "Y26"].r.mean(),
                         null=qd.c.mean(), t=tstat(qd.groupby("day").r.mean()), t_null=tstat(qd.groupby("day").c.mean())))
    P = pd.DataFrame(rows); P["pass"] = (P.t >= 4.19) & (P.DEV > 0) & (P.VAL > 0) & (P.Y26 > 0) & ((3 * P.DEV + P.VAL) / 4 > P.null)
    P.to_csv("D:/finance/si_ledgers/ICT3_pools.csv", index=False)
    print(f"\n2. POOLS rule x class: {len(P)}; passing: {int(P['pass'].sum())}; highest t {P.t.max():.2f} vs null {P.t_null.max():.2f}")
    print(P.sort_values("t", ascending=False).head(12)[["cls", "rule", "n", "DEV", "VAL", "Y26", "null", "t"]].round(3).to_string(index=False))
    W = S[S.nDEV >= 50].sort_values("DEV", ascending=False).drop_duplicates("mkt")
    print(f"\n3. WALK-FORWARD best of 240 per symbol on DEV ({len(W)}): DEV {W.DEV.mean():+.3f} -> VAL {W.VAL.mean():+.3f} (positive {int((W.VAL > 0).sum())}), 2026 {W.Y26.mean():+.3f} (positive {int((W.Y26 > 0).sum())}); both {int(((W.VAL > 0) & (W.Y26 > 0)).sum())}")
    PW = P[P.n >= 100].sort_values("DEV", ascending=False).drop_duplicates("cls")
    print("   best rule per class on DEV, then VAL / 2026 (out-of-time picks if both > 0):\n" + PW[["cls", "rule", "n", "DEV", "VAL", "Y26", "t"]].round(3).to_string(index=False))
    PW.to_csv("D:/finance/si_ledgers/ICT3_classpicks.csv", index=False)


if __name__ == "__main__":
    main()
