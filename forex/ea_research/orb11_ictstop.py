"""ORB11_ICTSTOP (PREREG_ORB11_ICTSTOP.md): ICT-style stops (equilibrium, swing, order block, FVG, structure trail, BE + trail) on the 30-minute ORB.
   python -m forex.ea_research.orb11_ictstop --dry | (run)"""
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.breakouts import local_clock
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS
from forex.ea_research.orb11 import SESS, END, H, M, PER

TPS = (1.0, 2.0, 3.0, np.inf)
RULES = [f"{e} {s} {('none' if np.isinf(tp) else f'{tp:g}R')}" for e in ("TOUCH", "C5") for s in ("BOX", "EQ", "SWING", "OB", "FVG") for tp in TPS] + \
        [f"{e} {s} none" for e in ("TOUCH", "C5") for s in ("TRAIL", "BE+TRAIL")]


def m5(D):
    """server-clock M5 bars from mid prices; per minute its bar position; swing lows/highs with the bar position from which they are known."""
    t = D["t"]; b = t // 300
    st = np.flatnonzero(np.r_[True, b[1:] != b[:-1]]); en = np.r_[st[1:], len(t)]
    mo = (D["bo"] + D["ao"]) / 2
    o, c = mo[st], D["mc"][en - 1]
    h = np.maximum.reduceat(D["mh"], st); l = np.minimum.reduceat(D["ml"], st)
    pos = np.repeat(np.arange(len(st)), en - st)
    n = len(st); swl = np.zeros(n, bool); swh = np.zeros(n, bool)
    j = np.arange(2, n - 2)
    swl[j] = (l[j] < l[j - 1]) & (l[j] < l[j - 2]) & (l[j] < l[j + 1]) & (l[j] < l[j + 2])
    swh[j] = (h[j] > h[j - 1]) & (h[j] > h[j - 2]) & (h[j] > h[j + 1]) & (h[j] > h[j + 2])
    return dict(o=o, c=c, h=h, l=l, pos=pos, st=st, swl=swl, swh=swh)


def struct_stop(B, pk, side, e, kind):
    """initial structure stop known at the start of M5 bar pk (only bars < pk closed; swings need j + 3 <= pk)."""
    if kind == "SWING":
        lo = max(0, pk - 27); j = np.arange(lo, pk - 2)[::-1]
        for jj in j:
            if side > 0 and B["swl"][jj] and B["l"][jj] < e: return B["l"][jj]
            if side < 0 and B["swh"][jj] and B["h"][jj] > e: return B["h"][jj]
        return None
    if kind == "OB":
        for jj in range(pk - 1, max(-1, pk - 13), -1):
            if side > 0 and B["c"][jj] < B["o"][jj]: return B["l"][jj] if B["l"][jj] < e else None
            if side < 0 and B["c"][jj] > B["o"][jj]: return B["h"][jj] if B["h"][jj] > e else None
        return None
    if kind == "FVG":
        for cc in (pk - 1, pk - 2):
            a = cc - 2
            if a < 0: continue
            if side > 0 and B["l"][cc] > B["h"][a] and B["l"][a] < e: return B["l"][a]
            if side < 0 and B["h"][cc] < B["l"][a] and B["h"][a] > e: return B["h"][a]
        return None


