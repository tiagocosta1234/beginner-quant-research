"""DAY2K-F: round-number level reactions as the daily 1:1 setup. PREREG_DAY2K_F.md. Run from the repo root.
  python -m forex.self_improving.day2k.day2kf --dry-run | --calibrate | --run"""
import sys
import numpy as np, pandas as pd
from forex.self_improving.day2k import day2k as D

INST = {"XAUUSD": 25.0, "SP": 50.0, "NSDQ": 250.0, "DOW": 250.0, "DAX": 250.0, "EURUSD": 0.005, "GBPUSD": 0.005, "AUDUSD": 0.005, "USDCAD": 0.005, "USDCHF": 0.005, "USDJPY": 0.5}
KS = (0.3, 0.6)
WIN0, WIN1 = 10 * 3600 + 6 * 60, 20 * 3600
OFFS = {"TRUE": 0.0, "P1": 0.37, "P2": 0.23, "P3": 0.61}
CACHE = D.CACHE / "day2kf.npz"


def events_for(A, days, off):
    """first level-cross event per day: returns arrays (bar index, level, direction +1 up/-1 down) with -1 index when none"""
    t = A["t"]; mh = (A["bh"] + A["ah"]) / 2; ml = (A["bl"] + A["al"]) / 2; mc = (A["bc"] + A["ac"]) / 2
    return t, mh, ml, mc


def find_event(mh, ml, mc, i0, i1, G, sh):
    """first level-cross bar j in [i0, i1), the level L and the direction (+1 up, -1 down); uses mid prices of bars up to j only"""
    prev = mc[i0 - 1:i1 - 1]; up = np.floor((mh[i0:i1] - sh) / G) > np.floor((prev - sh) / G); dn = np.ceil((ml[i0:i1] - sh) / G) < np.ceil((prev - sh) / G)
    ev = np.where(up | dn)[0]
    if len(ev) == 0: return None
    j = i0 + int(ev[0]); e = int(ev[0])
    if up[e] and dn[e]: direction = 1 if (np.floor((mh[j] - sh) / G) * G + sh - mc[j - 1]) <= (mc[j - 1] - (np.ceil((ml[j] - sh) / G) * G + sh)) else -1
    else: direction = 1 if up[e] else -1
    L = (np.floor((mh[j] - sh) / G) * G + sh) if direction > 0 else (np.ceil((ml[j] - sh) / G) * G + sh)
    return j, L, direction


def simulate(sym, G, off, days, atr, with_truncation=False):
    A = D.load(sym); t, mh, ml, mc = events_for(A, days, off)
    out = np.full((len(days), 2, 2, 2), np.nan)       # [day, k, mode(0 fade,1 continue), 0=R | 1=resolved]
    res = np.zeros((len(days), 2, 2), bool); info = []
    sh = off * G
    for di, d in enumerate(days):
        if not np.isfinite(atr[di]): continue
        i0 = int(np.searchsorted(t, d * 86400 + WIN0)); i1 = int(np.searchsorted(t, d * 86400 + WIN1)); ix = int(np.searchsorted(t, d * 86400 + D.EXIT))
        if i1 - i0 < 200 or ix >= len(t) or t[ix] != d * 86400 + D.EXIT: continue
        fe = find_event(mh, ml, mc, i0, i1, G, sh)
        if fe is None: continue
        j, L, direction = fe
        sp = A["sp"][j]
        for mode in (0, 1):
            side = direction if mode == 1 else -direction
            E = L + sp / 2 if side > 0 else L - sp / 2
            for ki, k in enumerate(KS):
                Dd = k * atr[di]; tp = E + side * Dd; sl = E - side * Dd
                hi = A["bh"][j:ix] if side > 0 else A["ah"][j:ix]; lo = A["bl"][j:ix] if side > 0 else A["al"][j:ix]
                htp, hsl = (hi >= tp, lo <= sl) if side > 0 else (lo <= tp, hi >= sl)
                a = int(np.argmax(htp)) if htp.any() else 10 ** 9; b = int(np.argmax(hsl)) if hsl.any() else 10 ** 9
                if b <= a and b < 10 ** 9: r = -1.0; rs = True
                elif a < 10 ** 9: r = 1.0; rs = True
                else:
                    X = A["bo"][ix] if side > 0 else A["ao"][ix]; r = float(np.clip(side * (X - E) / Dd, -1, 1)); rs = False
                out[di, ki, mode, 0] = r; res[di, ki, mode] = rs
        info.append((di, j, L, direction))
    return out[..., 0], res, info


def build(lo, hi, tag):
    f = D.CACHE / f"day2kf_{tag}.npz"; days = D.trading_days(lo, hi)
    if f.exists(): z = np.load(f, allow_pickle=True); return days, z["R"], z["RES"], z["N"]
    full = D.trading_days("2021-10-01", hi); R = np.full((len(days), len(INST), len(OFFS), 2, 2), np.nan); RES = np.zeros(R.shape, bool); N = np.zeros((len(INST), len(OFFS)), int)
    for si, (sym, G) in enumerate(INST.items()):
        A = D.load(sym); atr = D.atr20(A, full)[np.isin(full, days)]
        for oi, (on, off) in enumerate(OFFS.items()):
            r, rs, info = simulate(sym, G, off, days, atr); R[:, si, oi] = r; RES[:, si, oi] = rs; N[si, oi] = len(info)
        print("  built", sym, N[si].tolist(), flush=True)
    np.savez_compressed(f, R=R, RES=RES, N=N); return days, R, RES, N


