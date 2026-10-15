"""ICT_GRID (PREREG_ICT_GRID.md): 8 ICT entry models x 4 killzones x 3 biases x 5 targets on 46 MT5 broker symbols, matched random null.
   python -m forex.ea_research.ict_grid --dry | (run)"""
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.breakouts import local_clock
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS
from forex.ea_research.orb11 import END, H, M, PER
from forex.ea_research.orb11_ictstop import m5

MODELS = ["SWEEP_PD", "SWEEP_AS", "MSS_PD", "MSS_AS", "MSSFVG_PD", "MSSFVG_AS", "FVG", "OB"]
KZ = {"LKZ": (2 * H, 5 * H), "NYAM": (8 * H + 30 * M, 11 * H), "SB": (10 * H, 11 * H), "NYPM": (13 * H + 30 * M, 15 * H + 55 * M)}
BIAS = ["NONE", "DAILY", "PD"]
TG = ["1R", "2R", "3R", "LIQ", "TIME"]
EXIT_NY = 15 * H + 55 * M


def exits(D, k, kend, side, e, R, liq_mult):
    """results in R for targets 1R, 2R, 3R, LIQ (liq_mult x R, NaN if none) and TIME."""
    if side > 0:
        fav, adv, op, end = D["bh"][k:kend] - e, e - D["bl"][k:kend], D["bo"][k:kend], D["bo"][kend]
        gap = lambda i: e - op[i]
    else:
        fav, adv, op, end = e - D["al"][k:kend], D["ah"][k:kend] - e, D["ao"][k:kend], D["ao"][kend]
        gap = lambda i: op[i] - e
    n = len(fav); cf, ca = np.maximum.accumulate(fav), np.maximum.accumulate(adv)
    x_end = side * (end - e) / R
    i_sl = int(np.searchsorted(ca, R)); loss = max(R, gap(i_sl)) / R if i_sl < n else 0.0
    out = []
    for tp in (1.0, 2.0, 3.0, liq_mult, np.inf):
        if np.isnan(tp):
            out.append(np.nan); continue
        i_tp = int(np.searchsorted(cf, tp * R)) if np.isfinite(tp) else n
        out.append(-loss if (i_sl < n and i_sl <= i_tp) else (tp if i_tp < n else x_end))
    return out


def daily_levels(D):
    t = D["t"]; sd, sod = t // 86400, t % 86400
    ok = (sod >= H) & (sod < 22 * H + 55 * M)
    df = pd.DataFrame({"d": sd[ok], "o": ((D["bo"] + D["ao"]) / 2)[ok], "h": D["mh"][ok], "l": D["ml"][ok], "c": D["mc"][ok]})
    g = df.groupby("d").agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"))
    return g.index.to_numpy(), g.o.to_numpy(), g.h.to_numpy(), g.l.to_numpy(), g.c.to_numpy()


