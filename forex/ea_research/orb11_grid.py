"""ORB11_GRID (PREREG_ORB11_GRID.md): 99 stop / target exits on the trader's 30-minute London / NY ORB entries and on random entries, 46 MT5 broker symbols.
   python -m forex.ea_research.orb11_grid --dry | (run)"""
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.breakouts import local_clock
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS
from forex.ea_research.orb11 import SESS, END, H, M

SL = np.array([0.10, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0])
TP = np.array([0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 10, np.inf])
NAMES = [f"SL{s:g}_TP{('none' if np.isinf(t) else f'{t:g}')}" for s in SL for t in TP]
PER = {"DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "Y26": ("2026-01-01", "2026-10-02")}


def grid(D, k, kend, side, e, B):
    """R for each of the 99 exits (SL in box widths, TP in multiples of SL), position filled at minute k at price e."""
    if side > 0:
        fav, adv, op, end = D["bh"][k:kend] - e, e - D["bl"][k:kend], D["bo"][k:kend], D["bo"][kend]
        gap = lambda i: e - op[i]
    else:
        fav, adv, op, end = e - D["al"][k:kend], D["ah"][k:kend] - e, D["ao"][k:kend], D["ao"][kend]
        gap = lambda i: op[i] - e
    n = len(fav); cf, ca = np.maximum.accumulate(fav), np.maximum.accumulate(adv)
    x_end = side * (end - e)
    out = np.empty(len(SL) * len(TP), np.float32); j = 0
    for s in SL * B:
        i_sl = int(np.searchsorted(ca, s)); loss = max(s, gap(i_sl)) if i_sl < n else 0.0
        for tp in TP:
            i_tp = int(np.searchsorted(cf, tp * s)) if np.isfinite(tp) else n
            if i_sl < n and i_sl <= i_tp: out[j] = -loss / s
            elif i_tp < n: out[j] = tp
            else: out[j] = x_end / s
            j += 1
    return out


def market(args):
    sym, end = args
    D = load(sym, end); t = D["t"]; rng = np.random.default_rng(zlib.crc32(sym.encode()))
    meta, vals = [], []
    for sess, (tz, op_s, cl_s) in SESS.items():
        lc = local_clock(t, tz)
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
            up = np.flatnonzero(D["ah"][i1:kend] >= Hb); dn = np.flatnonzero(D["bl"][i1:kend] <= Lb)
            ku, kd = (i1 + up[0] if len(up) else None), (i1 + dn[0] if len(dn) else None)
            if not (ku is None and kd is None) and not (ku is not None and ku == kd):
                side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
                k = ku if side > 0 else kd
                e = max(Hb, D["ao"][k]) if side > 0 else min(Lb, D["bo"][k])
                if k < kend - 1:
                    meta.append((sym, sess, day, "ORB")); vals.append(grid(D, k, kend, side, e, B))
            kc = int(rng.integers(i1, kend - 1)); sc = 1 if rng.random() < 0.5 else -1
            meta.append((sym, sess, day, "CTRL")); vals.append(grid(D, kc, kend, sc, D["ao"][kc] if sc > 0 else D["bo"][kc], B))
    return meta, vals


def collect():
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, [(s, END) for s in SYMS]))
    meta = pd.DataFrame([m for r in res for m in r[0]], columns=["mkt", "sess", "day", "kind"])
    V = np.vstack([v for r in res for v in r[1]])
    return meta, V