def stats(days, R, RES):
    dev = days <= D.d64(D.DEV_HI); val = (days >= D.d64(D.VAL_LO)) & (days <= D.d64(D.VAL_HI)); rows = []
    for si, sym in enumerate(INST):
        for mode, mn in ((0, "fade"), (1, "continue")):
            for ki, k in enumerate(KS):
                r0 = R[:, si, 0, ki, mode]; r1 = R[:, si, 1, ki, mode]; both = np.isfinite(r0) & np.isfinite(r1); diff = np.where(both, r0 - r1, np.nan)
                md, td = D.block_t(r0[dev]); mv, tv = D.block_t(r0[val]); m1, t1 = D.block_t(r1[dev]); mdf, tdf = D.block_t(diff[dev]); nv = int(np.isfinite(r0[val]).sum())
                rs = RES[:, si, 0, ki, mode][np.isfinite(r0)]; w = np.nanmean(r0[np.isfinite(r0) & (np.abs(r0) >= 0.999)] > 0) if (np.abs(r0[np.isfinite(r0)]) >= 0.999).any() else np.nan
                rows.append(dict(cell=f"{sym}-{mn}-k{k}", n_dev=int(np.isfinite(r0[dev]).sum()), dev_R=md, dev_t=td, P1_R=m1, P1_t=t1, diff_t=tdf, n_val=nv, val_R=mv, val_t=tv, win=w, resolved=float(rs.mean()),
                                 S1=bool(md > 0 and td >= 3.10 and tdf >= 2.0 and mv > 0 and tv >= 1.65 and nv >= 200)))
    return pd.DataFrame(rows)


def main():
    a = sys.argv[1:]; days, R, RES, N = build(D.LO, D.VAL_HI, "devval"); pd.set_option("display.width", 230)
    if "--dry-run" in a:
        print("events per instrument [TRUE, P1, P2, P3] over", len(days), "days:"); [print(f"  {s:7s}", N[i].tolist(), "resolved k0.3/k0.6:", round(float(RES[:, i, 0, 0, 0][np.isfinite(R[:, i, 0, 0, 0])].mean()), 2), round(float(RES[:, i, 0, 1, 0][np.isfinite(R[:, i, 0, 1, 0])].mean()), 2)) for i, s in enumerate(INST)]
        rng = np.random.default_rng(4); bad = 0; n = 0
        for _ in range(60):
            si = int(rng.integers(len(INST))); sym = list(INST)[si]; G = INST[sym]; di = int(rng.integers(30, len(days))); d = int(days[di]); A = D.load(sym); t = A["t"]
            mh, ml, mc = (A["bh"] + A["ah"]) / 2, (A["bl"] + A["al"]) / 2, (A["bc"] + A["ac"]) / 2; i0 = int(np.searchsorted(t, d * 86400 + WIN0)); i1 = int(np.searchsorted(t, d * 86400 + WIN1))
            if i1 - i0 < 200: continue
            fe = find_event(mh, ml, mc, i0, i1, G, 0.0)
            if fe is None: continue
            j = fe[0]; cut = j + 1                                               # keep bars up to and including the event bar, drop everything after
            fe2 = find_event(mh[:cut], ml[:cut], mc[:cut], i0, min(i1, cut), G, 0.0); n += 1; bad += int(not (fe2 is not None and fe2 == fe))
        print(f"truncation test (event bar and level unchanged with all later bars removed): {n - bad}/{n} identical"); return
    if "--calibrate" in a:
        dev = days <= D.d64(D.DEV_HI); orc = []
        for si in range(len(INST)):
            for ki in range(2):
                f = R[:, si, 0, ki, 0]; c = R[:, si, 0, ki, 1]; o = np.fmax(f, c); orc.append(D.block_t(o[dev])[0])
        print("POSITIVE CONTROL (oracle side per event) mean dev R: min %.2f median %.2f max %.2f" % (min(orc), float(np.median(orc)), max(orc)))
        for oi, on in enumerate(("P1", "P2", "P3"), start=1):
            S = stats(days, np.concatenate([R[:, :, oi:oi + 1], R[:, :, 1:2]], axis=2), RES)
            print(f"placebo grid {on}: cells with DEV t >= 3.10: {int((S.dev_t >= 3.10).sum())} | best dev t {S.dev_t.max():.2f} | S1 {int(S.S1.sum())}")
        return
    if "--run" in a:
        S = stats(days, R, RES); S.to_csv(D.CACHE / "DAY2KF_cells.csv", index=False); print(S.round(3).to_string(index=False)); print("S1 survivors:", int(S.S1.sum()))
        print("\nclass summary: mean dev_R TRUE grid vs shifted grid P1, fade / continue, all instruments:");
        for mn in ("fade", "continue"):
            q = S[S.cell.str.contains(mn)]; print(f"  {mn}: TRUE {q.dev_R.mean():+.4f} R | P1 {q.P1_R.mean():+.4f} R | cells with true-grid dev t>2: {int((q.dev_t > 2).sum())} of {len(q)} | with diff t>2: {int((q.diff_t > 2).sum())}")
        return
    print(__doc__)


if __name__ == "__main__":
    main()
