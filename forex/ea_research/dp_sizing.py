"""Optimal DYNAMIC sizing of the pair for the MT5 broker test deadline (the trader 2026-10-10: "the chance is still too low, keep studying").
   python -m forex.ea_research.dp_sizing
Question: instead of a constant size, which multiplier m (x1.2, x1.8, x2.5, x3.5, x5.0 of the locked lots) should be traded each day as a function of the day and the counted profit so far, to maximise P(pass by 30 Oct) (15 business days from Mon 12 Oct), with a penalty for breach?
Model: backward induction (dynamic programming) over (days left, counted profit in 100 USD bins) with the EMPIRICAL guarded daily results of the pair at each multiplier (clean_boot_lib series: V = day result with the 2,000 loss cap, B = in-day low, Hi = in-day high; days resampled i.i.d. from the pool: 12-month MT5 broker pool, 2022-26 pool, or a 50/50 mix). Pass = counted profit >= 8,000 at a day end, or the cap-aware lock (counted profit + min(day high, 2,000) >= 8,100); breach = in-day low <= -2,500 or equity <= 92,000; counted profit adds min(day, 2,000) when positive. Objective: P(pass) - lambda x P(breach).
Then each optimal policy is EVALUATED by block-bootstrap simulation (mean block 5, so the autocorrelation of the real days is kept) and compared with the constant sizes; after day 15 the evaluation continues at x1.2 to 22 Dec to see what the aggressive month costs later. Approximations: the multipliers are rebuilt from the trades, so a size change is assumed to apply to all positions of the day; the guard acts at -2,000 at every size."""
from __future__ import annotations

import numpy as np

from forex.ea_research import clean_boot_lib as L
from forex.ea_research import clean_bootstrap as BS

A, CAPD, TARGET = BS.A, BS.CAPD, BS.TARGET
MULTS = (1.2, 1.8, 2.5, 3.5, 5.0)
H1, H2, C0 = 15, 52, 99.68
STEP = 100.0
GRID = np.arange(-8000.0, 8000.0 + STEP, STEP)


def load(pool):
    return [L.series(pool, m) for m in MULTS]


def dp(series_list, weights, lam):
    """series_list: list over pools of (list over multipliers of series dicts); weights: pool weights. Returns policy[j][c_idx] = multiplier index and value."""
    nS = len(GRID); W = np.zeros((H1 + 1, nS)); pol = np.zeros((H1, nS), int)
    for j in range(H1 - 1, -1, -1):
        best = np.full(nS, -1e9); arg = np.zeros(nS, int)
        for a in range(len(MULTS)):
            val = np.zeros(nS)
            for w, S in zip(weights, series_list):
                V, B, Hi = S[a]["V"], S[a]["B"], S[a]["Hi"]; n = len(V)
                c = GRID[:, None]; breach = (B[None, :] <= -0.025 * A) | (A + c + B[None, :] <= 0.92 * A)
                lock = (c + np.minimum(Hi[None, :], CAPD) >= 8100.0) | (c + np.where(V[None, :] > 0, np.minimum(V[None, :], CAPD), V[None, :]) >= TARGET)
                cn = c + np.where(V[None, :] > 0, np.minimum(V[None, :], CAPD), V[None, :]); idx = np.clip(np.rint((cn - GRID[0]) / STEP).astype(int), 0, nS - 1)
                cont = W[j + 1][idx]; r = np.where(breach, -lam, np.where(lock, 1.0, cont)); val += w * r.mean(axis=1)
            better = val > best; best = np.where(better, val, best); arg = np.where(better, a, arg)
        W[j] = best; pol[j] = arg
    return pol, W


