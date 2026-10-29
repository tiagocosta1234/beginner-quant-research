"""ORB11_ENTRY (PREREG_ORB11_ENTRY.md): 6 entry triggers x 6 filters x 2 exits on the trader's 30-minute London / NY box, 46 MT5 broker symbols, with a random-entry null.
   python -m forex.ea_research.orb11_entry --dry | (run)"""
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

TRIGS = ["TOUCH", "C5", "C15", "HOLD15", "RETEST", "FADE"]
FILTS = ["F0", "TREND", "WIDE", "SQUEEZE", "BOXDIR", "TREND+WIDE"]
COLS = ["mkt", "sess", "day", "trig", "side", "t_entry", "Hb", "Lb", "e", "R", "Rsp", "r1", "rh", "tr", "wide", "sq", "bd"]


def ex2(D, k, kend, side, e, R):
    """(1:1 result, hold-to-close result) in R for a position filled at minute k at price e with stop distance R."""
    if side > 0:
        fav, adv, op, end = D["bh"][k:kend] - e, e - D["bl"][k:kend], D["bo"][k:kend], D["bo"][kend]
        gap = lambda i: e - op[i]
    else:
        fav, adv, op, end = e - D["al"][k:kend], D["ah"][k:kend] - e, D["ao"][k:kend], D["ao"][kend]
        gap = lambda i: op[i] - e
    n = len(fav); cf, ca = np.maximum.accumulate(fav), np.maximum.accumulate(adv)
    x_end = side * (end - e)
    i_sl = int(np.searchsorted(ca, R)); i_tp = int(np.searchsorted(cf, R))
    loss = max(R, gap(i_sl)) / R if i_sl < n else None
    r1 = -loss if (i_sl < n and i_sl <= i_tp) else (1.0 if i_tp < n else x_end / R)
    rh = -loss if i_sl < n else x_end / R
    return r1, rh


def daily(D):
    """per server day: mid close before 22:55, mid range 01:00-22:55, 20-day SMA of closes, ATR20 of ranges."""
    t = D["t"]; sd, sod = t // 86400, t % 86400
    ok = (sod >= H) & (sod < 22 * H + 55 * M)
    df = pd.DataFrame({"d": sd[ok], "c": D["mc"][ok], "h": D["mh"][ok], "l": D["ml"][ok]})
    g = df.groupby("d").agg(c=("c", "last"), h=("h", "max"), l=("l", "min"))
    g["sma"] = g.c.rolling(20).mean(); g["atr"] = (g.h - g.l).rolling(20).mean()
    return g.index.to_numpy(), g.c.to_numpy(), g.sma.to_numpy(), g.atr.to_numpy()