def main():
    if "--dry" in sys.argv:
        D = load("EURUSD", END); meta, vals = market(("EURUSD", END)); V = np.vstack(vals); m = pd.DataFrame(meta, columns=["mkt", "sess", "day", "kind"])
        j = NAMES.index("SL1_TP1"); print("trades", m.groupby(["sess", "kind"]).size().to_dict())
        from forex.ea_research.orb11 import market as m11
        T = pd.DataFrame(m11(("EURUSD", END)), columns=["mkt", "sess", "day", "kind", "side", "t_entry", "Rpx", "R11", "R11_opt", "R_hold"])
        a = T[T.kind == "ORB"].R11.mean(); b = V[(m.kind == "ORB").to_numpy(), j].mean()
        print(f"check SL1_TP1 vs ORB11 R11 on EURUSD: {b:+.4f} vs {a:+.4f} (ORB11 also skipped R < 2 spreads)")
        cut = pd.Timestamp("2024-06-01").timestamp(); mc, vc = market(("EURUSD", cut)); mc = pd.DataFrame(mc, columns=m.columns); Vc = np.vstack(vc)
        sel = lambda mm: ((mm.day < pd.Timestamp(cut - 2 * 86400, unit="s")) & (mm.kind == "ORB")).to_numpy()
        print("truncation:", np.allclose(V[sel(m)][:len(Vc[sel(mc)])], Vc[sel(mc)]))
        return
    meta, V = collect(); meta["cls"] = meta.mkt.map(mclass)
    np.save("D:/finance/si_ledgers/ORB11_GRID_V.npy", V); meta.to_parquet("D:/finance/si_ledgers/ORB11_GRID_meta.parquet")
    pmask = {p: ((meta.day >= a) & (meta.day <= b)).to_numpy() for p, (a, b) in PER.items()}
    orb, ctl = (meta.kind == "ORB").to_numpy(), (meta.kind == "CTRL").to_numpy()
    print(f"{orb.sum()} breakout trades, {ctl.sum()} random entries, {V.shape[1]} exits each")
    # 1. pooled: best exit on breakouts vs best exit on random entries, DEV, and how the DEV-best does later
    print("\n1. POOLED best exit chosen on DEV 2022-24 (R per trade), then VAL 2025 / 2026; random-entry grid alongside")
    for grp in [("sess",), ("sess", "cls")]:
        for key, g in meta[orb].groupby(list(grp)):
            m = (meta[list(grp)] == pd.Series(key if isinstance(key, tuple) else (key,), index=list(grp))).all(axis=1).to_numpy()
            dev_o = V[m & orb & pmask["DEV"]].mean(0); dev_c = V[m & ctl & pmask["DEV"]].mean(0)
            jo = int(np.argmax(dev_o)); jc = int(np.argmax(dev_c))
            vo = V[m & orb & pmask["VAL"], jo].mean(); yo = V[m & orb & pmask["Y26"], jo].mean()
            print(f"  {str(key):24s} breakout best {NAMES[jo]:15s} DEV {dev_o[jo]:+.3f} -> VAL {vo:+.3f}, 2026 {yo:+.3f} | random best {NAMES[jc]:15s} DEV {dev_c[jc]:+.3f} | exits > 0 on DEV: breakout {int((dev_o > 0).sum())}/99, random {int((dev_c > 0).sum())}/99")
    # 2. per cell walk-forward
    print("\n2. PER CELL (symbol x session): best of 99 exits on DEV, then the same exit in VAL / 2026")
    rows = []
    for (mk, ss), g in meta.groupby(["mkt", "sess"]):
        m = ((meta.mkt == mk) & (meta.sess == ss)).to_numpy()
        for kind, km in (("ORB", orb), ("CTRL", ctl)):
            d = V[m & km & pmask["DEV"]]
            if len(d) < 50: continue
            mu = d.mean(0); j = int(np.argmax(mu))
            dv = V[m & km & (pmask["DEV"] | pmask["VAL"]), j]
            rows.append(dict(mkt=mk, sess=ss, kind=kind, exit=NAMES[j], DEV=mu[j], VAL=V[m & km & pmask["VAL"], j].mean(), Y26=V[m & km & pmask["Y26"], j].mean(),
                             t=dv.mean() / dv.std() * np.sqrt(len(dv)) if dv.std() > 0 else 0))
    W = pd.DataFrame(rows); W.to_csv("D:/finance/si_ledgers/ORB11_GRID_walkforward.csv", index=False)
    for kind in ("ORB", "CTRL"):
        w = W[W.kind == kind]
        print(f"  {kind}: {len(w)} cells; DEV-best mean DEV {w.DEV.mean():+.3f} -> VAL {w.VAL.mean():+.3f} (positive {int((w.VAL > 0).sum())}), 2026 {w.Y26.mean():+.3f} (positive {int((w.Y26 > 0).sum())}); positive in VAL AND 2026: {int(((w.VAL > 0) & (w.Y26 > 0)).sum())}")
    # 3. pass rule
    allp = []
    for (mk, ss), g in meta[orb].groupby(["mkt", "sess"]):
        m = ((meta.mkt == mk) & (meta.sess == ss)).to_numpy()
        mo, mc = m & orb, m & ctl
        dv = V[mo & (pmask["DEV"] | pmask["VAL"])]; t = dv.mean(0) / dv.std(0) * np.sqrt(len(dv))
        ok = (t >= 4.4) & (V[mo & pmask["DEV"]].mean(0) > 0) & (V[mo & pmask["VAL"]].mean(0) > 0) & (V[mo & pmask["Y26"]].mean(0) > 0) & (V[mo].mean(0) > V[mc].mean(0))
        allp.append((mk, ss, float(np.nanmax(t)), NAMES[int(np.nanargmax(t))], int(ok.sum())))
    P = pd.DataFrame(allp, columns=["mkt", "sess", "max_t", "exit_max_t", "passing_exits"]).sort_values("max_t", ascending=False)
    P.to_csv("D:/finance/si_ledgers/ORB11_GRID_cells.csv", index=False)
    print(f"\n3. Cells passing (t >= 4.4, > 0 in DEV, VAL, 2026, beats random): {int(P.passing_exits.sum())} of 9,108. Highest DEV+VAL t per cell:")
    print(P.head(10).to_string(index=False))
    # random-entry ceiling: the same max-t on random entries
    mt = []
    for (mk, ss), g in meta[ctl].groupby(["mkt", "sess"]):
        m = ((meta.mkt == mk) & (meta.sess == ss)).to_numpy() & ctl
        dv = V[m & (pmask["DEV"] | pmask["VAL"])]; mt.append(np.nanmax(dv.mean(0) / dv.std(0) * np.sqrt(len(dv))))
    print(f"   the same statistic on RANDOM entries: highest {np.nanmax(mt):.2f}, 95th percentile {np.nanpercentile(mt, 95):.2f}")
    # 4. heat map pooled (all symbols, both sessions, DEV+VAL) for the result file
    m = orb & (pmask["DEV"] | pmask["VAL"]); mc = ctl & (pmask["DEV"] | pmask["VAL"])
    hm = pd.DataFrame(V[m].mean(0).reshape(len(SL), len(TP)), index=[f"SL {s:g}B" for s in SL], columns=[("none" if np.isinf(t) else f"{t:g}R") for t in TP])
    hc = pd.DataFrame(V[mc].mean(0).reshape(len(SL), len(TP)), index=hm.index, columns=hm.columns)
    print("\n4. All symbols, both sessions, 2022-25, R per trade (rows = stop in box widths, columns = target):\nBREAKOUT\n" + hm.round(3).to_string() + "\nRANDOM ENTRY\n" + hc.round(3).to_string())
    hm.to_csv("D:/finance/si_ledgers/ORB11_GRID_heat.csv")


if __name__ == "__main__":
    main()
