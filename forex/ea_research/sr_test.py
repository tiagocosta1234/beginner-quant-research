"""SR exactly as in PREREG_SR.md.  python -m forex.ea_research.sr_test [--dry] [--hold] [--jobs N]"""
import sys, os, glob, time
import numpy as np
import pandas as pd
from multiprocessing import Pool

HOLD = "--hold" in sys.argv
DRY = "--dry" in sys.argv
JOBS = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 8
DATA = "forex/data_mt5/"
END_T = int(pd.Timestamp("2026-10-03" if HOLD else "2026-01-01").timestamp())
TFS = {"H1": 3600, "H2": 7200, "H4": 14400}
K, ZF, MAXAGE, NEAR, HOLDBARS, TP_R = 5, 0.25, 300, 3.0, 24, 1.5
PER = {"DEV": (pd.Timestamp("2021-12-01").timestamp(), pd.Timestamp("2024-01-01").timestamp()),
       "VAL": (pd.Timestamp("2024-01-01").timestamp(), pd.Timestamp("2026-01-01").timestamp()),
       "HOLD": (pd.Timestamp("2026-01-01").timestamp(), pd.Timestamp("2026-10-03").timestamp())}


def bars(m1, step):
    g = m1.groupby((m1.t // step) * step, sort=True)
    b = pd.DataFrame({"bo": g.bo.first(), "bh": g.bh.max(), "bl": g.bl.min(), "bc": g.bc.last(), "ao": g.ao.first(), "ah": g.ah.max(), "al": g.al.min(), "ac": g.ac.last(),
                      "mo": g.mo.first(), "mh": g.mh.max(), "ml": g.ml.min(), "mc": g.mc.last()})
    b.index.name = "t"
    return b.reset_index()


def make_signals(b, rng=None):
    """returns sig[mode][s] (int8 array) and lev[mode][s] (float array); mode 0 = bounce, 1 = breakout; s 0 = all levels, 1 = levels with >= 2 touches."""
    mh, ml, mc = b.mh.to_numpy(), b.ml.to_numpy(), b.mc.to_numpy()
    n = len(b)
    cp = np.r_[mc[0], mc[:-1]]
    tr = np.maximum.reduce([mh - ml, np.abs(mh - cp), np.abs(ml - cp)])
    atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
    hs, ls = pd.Series(mh), pd.Series(ml)
    left_h = hs.shift(1).rolling(K).max().to_numpy()
    right_h = hs[::-1].shift(1).rolling(K).max()[::-1].to_numpy()
    left_l = ls.shift(1).rolling(K).min().to_numpy()
    right_l = ls[::-1].shift(1).rolling(K).min()[::-1].to_numpy()
    sh = (mh > left_h) & (mh >= right_h)
    sl = (ml < left_l) & (ml <= right_l)
    sig = np.zeros((2, 2, n), np.int8)
    lev = np.zeros((2, 2, n))
    P, T, B = [], [], []
    for j in range(40, n):
        a = atr[j]
        z = ZF * a
        i = j - K
        for isw, price in ((sh[i], mh[i]), (sl[i], ml[i])):
            if not isw:
                continue
            p = price + (rng.uniform(-2, 2) * a if rng is not None else 0.0)
            hit = -1
            for k, lp in enumerate(P):
                if abs(lp - p) < z:
                    hit = k
                    break
            if hit >= 0:
                T[hit] += 1
                P[hit] += (p - P[hit]) / T[hit]
            else:
                P.append(p); T.append(1); B.append(j)
        if j % 50 == 0 and P:
            keep = [k for k in range(len(P)) if j - B[k] <= MAXAGE]
            P, T, B = [P[k] for k in keep], [T[k] for k in keep], [B[k] for k in keep]
        cj, cpj, hj, lj = mc[j], mc[j - 1], mh[j], ml[j]
        best = {}
        for k, L in enumerate(P):
            dist = abs(L - cj)
            if dist > NEAR * a:
                continue
            for s in (0, 1):
                if s == 1 and T[k] < 2:
                    continue
                if hj >= L - z and cj < L - z and cpj < L:
                    c = (0, s, -1)
                elif lj <= L + z and cj > L + z and cpj > L:
                    c = (0, s, 1)
                elif cj > L + z and cpj <= L + z:
                    c = (1, s, 1)
                elif cj < L - z and cpj >= L - z:
                    c = (1, s, -1)
                else:
                    continue
                if (c[0], c[1]) not in best or dist < best[(c[0], c[1])][0]:
                    best[(c[0], c[1])] = (dist, c[2], L)
        for (m, s), (dist, side, L) in best.items():
            sig[m, s, j] = side
            lev[m, s, j] = L
    return sig, lev, atr


def simulate(b, sg, lv, atr):
    t, bo, ao, bh, bl, ah, al = (b[c].to_numpy() for c in ("t", "bo", "ao", "bh", "bl", "ah", "al"))
    n = len(t)
    hr = (t // 3600) % 24
    out_t, out_r = [], []
    busy = -1
    for j in np.nonzero(sg)[0]:
        i0 = j + 1
        if i0 <= busy or i0 + HOLDBARS + 1 >= n or hr[i0] in (23, 0):
            continue
        side, L, a = sg[j], lv[j], atr[j]
        z = ZF * a
        if side > 0:
            e = ao[i0]
            stop = L - z - 0.5 * a
            D = e - stop
            if D < 0.5 * a:
                D = 0.5 * a
                stop = e - D
            tgt = e + TP_R * D
            r = None
            for k in range(i0, i0 + HOLDBARS + 1):
                if bo[k] <= stop:
                    r = (bo[k] - e) / D
                    break
                if bl[k] <= stop:
                    r = -1.0
                    break
                if bo[k] >= tgt:
                    r = (bo[k] - e) / D
                    break
                if bh[k] >= tgt:
                    r = TP_R
                    break
            if r is None:
                k = i0 + HOLDBARS + 1
                r = (bo[k] - e) / D
        else:
            e = bo[i0]
            stop = L + z + 0.5 * a
            D = stop - e
            if D < 0.5 * a:
                D = 0.5 * a
                stop = e + D
            tgt = e - TP_R * D
            r = None
            for k in range(i0, i0 + HOLDBARS + 1):
                if ao[k] >= stop:
                    r = (e - ao[k]) / D
                    break
                if ah[k] >= stop:
                    r = -1.0
                    break
                if ao[k] <= tgt:
                    r = (e - ao[k]) / D
                    break
                if al[k] <= tgt:
                    r = TP_R
                    break
            if r is None:
                k = i0 + HOLDBARS + 1
                r = (e - ao[k]) / D
        busy = k
        out_t.append(t[min(k, n - 1)])
        out_r.append(r)
    return np.array(out_t), np.array(out_r)


def stats(tx, r, lo, hi):
    m = (tx >= lo) & (tx < hi)
    x = r[m]
    n = len(x)
    if n < 3 or x.std() == 0:
        return n, np.nan, np.nan, np.nan
    return n, x.mean(), x.mean() / (x.std(ddof=1) / np.sqrt(n)), (x > 0).mean()


def one_symbol(path):
    sym = os.path.basename(path).replace("_M1_rates.parquet", "")
    d = pd.read_parquet(path, columns=["t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"]).sort_values("t").drop_duplicates("t")
    d = d[(d.t < END_T) & (d.bo > 0) & (d.ao >= d.bo)]
    m1 = d[["t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"]].copy()
    m1["mo"], m1["mh"], m1["ml"], m1["mc"] = (d.bo + d.ao) / 2, (d.bh + d.ah) / 2, (d.bl + d.al) / 2, (d.bc + d.ac) / 2
    rows, plc = [], {}
    rng = np.random.default_rng(abs(hash(sym)) % (2 ** 32))
    for tf, step in TFS.items():
        b = bars(m1, step)
        if len(b) < 800:
            continue
        sig, lev, atr = make_signals(b)
        for mode in (0, 1):
            for s in (0, 1):
                tx, r = simulate(b, sig[mode, s], lev[mode, s], atr)
                row = dict(sym=sym, tf=tf, mode="bounce" if mode == 0 else "breakout", s=s + 1)
                for p in ("DEV", "VAL") + (("HOLD",) if HOLD else ()):
                    n, mu, tt, hit = stats(tx, r, *PER[p])
                    row.update({f"n_{p}": n, f"mu_{p}": mu, f"t_{p}": tt, f"hit_{p}": hit})
                rows.append(row)
        if not DRY:
            for dr in range(10):
                sig2, lev2, atr2 = make_signals(b, rng)
                for mode in (0, 1):
                    for s in (0, 1):
                        tx, r = simulate(b, sig2[mode, s], lev2[mode, s], atr2)
                        n, mu, tt, hit = stats(tx, r, *PER["DEV"])
                        plc.setdefault(dr, []).append(tt if n >= 100 and tt == tt else np.nan)
    return rows, plc


if __name__ == "__main__":
    files = sorted(glob.glob(DATA + "*_M1_rates.parquet"))
    if DRY:
        t0 = time.time()
        rows, _ = one_symbol(DATA + "EURUSD_M1_rates.parquet")
        R = pd.DataFrame(rows)
        print("EURUSD cells", len(R), "secs %.1f" % (time.time() - t0))
        print(R[["tf", "mode", "s", "n_DEV", "mu_DEV", "t_DEV", "n_VAL", "mu_VAL", "t_VAL"]].round(3).to_string(index=False))
        sys.exit()
    t0 = time.time()
    with Pool(JOBS) as pool:
        res = pool.map(one_symbol, files)
    R = pd.DataFrame([r for rr, _ in res for r in rr])
    R.to_csv("data/tmp/sr_cells.csv", index=False)
    mx = []
    for dr in range(10):
        allv = np.array([x for _, p in res for x in p.get(dr, [])], dtype=float)
        mx.append(np.nanmax(allv))
    ceil = np.percentile(mx, 95)
    R["cand"] = (R.mu_DEV >= 0.05) & (R.t_DEV >= 4.0) & (R.n_DEV >= 100) & (R.mu_VAL > 0) & (R.t_VAL >= 1.65) & (R.n_VAL >= 50) & (R.t_DEV > ceil)
    print(f"cells {len(R)} | placebo (random levels) max-t over cells per draw: {np.round(sorted(mx), 2).tolist()} | 95th {ceil:.2f} | secs {time.time() - t0:.0f}")
    print("share positive: DEV %.1f%%, VAL %.1f%%, both %.1f%%" % ((R.mu_DEV > 0).mean() * 100, (R.mu_VAL > 0).mean() * 100, ((R.mu_DEV > 0) & (R.mu_VAL > 0)).mean() * 100))
    print("median mean R per trade by mode x timeframe (DEV / VAL):")
    print(R.groupby(["mode", "tf"])[["mu_DEV", "mu_VAL"]].median().round(3).to_string())
    print("median trades per cell (DEV):", R.groupby("tf").n_DEV.median().to_dict())
    print("TOP 10 by DEV t:\n", R.sort_values("t_DEV", ascending=False).head(10)[["sym", "tf", "mode", "s", "n_DEV", "mu_DEV", "t_DEV", "n_VAL", "mu_VAL", "t_VAL"]].round(3).to_string(index=False))
    print("CANDIDATES:", R[R.cand][["sym", "tf", "mode", "s", "mu_DEV", "t_DEV", "mu_VAL", "t_VAL"]].round(3).to_dict("records"))
    both = R[(R.mu_DEV > 0) & (R.mu_VAL > 0)].sort_values("t_VAL", ascending=False).head(8)
    print("Positive in both, top 8 by VAL t:\n", both[["sym", "tf", "mode", "s", "n_DEV", "mu_DEV", "t_DEV", "n_VAL", "mu_VAL", "t_VAL"]].round(3).to_string(index=False))