def market(args):
    sym, end = args
    D = load(sym, end); t = D["t"]; rng = np.random.default_rng(zlib.crc32(sym.encode()) + 7)
    ud, dc, dsma, datr = daily(D); rows = []
    mid_o = (D["bo"] + D["ao"]) / 2
    for sess, (tz, op_s, cl_s) in SESS.items():
        lc = local_clock(t, tz); past = []
        for d in np.unique(lc // 86400):
            base = d * 86400
            i0, i1 = np.searchsorted(lc, base + op_s), np.searchsorted(lc, base + op_s + 30 * M)
            xe = np.searchsorted(lc, base + cl_s)
            if i1 >= len(t) or i1 - i0 < 20 or lc[i0] // 86400 != d or xe <= i1 + 1: continue
            cap = np.searchsorted(t, (t[i1] // 86400) * 86400 + 22 * H + 55 * M); kend = min(xe, cap, len(t) - 1)
            if kend <= i1 + 1: continue
            Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min(); B = Hb - Lb
            if not B > 0: continue
            day = pd.Timestamp(d * 86400, unit="s")
            # filters known at the box close, from earlier data only
            p = int(np.searchsorted(ud, t[i0] // 86400)) - 1
            trend = int(np.sign(dc[p] - dsma[p])) if p >= 0 and np.isfinite(dsma[p]) else 0
            spr = float(np.median(D["ao"][i0:i1] - D["bo"][i0:i1])); wide = bool(B >= 40 * spr)
            ratio = B / datr[p] if p >= 0 and np.isfinite(datr[p]) and datr[p] > 0 else np.nan
            hist = [x for x in past[-60:] if np.isfinite(x)]
            sq = bool(len(hist) >= 20 and np.isfinite(ratio) and ratio <= np.quantile(hist, 1 / 3))
            past.append(ratio)
            bdir = int(np.sign(D["mc"][i1 - 1] - mid_o[i0]))

            def add(trig, side, k, e, R):
                if not (k < kend - 1 and R > 0): return
                s = D["ao"][k] - D["bo"][k]
                if R < 2 * s: return
                r1, rh = ex2(D, k, kend, side, e, R)
                rows.append((sym, sess, day, trig, side, int(t[k]), Hb, Lb, e, R, R / s if s > 0 else np.nan, r1, rh,
                             side == trend, wide, sq, side == bdir))

            up = np.flatnonzero(D["ah"][i1:kend] >= Hb); dn = np.flatnonzero(D["bl"][i1:kend] <= Lb)
            ku, kd = (i1 + up[0] if len(up) else None), (i1 + dn[0] if len(dn) else None)
            if not (ku is None and kd is None) and not (ku is not None and ku == kd):
                side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
                k0 = ku if side > 0 else kd; edge, opp = (Hb, Lb) if side > 0 else (Lb, Hb)
                # T1 TOUCH
                e = max(Hb, D["ao"][k0]) if side > 0 else min(Lb, D["bo"][k0])
                add("TOUCH", side, k0, e, side * (e - opp))
                # T4 HOLD15
                j = int(np.searchsorted(lc, lc[k0] + 15 * M))
                if j < kend - 1 and side * (D["mc"][j - 1] - edge) > 0:
                    e = D["ao"][j] if side > 0 else D["bo"][j]; add("HOLD15", side, j, e, side * (e - opp))
                # T5 RETEST: limit at the edge for 60 minutes after the touch minute
                jl = min(kend - 1, int(np.searchsorted(lc, lc[k0] + 60 * M)))
                w = np.flatnonzero(D["al"][k0 + 1:jl] <= Hb) if side > 0 else np.flatnonzero(D["bh"][k0 + 1:jl] >= Lb)
                if len(w):
                    j = k0 + 1 + w[0]; e = min(Hb, D["ao"][j]) if side > 0 else max(Lb, D["bo"][j])
                    add("RETEST", side, j, e, side * (e - opp))
                # T6 FADE: first mid close back inside -> other way at the next open, stop at the breakout extreme
                back = np.flatnonzero(D["mc"][k0:kend - 1] < Hb) if side > 0 else np.flatnonzero(D["mc"][k0:kend - 1] > Lb)
                if len(back):
                    j = k0 + back[0]; k = j + 1
                    if side > 0:
                        ext = D["ah"][k0:j + 1].max(); e = D["bo"][k]; add("FADE", -1, k, e, ext - e)
                    else:
                        ext = D["bl"][k0:j + 1].min(); e = D["ao"][k]; add("FADE", 1, k, e, e - ext)
            # T2 / T3: first 5- / 15-minute mid close outside the box
            for trig, wmin in (("C5", 5), ("C15", 15)):
                bnd = base + op_s + 30 * M + wmin * M * np.arange(1, 200)
                bnd = bnd[bnd <= lc[kend - 1]]
                last = np.searchsorted(lc, bnd) - 1; first = np.searchsorted(lc, bnd - wmin * M)
                for a, b in zip(first, last):
                    if b < a: continue
                    c = D["mc"][b]
                    if c > Hb or c < Lb:
                        side = 1 if c > Hb else -1; k = b + 1
                        if k < kend - 1:
                            e = D["ao"][k] if side > 0 else D["bo"][k]; add(trig, side, k, e, side * (e - (Lb if side > 0 else Hb)))
                        break
            # random-entry null: random minute after the box, random side, stop = box width
            kc = int(rng.integers(i1, kend - 1)); sc = 1 if rng.random() < 0.5 else -1
            add("CTRL", sc, kc, D["ao"][kc] if sc > 0 else D["bo"][kc], B)
    return rows


def collect():
    with ProcessPoolExecutor(8) as ex:
        out = [r for rr in ex.map(market, [(s, END) for s in SYMS]) for r in rr]
    return pd.DataFrame(out, columns=COLS)


def fmask(T, f):
    return {"F0": np.ones(len(T), bool), "TREND": T.tr.to_numpy(), "WIDE": T.wide.to_numpy(), "SQUEEZE": T.sq.to_numpy(),
            "BOXDIR": T.bd.to_numpy(), "TREND+WIDE": (T.tr & T.wide).to_numpy()}[f]


def tstat(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]; n = len(x)
    return x.mean() / x.std(ddof=1) * np.sqrt(n) if n > 2 and x.std() > 0 else np.nan


def main():
    pd.set_option("display.width", 250)
    if "--dry" in sys.argv:
        T = pd.DataFrame(market(("EURUSD", END)), columns=COLS)
        print(T.groupby(["sess", "trig"]).size().unstack().to_string())
        print("filter shares:", T[T.trig == "TOUCH"][["tr", "wide", "sq", "bd"]].mean().round(3).to_dict())
        print(T[T.trig.isin(["C5", "FADE", "RETEST"])].head(6)[COLS[:11]].to_string())
        cut = pd.Timestamp("2024-06-01").timestamp(); Tc = pd.DataFrame(market(("EURUSD", cut)), columns=COLS)
        sel = lambda X: X[(X.t_entry < cut - 2 * 86400) & (X.trig != "CTRL")].sort_values(["t_entry", "trig"]).reset_index(drop=True)
        a, b = sel(T), sel(Tc)
        same = len(a) == len(b) and a[["t_entry", "trig", "r1", "tr", "sq"]].equals(b[["t_entry", "trig", "r1", "tr", "sq"]])
        print("truncation:", len(a), len(b), "identical" if same else "DIFFERENT")
        # baseline reproduces ORB11 on EURUSD
        from forex.ea_research.orb11 import market as m11
        O = pd.DataFrame(m11(("EURUSD", END)), columns=["mkt", "sess", "day", "kind", "side", "t_entry", "Rpx", "R11", "R11_opt", "R_hold"])
        print(f"TOUCH 1:1 {T[T.trig == 'TOUCH'].r1.mean():+.4f} vs ORB11 {O[O.kind == 'ORB'].R11.mean():+.4f} (n {int((T.trig == 'TOUCH').sum())} vs {int((O.kind == 'ORB').sum())})")
        return
    T = collect(); T.to_parquet("data/si_ledgers/ORB11_ENTRY.parquet")
    T["cls"] = T.mkt.map(mclass)
    C = T[T.trig == "CTRL"].set_index(["mkt", "sess", "day"])[["r1", "rh"]].rename(columns={"r1": "c1", "rh": "ch"})
    X = T[T.trig != "CTRL"].join(C, on=["mkt", "sess", "day"]).reset_index(drop=True)
    pm = {p: ((X.day >= a) & (X.day <= b)).to_numpy() for p, (a, b) in PER.items()}
    dv = pm["DEV"] | pm["VAL"]
    print(f"{len(X)} rule trades, {len(C)} random entries; 1:1 win rate by trigger: {X.groupby('trig').r1.apply(lambda s: (s > 0).mean()).round(3).to_dict()}")
    rules = [(tg, f, x) for tg in TRIGS for f in FILTS for x in ("r1", "rh")]
    # 1. pooled tables
    out = []
    for tg, f, x in rules:
        cx = "c1" if x == "r1" else "ch"
        base = (X.trig == tg).to_numpy() & fmask(X, f)
        for grp in ("sess", "cls"):
            for key in (X.sess.unique() if grp == "sess" else [(s, c) for s in X.sess.unique() for c in X.cls.unique()]):
                m = base & ((X.sess == key).to_numpy() if grp == "sess" else ((X.sess == key[0]) & (X.cls == key[1])).to_numpy())
                if m.sum() < 30: continue
                d = X[m & dv].groupby("day")[x].mean(); dc = X[m & dv].groupby("day")[cx].mean()
                out.append(dict(pool=str(key), trig=tg, filt=f, exit="1:1" if x == "r1" else "hold", n=int(m.sum()),
                                DEV=X[m & pm["DEV"]][x].mean(), VAL=X[m & pm["VAL"]][x].mean(), Y26=X[m & pm["Y26"]][x].mean(),
                                rnd=X[m & dv][cx].mean(), t=tstat(d), t_rnd=tstat(dc)))
    P = pd.DataFrame(out)
    P["pass"] = (P.t >= 3.81) & (P.DEV > 0) & (P.VAL > 0) & (P.Y26 > 0) & ((P.DEV * 3 + P.VAL) / 4 > P.rnd)
    P.to_csv("data/si_ledgers/ORB11_ENTRY_pools.csv", index=False)
    for s in ("LON", "NY"):
        q = P[P.pool == s]
        for x in ("1:1", "hold"):
            tab = q[q.exit == x].pivot(index="trig", columns="filt", values="DEV").reindex(index=TRIGS, columns=FILTS)
            print(f"\n1. {s}, exit {x}, all symbols, DEV 2022-24 R per trade (rows trigger, columns filter):\n" + tab.round(3).to_string())
        q = q.sort_values("t", ascending=False)
        print(f"   {s} best 6 by DEV+VAL daily t:\n" + q.head(6)[["trig", "filt", "exit", "n", "DEV", "VAL", "Y26", "rnd", "t", "t_rnd"]].round(3).to_string(index=False))
    pc = P[P.pool.str.startswith("(")].sort_values("t", ascending=False)
    print(f"\n   pools passing (t >= 3.81, > 0 DEV/VAL/2026, above random): {int(P['pass'].sum())} of {len(P)}")
    print("   best 12 session x class pools:\n" + pc.head(12)[["pool", "trig", "filt", "exit", "n", "DEV", "VAL", "Y26", "rnd", "t", "t_rnd"]].round(3).to_string(index=False))
    print(f"   positive in DEV, VAL and 2026: {int(((P.DEV > 0) & (P.VAL > 0) & (P.Y26 > 0)).sum())} of {len(P)} pools")
    # 2./3. cells and walk-forward
    rows = []; wf = []
    for (mk, ss), g in X.groupby(["mkt", "sess"]):
        gi = g.index.to_numpy(); best = None
        for tg, f, x in rules:
            cx = "c1" if x == "r1" else "ch"
            m = gi[(g.trig == tg).to_numpy() & fmask(g, f)]
            if len(m) < 30: continue
            s = X.loc[m]; d = s[dv[m]]
            r = dict(mkt=mk, sess=ss, trig=tg, filt=f, exit=x, n=len(s), DEV=s[pm["DEV"][m]][x].mean(), VAL=s[pm["VAL"][m]][x].mean(),
                     Y26=s[pm["Y26"][m]][x].mean(), rnd=d[cx].mean(), t=tstat(d[x]), t_rnd=tstat(d[cx]))
            rows.append(r)
            if (pm["DEV"][m]).sum() >= 50 and (best is None or r["DEV"] > best["DEV"]): best = r
        if best: wf.append(best)
    S = pd.DataFrame(rows); S["pass"] = (S.t >= 4.33) & (S.DEV > 0) & (S.VAL > 0) & (S.Y26 > 0) & (S.DEV > S.rnd)
    S.to_csv("data/si_ledgers/ORB11_ENTRY_cells.csv", index=False)
    W = pd.DataFrame(wf)
    print(f"\n2. CELLS: {len(S)} tested, passing (t >= 4.33, > 0 DEV/VAL/2026, above random): {int(S['pass'].sum())}")
    print(S.sort_values("t", ascending=False).head(12)[["mkt", "sess", "trig", "filt", "exit", "n", "DEV", "VAL", "Y26", "rnd", "t"]].round(3).to_string(index=False))
    print(f"   highest t {S.t.max():.2f}; the same search on random entries (same days, same exit): highest {S.t_rnd.max():.2f}, 95th pct of cells {np.nanpercentile(S.t_rnd, 95):.2f} vs real {np.nanpercentile(S.t, 95):.2f}")
    print(f"\n3. WALK-FORWARD: best of 72 rules per symbol-session on DEV ({len(W)} cells): DEV {W.DEV.mean():+.3f} -> VAL {W.VAL.mean():+.3f} (positive {int((W.VAL > 0).sum())}), 2026 {W.Y26.mean():+.3f} (positive {int((W.Y26 > 0).sum())}); both: {int(((W.VAL > 0) & (W.Y26 > 0)).sum())}")
    print("   triggers chosen:", W.trig.value_counts().to_dict(), " filters:", W.filt.value_counts().to_dict())
    pw = []
    for key, q in P[P.pool.str.startswith("(")].groupby("pool"):
        b = q.sort_values("DEV", ascending=False).iloc[0]; pw.append(b)
    PW = pd.DataFrame(pw)
    print("   best rule per session x class on DEV, then VAL / 2026:\n" + PW[["pool", "trig", "filt", "exit", "n", "DEV", "VAL", "Y26"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
