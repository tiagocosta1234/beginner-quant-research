"""Value of the FINAL pass-lock design (the trader 2026-10-09: stop when the COUNTED value reaches 8,000, unrealised profit included, confirm after closing, release if short).
   python -m mt5broker.ea_research.clean_lock_final
Compares, with the clean_bootstrap engine (plan A x1.2, 36 / 52 business days, 50/50 regime mix and each regime, edge kept 1.0 and 0.7): no lock; cap-aware lock at counted equity >= 8,300 (the earlier test); cap-aware lock at >= 8,100 (final margin 100 USD); cap-aware lock at >= 8,000 (no margin).
Closing 24 oz costs slippage: at the trigger the counted equity is L; after the close the counted balance is L - cost. If it is below 8,000 the guard RELEASES and trading resumes (the path continues without having passed, and has lost the positions' future). cost = 0 / 50 / 150 USD tested."""
from __future__ import annotations

import numpy as np

from mt5broker.ea_research import clean_boot_lib as L
from mt5broker.ea_research import clean_bootstrap as BS

A, CAPD, TARGET = BS.A, BS.CAPD, BS.TARGET


def run_lock(V12, B12, H12, idx, level, cost):
    n = idx.shape[0]; cnt = np.full(n, BS.C0); st = np.zeros(n, np.int8); day = np.full(n, -1, np.int32)
    for j in range(idx.shape[1]):
        v, b, hi = V12[idx[:, j]], B12[idx[:, j]], H12[idx[:, j]]; act = st == 0
        br = act & ((b <= -0.025 * A) | (A + cnt + b <= 0.92 * A)); st = np.where(br, 2, st); day = np.where(br, j, day); act = st == 0
        if level is not None:
            peak = cnt + np.minimum(hi, CAPD); lk = act & (peak >= level)
            ok = lk & (peak - cost >= TARGET)                        # confirmed after the close
            st = np.where(ok, 1, st); day = np.where(ok, j, day)
            rel = lk & ~ok                                            # released: the day is closed flat at the trigger value less the cost; the path continues
            cnt = np.where(rel, cnt + np.minimum(peak - cnt, CAPD) - cost, cnt)
            act = st == 0
            skip = rel
        else:
            skip = np.zeros(n, bool)
        cnt = np.where(act & ~skip, cnt + np.where(v > 0, np.minimum(v, CAPD), v), cnt)
        ps = act & ~skip & (cnt >= TARGET); st = np.where(ps, 1, st); day = np.where(ps, j, day)
    return st, day


def est(P, w, level, cost, outer=200, inner=2000):
    res = []
    for _ in range(outer):
        hist = {}
        for p, arr in P.items():
            k = BS.stationary_idx(len(arr[0]), 1, len(arr[0]))[0]                # ONE index per pool so V, B and the day high stay aligned
            hist[p] = tuple(a[k] for a in arr)
        nE = int(round(w * inner)); sts = []
        for p, c in (("MT5", nE), ("FT", inner - nE)):
            if c == 0: continue
            V12, B12, V18, B18, H12 = hist[p]; sts.append(run_lock(V12, B12, H12, BS.stationary_idx(len(V12), c, BS.H22), level, cost))
        st = np.concatenate([s[0] for s in sts]); day = np.concatenate([s[1] for s in sts])
        res.append((np.mean((st == 1) & (day < BS.H30)), np.mean((st == 1) & (day < BS.H22)), np.mean((st == 2) & (day < BS.H22))))
    r = np.array(res); return r.mean(0), np.percentile(r, 2.5, 0), np.percentile(r, 97.5, 0)


def main():
    for h in (1.0, 0.7):
        P = BS.pools(h); print(f"\n--- edge kept {h:.1f}", flush=True)
        for w, lab in ((0.5, "50/50 mix"), (1.0, "12M only"), (0.0, "5Y only")):
            for name, level, cost in (("no lock", None, 0), ("lock 8,300", 8300.0, 50), ("lock 8,100 cost 0", 8100.0, 0), ("lock 8,100 cost 50", 8100.0, 50), ("lock 8,100 cost 150", 8100.0, 150), ("lock 8,000 cost 50", 8000.0, 50)):
                m, lo, hi = est(P, w, level, cost)
                print(f"  {lab:10s} {name:20s}: by 30 Nov {100*m[0]:5.1f}% [{100*lo[0]:5.1f}-{100*hi[0]:5.1f}] | by 22 Dec {100*m[1]:5.1f}% [{100*lo[1]:5.1f}-{100*hi[1]:5.1f}] | breach {100*m[2]:4.1f}%", flush=True)


if __name__ == "__main__":
    main()