def run_exit(D, B, k, kend, side, e, stop0, tps, trail=False, be=False):
    """results in initial-R for the given targets (fixed stop) or the trailing stop (trail / be)."""
    R = side * (e - stop0)
    if side > 0:
        fav, lo, op, end = D["bh"][k:kend] - e, D["bl"][k:kend], D["bo"][k:kend], D["bo"][kend]
    else:
        fav, lo, op, end = e - D["al"][k:kend], D["ah"][k:kend], D["ao"][k:kend], D["ao"][kend]
    n = len(fav); x_end = side * (end - e) / R
    if not trail and not be:
        adv = (e - lo) if side > 0 else (lo - e)
        ca, cf = np.maximum.accumulate(adv), np.maximum.accumulate(fav)
        i_sl = int(np.searchsorted(ca, R))
        loss = (max(R, (e - op[i_sl]) if side > 0 else (op[i_sl] - e)) / R) if i_sl < n else 0.0
        out = []
        for tp in tps:
            i_tp = int(np.searchsorted(cf, tp * R)) if np.isfinite(tp) else n
            out.append(-loss if (i_sl < n and i_sl <= i_tp) else (tp if i_tp < n else x_end))
        return out
    # dynamic stop: per minute stop level (in side-signed price), from swings confirmed after entry
    pm = B["pos"][k:kend]; pk = pm[0]
    stop = np.full(n, stop0, float)
    if be:
        i1 = int(np.searchsorted(np.maximum.accumulate(fav), R))
        if i1 < n - 1:
            stop[i1 + 1:] = e if side > 0 else e
            act = pm[i1 + 1]                                                   # trail starts once at breakeven
        else:
            act = None
    else:
        act = pk
    if act is not None:
        js = np.arange(max(act - 2, 0), pm[-1] - 2)
        sw = (B["swl"][js] if side > 0 else B["swh"][js])
        js = js[sw]
        if len(js):
            lv = B["l"][js] if side > 0 else B["h"][js]
            known = js + 3                                                     # bar position from which each swing is known
            lvl = np.full(pm[-1] - pk + 2, np.nan)
            for kn, v in zip(known, lv):
                ii = kn - pk
                if 0 <= ii < len(lvl): lvl[ii] = v if np.isnan(lvl[ii]) else (max(lvl[ii], v) if side > 0 else min(lvl[ii], v))
            s = pd.Series(lvl).cummax().to_numpy() if side > 0 else pd.Series(lvl).cummin().to_numpy()
            dyn = s[pm - pk]
            ok = np.isfinite(dyn)
            stop[ok] = np.maximum(stop[ok], dyn[ok]) if side > 0 else np.minimum(stop[ok], dyn[ok])
        if be and i1 < n - 1:
            stop[:i1 + 1] = stop0
    hit = np.flatnonzero(lo <= stop) if side > 0 else np.flatnonzero(lo >= stop)
    if len(hit):
        i = hit[0]; px = min(stop[i], op[i]) if side > 0 else max(stop[i], op[i])
        return [side * (px - e) / R]
    return [x_end]