def candidates(D, Bm, j0, j1, nb, kend, lv):
    """all signals inside the killzone bars [j0, j1): (k_fill, model, side, e, stop, liq_price)."""
    st, o, c, h, l = Bm["st"], Bm["o"], Bm["c"], Bm["h"], Bm["l"]
    out = []
    kmax = kend - 1
    k_kz = st[j0]

    def limit_fill(side, level, ja, jb):
        """first minute in bars [ja, jb) where a limit at level fills; returns (k, price) or None."""
        if ja >= nb: return None
        a = st[ja]; b = st[min(jb, nb - 1)] if jb < nb else len(D["t"]); b = min(b, kmax)
        if b <= a: return None
        w = np.flatnonzero(D["al"][a:b] <= level) if side > 0 else np.flatnonzero(D["bh"][a:b] >= level)
        if not len(w): return None
        k = a + w[0]
        return k, (min(level, D["ao"][k]) if side > 0 else max(level, D["bo"][k]))

    for lvl in ("PD", "AS"):
        lo_, hi_ = (lv["pdl"], lv["pdh"]) if lvl == "PD" else (lv["asl"], lv["ash"])
        if not (np.isfinite(lo_) and np.isfinite(hi_)): continue
        liq = {1: hi_, -1: lo_}
        for j in range(j0, j1):
            if j + 1 >= nb: break
            for side, swept in ((1, l[j] < lo_ and c[j] > lo_), (-1, h[j] > hi_ and c[j] < hi_)):
                if not swept: continue
                k = st[j + 1]
                if k >= kmax: continue
                ext = D["bl"][k_kz:k].min() if side > 0 else D["ah"][k_kz:k].max()
                out.append((k, f"SWEEP_{lvl}", side, D["ao"][k] if side > 0 else D["bo"][k], ext, liq[side]))
                # MSS within 12 bars
                base = max(j - 6, 0)
                if j - base < 2: continue
                ref = h[base:j].max() if side > 0 else l[base:j].min()
                for jm in range(j + 1, min(j + 13, j1)):
                    if jm + 1 >= nb: break
                    if (side > 0 and c[jm] > ref) or (side < 0 and c[jm] < ref):
                        km = st[jm + 1]
                        if km >= kmax: break
                        ext2 = D["bl"][k_kz:km].min() if side > 0 else D["ah"][k_kz:km].max()
                        out.append((km, f"MSS_{lvl}", side, D["ao"][km] if side > 0 else D["bo"][km], ext2, liq[side]))
                        # latest FVG of the MSS leg
                        fv = None
                        for cc in range(jm, j, -1):
                            if cc - 2 < 0: break
                            if side > 0 and l[cc] > h[cc - 2]: fv = l[cc]; break
                            if side < 0 and h[cc] < l[cc - 2]: fv = h[cc]; break
                        if fv is not None:
                            f = limit_fill(side, fv, jm + 1, jm + 13)
                            if f: out.append((f[0], f"MSSFVG_{lvl}", side, f[1], ext2, liq[side]))
                        break
    # FVG continuation and OB retrace (liquidity target = prior-day extreme)
    liqpd = {1: lv["pdh"], -1: lv["pdl"]}
    for cc in range(max(j0 + 2, 2), j1):
        if cc + 1 >= nb: break
        for side, ok in ((1, l[cc] > h[cc - 2]), (-1, h[cc] < l[cc - 2])):
            if not ok: continue
            stop = D["bl"][st[cc - 2]:st[cc - 1]].min() if side > 0 else D["ah"][st[cc - 2]:st[cc - 1]].max()
            f = limit_fill(side, l[cc] if side > 0 else h[cc], cc + 1, cc + 13)
            if f: out.append((f[0], "FVG", side, f[1], stop, liqpd[side]))
    for j in range(j0, j1):
        if j + 1 >= nb or j < 30: continue
        for side in (1, -1):
            js = np.arange(j - 24, j - 2)
            sw = Bm["swh"][js] if side > 0 else Bm["swl"][js]
            if not sw.any(): continue
            ref = (h if side > 0 else l)[js[sw][-1]]
            if not ((side > 0 and c[j] > ref >= c[j - 1]) or (side < 0 and c[j] < ref <= c[j - 1])): continue
            ob = None
            for jj in range(j - 1, j - 7, -1):
                if (side > 0 and c[jj] < o[jj]) or (side < 0 and c[jj] > o[jj]): ob = jj; break
            if ob is None: continue
            lvl_ = h[ob] if side > 0 else l[ob]
            stop = D["bl"][st[ob]:st[ob + 1]].min() if side > 0 else D["ah"][st[ob]:st[ob + 1]].max()
            f = limit_fill(side, lvl_, j + 1, j + 13)
            if f: out.append((f[0], "OB", side, f[1], stop, liqpd[side]))
    return out


def market(args):
    sym, end = args
    D = load(sym, end); t = D["t"]; Bm = m5(D); nb = len(Bm["st"])
    rng = np.random.default_rng(zlib.crc32(sym.encode()) + 23)
    lcny = local_clock(t, "America/New_York"); bny = lcny[Bm["st"]]
    ud, do, dh, dl, dc = daily_levels(D)
    # Asian range per New York date: bars 19:00-24:00 NY
    bsec, bday = bny % 86400, bny // 86400
    am = bsec >= 19 * H
    asia = pd.DataFrame({"d": bday[am], "h": Bm["h"][am], "l": Bm["l"][am]}).groupby("d").agg(h=("h", "max"), l=("l", "min"), n=("h", "size"))
    asia = asia[asia.n >= 30]
    rows = []
    for D_ny in np.unique(bday):
        for kz, (a, b) in KZ.items():
            j0, j1 = int(np.searchsorted(bny, D_ny * 86400 + a)), int(np.searchsorted(bny, D_ny * 86400 + b))
            if j1 - j0 < 6 or j1 >= nb: continue
            k0 = Bm["st"][j0]; sday = t[k0] // 86400
            kend = min(int(np.searchsorted(lcny, D_ny * 86400 + EXIT_NY)), int(np.searchsorted(t, sday * 86400 + 22 * H + 55 * M)), len(t) - 1)
            if kend <= Bm["st"][j1 - 1]: continue
            p = int(np.searchsorted(ud, sday)) - 1
            if p < 0: continue
            lv = dict(pdh=dh[p], pdl=dl[p], pdm=(dh[p] + dl[p]) / 2, pdir=int(np.sign(dc[p] - do[p])),
                      ash=asia.h.get(D_ny - 1, np.nan), asl=asia.l.get(D_ny - 1, np.nan))
            cands = sorted(candidates(D, Bm, j0, j1, nb, kend, lv), key=lambda x: x[0])
            day = pd.Timestamp(sday * 86400, unit="s"); cache = {}
            for mdl in MODELS:
                cm = [x for x in cands if x[1] == mdl]
                for bias in BIAS:
                    for x in cm:
                        k, _, side, e, stop, liq = x
                        if bias == "DAILY" and side != lv["pdir"]: continue
                        if bias == "PD" and not ((side > 0 and e < lv["pdm"]) or (side < 0 and e > lv["pdm"])): continue
                        spr = D["ao"][k] - D["bo"][k]; R = side * (e - stop)
                        if not (R > 0 and R >= 2 * spr and k < kend - 1): continue
                        if x not in cache:
                            lm = side * (liq - e) / R if np.isfinite(liq) else np.nan
                            lm = lm if lm >= 0.5 else np.nan
                            r = exits(D, k, kend, side, e, R, lm)
                            kc = int(rng.integers(k0, min(Bm["st"][j1], kend - 1))); sc = 1 if rng.random() < 0.5 else -1
                            ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
                            cr = exits(D, kc, kend, sc, ec, R, lm)
                            cache[x] = (r, cr, R / spr if spr > 0 else np.nan)
                        r, cr, rs = cache[x]
                        rows.append((sym, kz, day, mdl, bias, side, int(t[k]), rs, *r, *cr))
                        break
    return rows


