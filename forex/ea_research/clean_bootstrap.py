"""A2 (the trader 2026-10-09, "faz A e B"): P(pass the MT5 Pro test) from NOW as a block-bootstrap with a confidence interval, mixing the two regimes, with and without the catch-up rule and with edge haircuts.
   python -m forex.ea_research.clean_bootstrap
State at the time of writing (live_state.py, 2026-10-09 19:40 local): balance 100,099.68, counted closed profit +99.68, four gold longs open (floating +470 NOT counted: it can still reverse).
Window: Monday 12 Oct .. Monday 30 Nov = 36 business days; .. Tuesday 22 Dec = 52 business days (last day a withdrawal can be requested).
Method: stationary block bootstrap (mean block 5 days) of the guarded daily series of the pair at x1.2 (loss cap 2,000 only, no profit cap, no pass lock; the MT5 broker counted-profit rule min(day, 2,000) is applied per day; breach = in-day low <= -2,500 or equity <= 92,000).
Regime mix: w = share of paths drawn from the 12-month MT5 broker pool (strong gold trend); 1 - w from the 2022-26 MT5-scaled pool. CI: 200 outer resamples of the HISTORY (each pool resampled by blocks) x 2,000 inner paths: the interval is the uncertainty in the day distribution, not path luck.
Haircut h: every day's result is shifted down by (1 - h) x the pool's mean daily result (h = 1 is the history as it was; 0.5 keeps half of the average edge); the in-day low is shifted the same and the guard still floors the day at -2,000."""
from __future__ import annotations

import numpy as np

from forex.ea_research import clean_boot_lib as L

A, CAPD, TARGET = L.A, L.CAPD, L.TARGET
H30, H22, C0 = 36, 52, 99.68
RNG = np.random.default_rng(20261009)


def stationary_idx(n: int, paths: int, H: int, mean_block: float = 5.0):
    idx = np.empty((paths, H), dtype=np.int64); idx[:, 0] = RNG.integers(0, n, paths); jump = RNG.random((paths, H)) < 1.0 / mean_block; new = RNG.integers(0, n, (paths, H))
    for j in range(1, H):
        idx[:, j] = np.where(jump[:, j], new[:, j], (idx[:, j - 1] + 1) % n)
    return idx


def run(V12, B12, V18, B18, idx, catchup: bool, Hi12=None, lock: str = "none"):
    """lock: none = no pass lock; capaware = lock when counted profit incl. today's capped high >= 8,300; legacy = lock on raw equity (cnt + today's UNCAPPED high >= 8,300): a premature lock is a STUCK path (state 3)."""
    n = idx.shape[0]; cnt = np.full(n, C0); st = np.zeros(n, np.int8); day = np.full(n, -1, np.int32)
    for j in range(idx.shape[1]):
        use = np.zeros(n, bool)
        if catchup and V18 is not None:
            use = (j + 1 >= 20) & (cnt < 0.75 * TARGET * (j + 2) / 37.0)
        v = np.where(use, V18[idx[:, j]], V12[idx[:, j]]); b = np.where(use, B18[idx[:, j]], B12[idx[:, j]]); act = st == 0
        br = act & ((b <= -0.025 * A) | (A + cnt + b <= 0.92 * A))
        st = np.where(br, 2, st); day = np.where(br, j, day); act = st == 0
        if lock != "none":
            hi = Hi12[idx[:, j]]; lk = act & ((cnt + (np.minimum(hi, CAPD) if lock == "capaware" else hi)) >= L.C.LOCK)
            real = lk & (cnt + np.minimum(hi, CAPD) >= TARGET); st = np.where(real, 1, np.where(lk, 3, st)); day = np.where(lk, j, day); act = st == 0
        cnt = np.where(act, cnt + np.where(v > 0, np.minimum(v, CAPD), v), cnt)
        ps = act & (cnt >= TARGET); st = np.where(ps, 1, st); day = np.where(ps, j, day)
    return st, day


def haircut(V, B, h, Hi=None):
    d = (1.0 - h) * V.mean()
    out = (np.maximum(V - d, -CAPD), np.maximum(B - d, -2100.0))
    return out if Hi is None else out + (np.maximum(Hi - d, 0.0),)


def pools(h, policy="HOLD"):
    out = {}
    for p in ("MT5", "FT"):
        s12, s18 = L.series(p, 1.2, policy), L.series(p, 1.8, policy); V12, B12, H12 = haircut(s12["V"], s12["B"], h, s12["Hi"]); V18, B18 = haircut(s18["V"], s18["B"], h); out[p] = (V12, B12, V18, B18, H12)
    return out


def estimate(P, w, catchup, outer=200, inner=2000, lock="none"):
    res = []
    for _ in range(outer):
        # resample each pool's history by blocks, then draw the inner paths from the resampled history (mix by w)
        hist = {}
        for p, arr in P.items():
            n = len(arr[0]); k = stationary_idx(n, 1, n)[0]; hist[p] = tuple(a[k] for a in arr)
        nE = int(round(w * inner)); runs = []
        for p, cnt in (("MT5", nE), ("FT", inner - nE)):
            if cnt == 0: continue
            V12, B12, V18, B18, H12 = hist[p]; idx = stationary_idx(len(V12), cnt, H22); st, day = run(V12, B12, V18, B18, idx, catchup, H12, lock); runs.append((st, day))
        st = np.concatenate([r[0] for r in runs]); day = np.concatenate([r[1] for r in runs])
        res.append((np.mean((st == 1) & (day < H30)), np.mean((st == 1) & (day < H22)), np.mean((st == 2) & (day < H22)), np.median(day[st == 1]) + 1 if (st == 1).any() else np.nan, np.mean(st == 3)))
    r = np.array(res); lo, hi = np.nanpercentile(r, 2.5, axis=0), np.nanpercentile(r, 97.5, axis=0)
    return np.nanmean(r, axis=0), lo, hi


def main():
    print(f"Start: counted +{C0:.2f}; {H30} business days to 30 Nov, {H22} to 22 Dec; block bootstrap mean block 5; 200 outer x 2,000 inner paths", flush=True)
    for h in (1.0, 0.7, 0.5):
        P = pools(h)
        print(f"\n=== edge kept h = {h:.1f}  (pool means per day: 12M {P['MT5'][0].mean():+.0f} USD, 5Y {P['FT'][0].mean():+.0f} USD at x1.2)", flush=True)
        for w, lab in ((1.0, "12M regime only"), (0.5, "50/50 mix"), (0.0, "5Y regime only")):
            for catch in (False, True):
                m, lo, hi = estimate(P, w, catch)
                print(f"  {lab:16s} {'PLAN B (catch-up)' if catch else 'PLAN A (x1.2)    '}: pass by 30 Nov {100*m[0]:5.1f}% [{100*lo[0]:5.1f}-{100*hi[0]:5.1f}] | by 22 Dec {100*m[1]:5.1f}% [{100*lo[1]:5.1f}-{100*hi[1]:5.1f}] | breach by 22 Dec {100*m[2]:4.1f}% [{100*lo[2]:4.1f}-{100*hi[2]:4.1f}] | median pass day {m[3]:4.0f}", flush=True)


if __name__ == "__main__":
    main()