def market(args):
    sym, end = args
    D = load(sym, end); t = D["t"]; B = m5(D); rng = np.random.default_rng(zlib.crc32(sym.encode()) + 11); rows = []
    for sess, (tz, op_s, cl_s) in SESS.items():
        lc = local_clock(t, tz)
        for d in np.unique(lc // 86400):
            base = d * 86400
            i0, i1 = np.searchsorted(lc, base + op_s), np.searchsorted(lc, base + op_s + 30 * M)
            xe = np.searchsorted(lc, base + cl_s)
            if i1 >= len(t) or i1 - i0 < 20 or lc[i0] // 86400 != d or xe <= i1 + 1: continue
            cap = np.searchsorted(t, (t[i1] // 86400) * 86400 + 22 * H + 55 * M); kend = min(xe, cap, len(t) - 1)
            if kend <= i1 + 1: continue
            Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min(); Bw = Hb - Lb
            if not Bw > 0: continue
            day = pd.Timestamp(d * 86400, unit="s")
            entries = []
            up = np.flatnonzero(D["ah"][i1:kend] >= Hb); dn = np.flatnonzero(D["bl"][i1:kend] <= Lb)
            ku, kd = (i1 + up[0] if len(up) else None), (i1 + dn[0] if len(dn) else None)
            if not (ku is None and kd is None) and not (ku is not None and ku == kd):
                side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
                k0 = ku if side > 0 else kd
                entries.append(("TOUCH", side, k0, max(Hb, D["ao"][k0]) if side > 0 else min(Lb, D["bo"][k0])))
            bnd = base + op_s + 30 * M + 5 * M * np.arange(1, 200); bnd = bnd[bnd <= lc[kend - 1]]
            last = np.searchsorted(lc, bnd) - 1; first = np.searchsorted(lc, bnd - 5 * M)
            for a, b in zip(first, last):
                if b < a: continue
                c = D["mc"][b]
                if c > Hb or c < Lb:
                    s_ = 1 if c > Hb else -1; k = b + 1
                    if k < kend - 1: entries.append(("C5", s_, k, D["ao"][k] if s_ > 0 else D["bo"][k]))
                    break
            kc = int(rng.integers(i1, kend - 1)); sc = 1 if rng.random() < 0.5 else -1
            entries.append(("CTRL", sc, kc, D["ao"][kc] if sc > 0 else D["bo"][kc]))
            for name, side, k, e in entries:
                if not k < kend - 1: continue
                spr = D["ao"][k] - D["bo"][k]; pk = B["pos"][k]
                if name == "CTRL":
                    st = {"BOX": e - side * Bw, "EQ": e - side * Bw / 2}
                else:
                    st = {"BOX": Lb if side > 0 else Hb, "EQ": (Hb + Lb) / 2}
                for kind in ("SWING", "OB", "FVG"):
                    s0 = struct_stop(B, pk, side, e, kind)
                    if s0 is None and kind != "FVG": s0 = st["BOX"]
                    st[kind] = s0
                res = {}
                for kind, s0 in st.items():
                    if s0 is None: continue
                    R = side * (e - s0)
                    if not R > 0 or R < 2 * spr: continue
                    for tp, r in zip(TPS, run_exit(D, B, k, kend, side, e, s0, TPS)):
                        res[f"{kind} {('none' if np.isinf(tp) else f'{tp:g}R')}"] = r
                    if kind == "SWING": res["TRAIL none"] = run_exit(D, B, k, kend, side, e, s0, TPS, trail=True)[0]
                    if kind == "BOX": res["BE+TRAIL none"] = run_exit(D, B, k, kend, side, e, s0, TPS, be=True)[0]
                    res[f"R_{kind}"] = R / spr if spr > 0 else np.nan
                rows.append(dict(mkt=sym, sess=sess, day=day, ent=name, side=side, t_entry=int(t[k]), **res))
    return rows


def collect():
    with ProcessPoolExecutor(8) as ex:
        out = [r for rr in ex.map(market, [(s, END) for s in SYMS]) for r in rr]
    return pd.DataFrame(out)


def tstat(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return x.mean() / x.std(ddof=1) * np.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else np.nan


def main():
    pd.set_option("display.width", 250)
    if "--dry" in sys.argv:
        T = pd.DataFrame(market(("EURUSD", END)))
        cols = [c for c in T.columns if c not in ("mkt", "sess", "day", "ent", "side", "t_entry")]
        print(T.groupby(["sess", "ent"]).size().to_string())
        print("share with a result per stop:", T[T.ent == "TOUCH"][[c for c in cols if not c.startswith("R_")]].notna().mean().round(2).to_dict())
        print("median initial stop in spreads:", T[T.ent == "TOUCH"][[c for c in cols if c.startswith("R_")]].median().round(1).to_dict())
        cut = pd.Timestamp("2024-06-01").timestamp(); Tc = pd.DataFrame(market(("EURUSD", cut)))
        sel = lambda X: X[(X.t_entry < cut - 2 * 86400) & (X.ent != "CTRL")].sort_values(["t_entry", "ent"]).reset_index(drop=True)[["t_entry", "ent", "SWING none", "TRAIL none", "BE+TRAIL none", "FVG 2R"]]
        a, b = sel(T), sel(Tc)
        print("truncation:", len(a), len(b), "identical" if a.equals(b) else "DIFFERENT")
        from forex.ea_research.orb11 import market as m11
        O = pd.DataFrame(m11(("EURUSD", END)), columns=["mkt", "sess", "day", "kind", "side", "t_entry", "Rpx", "R11", "R11_opt", "R_hold"])
        print(f"TOUCH BOX 1R {T[T.ent == 'TOUCH']['BOX 1R'].mean():+.4f} vs ORB11 {O[O.kind == 'ORB'].R11.mean():+.4f}")
        return
    T = collect(); T.to_parquet("D:/finance/si_ledgers/ORB11_ICTSTOP.parquet"); T["cls"] = T.mkt.map(mclass)
    rcols = [r.split(" ", 1)[1] for r in RULES if r.startswith("TOUCH")]
    C = T[T.ent == "CTRL"].set_index(["mkt", "sess", "day"])[rcols]
    X = T[T.ent != "CTRL"].reset_index(drop=True)
    Cj = C.reindex(pd.MultiIndex.from_frame(X[["mkt", "sess", "day"]])).reset_index(drop=True)
    pm = {p: ((X.day >= a) & (X.day <= b)).to_numpy() for p, (a, b) in PER.items()}; dv = pm["DEV"] | pm["VAL"]
    print(f"{len(X)} entries ({X.ent.value_counts().to_dict()}), {len(C)} random entries; median initial stop in spreads:",
          X[[c for c in X.columns if c.startswith("R_")]].median().round(1).to_dict())
    out = []
    for ent in ("TOUCH", "C5"):
        for rc in rcols:
            base = (X.ent == ent).to_numpy() & X[rc].notna().to_numpy()
            for key in [(s,) for s in ("LON", "NY")] + [(s, c) for s in ("LON", "NY") for c in X.cls.unique()]:
                m = base & (X.sess == key[0]).to_numpy() & ((X.cls == key[1]).to_numpy() if len(key) > 1 else True)
                if m.sum() < 30: continue
                d = X[m & dv].groupby("day")[rc].mean()
                out.append(dict(pool=" ".join(key), rule=f"{ent} {rc}", n=int(m.sum()), DEV=X.loc[m & pm["DEV"], rc].mean(), VAL=X.loc[m & pm["VAL"], rc].mean(),
                                Y26=X.loc[m & pm["Y26"], rc].mean(), rnd=Cj.loc[m & dv, rc].mean(), win=(X.loc[m, rc] > 0).mean(), t=tstat(d)))
    P = pd.DataFrame(out); P["pass"] = (P.t >= 3.69) & (P.DEV > 0) & (P.VAL > 0) & (P.Y26 > 0) & ((3 * P.DEV + P.VAL) / 4 > P.rnd)
    P.to_csv("D:/finance/si_ledgers/ORB11_ICTSTOP_pools.csv", index=False)
    for s in ("LON", "NY"):
        q = P[P.pool == s].set_index("rule")
        print(f"\n1. {s}, all symbols (R per trade of the INITIAL stop; rnd = random entries, same stop rule, 2022-25):")
        print(q[["n", "DEV", "VAL", "Y26", "rnd", "win", "t"]].round(3).to_string())
    pc = P[P.pool.str.contains(" ")].sort_values("t", ascending=False)
    print(f"\n   pools passing: {int(P['pass'].sum())} of {len(P)}; best 12 session x class pools:")
    print(pc.head(12)[["pool", "rule", "n", "DEV", "VAL", "Y26", "rnd", "t"]].round(3).to_string(index=False))
    rows = []; wf = []
    for (mk, ss), g in X.groupby(["mkt", "sess"]):
        best = None
        for ent in ("TOUCH", "C5"):
            for rc in rcols:
                idx = g.index[(g.ent == ent).to_numpy() & g[rc].notna().to_numpy()]
                if len(idx) < 30: continue
                s = X.loc[idx, rc]; dvi = dv[idx]
                r = dict(mkt=mk, sess=ss, rule=f"{ent} {rc}", n=len(idx), DEV=s[pm["DEV"][idx]].mean(), VAL=s[pm["VAL"][idx]].mean(), Y26=s[pm["Y26"][idx]].mean(),
                         rnd=Cj.loc[idx[dvi], rc].mean(), t=tstat(s[dvi]), t_rnd=tstat(Cj.loc[idx[dvi], rc]))
                rows.append(r)
                if pm["DEV"][idx].sum() >= 50 and (best is None or r["DEV"] > best["DEV"]): best = r
        if best: wf.append(best)
    S = pd.DataFrame(rows); S["pass"] = (S.t >= 4.22) & (S.DEV > 0) & (S.VAL > 0) & (S.Y26 > 0) & (S.DEV > S.rnd)
    S.to_csv("D:/finance/si_ledgers/ORB11_ICTSTOP_cells.csv", index=False); W = pd.DataFrame(wf)
    print(f"\n2. CELLS: {len(S)} tested, passing (t >= 4.22, > 0 DEV/VAL/2026, above random): {int(S['pass'].sum())}")
    print(S.sort_values("t", ascending=False).head(10)[["mkt", "sess", "rule", "n", "DEV", "VAL", "Y26", "rnd", "t"]].round(3).to_string(index=False))
    print(f"   highest t {S.t.max():.2f}; random entries with the same rules: highest {S.t_rnd.max():.2f}")
    print(f"\n3. WALK-FORWARD best of 44 per cell on DEV ({len(W)} cells): DEV {W.DEV.mean():+.3f} -> VAL {W.VAL.mean():+.3f} (positive {int((W.VAL > 0).sum())}), 2026 {W.Y26.mean():+.3f} (positive {int((W.Y26 > 0).sum())}); both {int(((W.VAL > 0) & (W.Y26 > 0)).sum())}")
    print("   rules chosen:", W.rule.str.split(" ").str[1].value_counts().to_dict())


if __name__ == "__main__":
    main()