COLS = ["mkt", "kz", "day", "model", "bias", "side", "t_entry", "Rsp"] + [f"r_{g}" for g in TG] + [f"c_{g}" for g in TG]


def collect():
    with ProcessPoolExecutor(8) as ex:
        out = [r for rr in ex.map(market, [(s, END) for s in SYMS]) for r in rr]
    return pd.DataFrame(out, columns=COLS)


def tstat(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return x.mean() / x.std(ddof=1) * np.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else np.nan


def main():
    pd.set_option("display.width", 250)
    if "--dry" in sys.argv:
        T = pd.DataFrame(market(("EURUSD", END)), columns=COLS)
        print(T[T.bias == "NONE"].groupby(["model", "kz"]).size().unstack().to_string())
        print("median stop in spreads by model:", T[T.bias == "NONE"].groupby("model").Rsp.median().round(1).to_dict())
        print("LIQ target available:", T.r_LIQ.notna().mean().round(2))
        print(T.head(5)[COLS[:8]].to_string())
        cut = pd.Timestamp("2024-06-01").timestamp(); Tc = pd.DataFrame(market(("EURUSD", cut)), columns=COLS)
        sel = lambda X: X[X.t_entry < cut - 2 * 86400].sort_values(["t_entry", "model", "bias", "kz"]).reset_index(drop=True)[["t_entry", "model", "bias", "kz", "r_2R", "r_TIME"]]
        a, b = sel(T), sel(Tc)
        print("truncation:", len(a), len(b), "identical" if a.equals(b) else "DIFFERENT")
        return
    T = collect(); T.to_parquet("D:/finance/si_ledgers/ICT_GRID.parquet"); T["cls"] = T.mkt.map(mclass)
    pm = {p: ((T.day >= a) & (T.day <= b)).to_numpy() for p, (a, b) in PER.items()}; dv = pm["DEV"] | pm["VAL"]
    print(f"{len(T)} rule-trades; by model (bias NONE): {T[T.bias == 'NONE'].model.value_counts().to_dict()}")
    # long format: one row per (trade, target)
    L = []
    for g in TG:
        L.append(T[["mkt", "cls", "kz", "day", "model", "bias", f"r_{g}", f"c_{g}"]].rename(columns={f"r_{g}": "r", f"c_{g}": "c"}).assign(tg=g))
    L = pd.concat(L, ignore_index=True); L = L[L.r.notna()].reset_index(drop=True)
    L["per"] = np.select([pm2 for pm2 in [((L.day >= a) & (L.day <= b)).to_numpy() for a, b in PER.values()]], list(PER.keys()), "PRE")
    L["rule"] = L.model + " " + L.kz + " " + L.bias + " " + L.tg
    # 0. overview by model x target, all symbols
    ov = L[L.per.isin(["DEV", "VAL"])].groupby(["model", "tg"]).r.mean().unstack().reindex(index=MODELS, columns=TG)
    ovc = L[L.per.isin(["DEV", "VAL"])].groupby(["model", "tg"]).c.mean().unstack().reindex(index=MODELS, columns=TG)
    print("\n0. All symbols, killzones and biases pooled, 2022-25, R per trade (rows model, columns target):\n" + ov.round(3).to_string() + "\n   matched random null:\n" + ovc.round(3).to_string())
    print("   by killzone (2022-25):", L[L.per.isin(["DEV", "VAL"])].groupby("kz").r.mean().round(3).to_dict(), " by bias:", L[L.per.isin(["DEV", "VAL"])].groupby("bias").r.mean().round(3).to_dict())
    print("   by year:", L.groupby(L.day.dt.year).r.mean().round(3).to_dict(), " null:", L.groupby(L.day.dt.year).c.mean().round(3).to_dict())
    # 1. cells
    g = L.groupby(["mkt", "rule", "per"]).agg(m=("r", "mean"), n=("r", "size"), cm=("c", "mean")).unstack("per")
    dvL = L[L.per.isin(["DEV", "VAL"])]
    tt = dvL.groupby(["mkt", "rule"]).agg(t=("r", tstat), t_rnd=("c", tstat), n_dv=("r", "size"), c_dv=("c", "mean"))
    S = pd.DataFrame({"DEV": g["m"]["DEV"], "VAL": g["m"]["VAL"], "Y26": g["m"].get("Y26"), "nDEV": g["n"]["DEV"]}).join(tt).reset_index()
    S = S[S.n_dv >= 30]
    S["pass"] = (S.t >= 4.59) & (S.DEV > 0) & (S.VAL > 0) & (S.Y26 > 0) & ((3 * S.DEV + S.VAL) / 4 > S.c_dv)
    S.to_csv("D:/finance/si_ledgers/ICT_GRID_cells.csv", index=False)
    print(f"\n1. CELLS: {len(S)} with >= 30 trades in 2022-25; passing (t >= 4.59, > 0 DEV/VAL/2026, above null): {int(S['pass'].sum())}")
    print(S.sort_values("t", ascending=False).head(15)[["mkt", "rule", "n_dv", "DEV", "VAL", "Y26", "c_dv", "t"]].round(3).to_string(index=False))
    print(f"   highest t {S.t.max():.2f}; the same search on the matched null: highest {S.t_rnd.max():.2f}; 99th pct real {np.nanpercentile(S.t, 99):.2f} vs null {np.nanpercentile(S.t_rnd, 99):.2f}")
    print(f"   cells positive in DEV, VAL and 2026: {int(((S.DEV > 0) & (S.VAL > 0) & (S.Y26 > 0)).sum())} of {len(S)}")
    # 2. pools rule x class (daily mean)
    rows = []
    for (cl, rule), q in L.groupby(["cls", "rule"]):
        qd = q[q.per.isin(["DEV", "VAL"])]
        if len(qd) < 50: continue
        d = qd.groupby("day").r.mean()
        rows.append(dict(cls=cl, rule=rule, n=len(qd), DEV=q[q.per == "DEV"].r.mean(), VAL=q[q.per == "VAL"].r.mean(), Y26=q[q.per == "Y26"].r.mean(), null=qd.c.mean(), t=tstat(d), t_null=tstat(qd.groupby("day").c.mean())))
    P = pd.DataFrame(rows); P["pass"] = (P.t >= 4.07) & (P.DEV > 0) & (P.VAL > 0) & (P.Y26 > 0) & ((3 * P.DEV + P.VAL) / 4 > P.null)
    P.to_csv("D:/finance/si_ledgers/ICT_GRID_pools.csv", index=False)
    print(f"\n2. POOLS rule x class: {len(P)}; passing (t >= 4.07 ...): {int(P['pass'].sum())}; highest t {P.t.max():.2f} vs null {P.t_null.max():.2f}")
    print(P.sort_values("t", ascending=False).head(12)[["cls", "rule", "n", "DEV", "VAL", "Y26", "null", "t"]].round(3).to_string(index=False))
    # 3. walk-forward per symbol and per class
    W = S[S.nDEV >= 50].sort_values("DEV", ascending=False).drop_duplicates("mkt")
    print(f"\n3. WALK-FORWARD best of 480 per symbol on DEV ({len(W)}): DEV {W.DEV.mean():+.3f} -> VAL {W.VAL.mean():+.3f} (positive {int((W.VAL > 0).sum())}), 2026 {W.Y26.mean():+.3f} (positive {int((W.Y26 > 0).sum())}); both {int(((W.VAL > 0) & (W.Y26 > 0)).sum())}")
    print("   models chosen:", W.rule.str.split(" ").str[0].value_counts().to_dict())
    PW = P[P.n >= 100].sort_values("DEV", ascending=False).drop_duplicates("cls")
    print("   best rule per class on DEV (pool), then VAL / 2026 (out-of-time picks if both > 0):\n" + PW[["cls", "rule", "n", "DEV", "VAL", "Y26", "t"]].round(3).to_string(index=False))
    PW.to_csv("D:/finance/si_ledgers/ICT_GRID_classpicks.csv", index=False)


if __name__ == "__main__":
    main()