def simulate(series_by_pool_mult, pool, policy, paths=20000, H=H2, mult_after=0):
    S = series_by_pool_mult[pool]; n = len(S[0]["V"]); idx = BS.stationary_idx(n, paths, H); cnt = np.full(paths, C0); st = np.zeros(paths, np.int8); day = np.full(paths, -1)
    for j in range(H):
        if isinstance(policy, (int, np.integer)):
            a = np.full(paths, int(policy))
        else:
            ci = np.clip(np.rint((cnt - GRID[0]) / STEP).astype(int), 0, len(GRID) - 1); a = policy[j][ci] if j < H1 else np.zeros(paths, int)       # after day 15 the dynamic policy falls back to x1.2
        V = np.empty(paths); B = np.empty(paths); Hi = np.empty(paths)
        for k in range(len(MULTS)):
            m = a == k
            if m.any(): V[m], B[m], Hi[m] = S[k]["V"][idx[m, j]], S[k]["B"][idx[m, j]], S[k]["Hi"][idx[m, j]]
        act = st == 0; br = act & ((B <= -0.025 * A) | (A + cnt + B <= 0.92 * A)); st = np.where(br, 2, st); day = np.where(br, j, day); act = st == 0
        lk = act & ((cnt + np.minimum(Hi, CAPD) >= 8100.0)); st = np.where(lk, 1, st); day = np.where(lk, j, day); act = st == 0
        cnt = np.where(act, cnt + np.where(V > 0, np.minimum(V, CAPD), V), cnt); ps = act & (cnt >= TARGET); st = np.where(ps, 1, st); day = np.where(ps, j, day)
    return np.mean((st == 1) & (day < H1)), np.mean((st == 2) & (day < H1)), np.mean((st == 1) & (day < H)), np.mean(st == 2)


def main():
    pools = {"MT5": load("MT5"), "FT": load("FT")}; print("pool day counts:", {k: len(v[0]["V"]) for k, v in pools.items()})
    print("mean day USD by multiplier (12M pool):", [round(float(s["V"].mean())) for s in pools["MT5"]], "| (2022-26 pool):", [round(float(s["V"].mean())) for s in pools["FT"]])
    for mix_name, weights in (("50/50 mix", (0.5, 0.5)), ("12M regime only", (1.0, 0.0)), ("2022-26 regime only", (0.0, 1.0))):
        print(f"\n######## policy designed on: {mix_name}")
        for lam in (0.0, 0.3, 1.0):
            pol, W = dp([pools["MT5"], pools["FT"]], weights, lam)
            ci = int(round((C0 - GRID[0]) / STEP)); print(f"  lambda {lam}: DP value at the start {W[0][ci]:+.3f}")
            for nm, pool in (("12M", "MT5"), ("2022-26", "FT")):
                r = simulate(pools, pool, pol); print(f"     evaluated on {nm:8s}: pass by 30 Oct {100*r[0]:5.1f}% | breach by 30 Oct {100*r[1]:4.1f}% | then x1.2 to 22 Dec: pass {100*r[2]:5.1f}% breach {100*r[3]:4.1f}%")
            if lam == 0.3 and mix_name == "50/50 mix":
                print("     policy (multiplier chosen) by day and counted profit:")
                for j in (0, 3, 6, 9, 12, 14):
                    print(f"       day {j+1:2d}: " + " ".join(f"{int(c):>6d}:x{MULTS[pol[j][int(round((c - GRID[0]) / STEP))]]}" for c in (-2000, 0, 1000, 2000, 3000, 4000, 5000, 6000, 7000)))
        print(f"  constant sizes for comparison ({mix_name}):")
        for a, m in enumerate(MULTS):
            parts = [simulate(pools, pool, a) for pool in ("MT5", "FT")]; w = weights
            print(f"     x{m}: pass by 30 Oct {100*(w[0]*parts[0][0]+w[1]*parts[1][0]):5.1f}% | breach {100*(w[0]*parts[0][1]+w[1]*parts[1][1]):4.1f}% | at x{m} to 22 Dec: pass {100*(w[0]*parts[0][2]+w[1]*parts[1][2]):5.1f}% breach {100*(w[0]*parts[0][3]+w[1]*parts[1][3]):4.1f}%")


if __name__ == "__main__":
    main()
