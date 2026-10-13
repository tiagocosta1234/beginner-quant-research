"""Can P(pass the MT5 Pro test) reach 70%, and by when? (the trader 2026-10-10 14:40: "precisamos de 70%, trabalha ate atingirmos um numero equivalente ou superior", after the answer that P(pass by 30 Oct) is about 4%.)
   python -m forex.ea_research.pass70
Written before any run of it. A planning simulation, not an edge trial: nothing here is tuned on the hold-out or claimed as a new edge.
State (live_state, 2026-10-10 14:40 local): counted closed profit +99.68; four gold longs floating +460.40 (NOT counted; they can still reverse).
Rules simulated (as live, test preset): guard loss cap 2,000 a day, the MT5 broker counted-profit rule min(day, 2,000), breach = in-day low <= -2,500 or equity <= 92,000,
pass = counted profit >= 8,000 at a day end or the counted-equity pass lock (counted + min(day high, 2,000) >= 8,100), and the NO-HEDGE rule (a trade opened while an opposite position is open is skipped: the guard closes it within a second).
Pools (clean_boot_lib): MT5 = last 12 months on MT5 broker real ticks (gold in a strong trend), FT = 2022-26 MT5 broker trades scaled to MT5 broker prices; MIX = 50/50. Days are drawn by a stationary block bootstrap (mean block 5 days).
P1  ceiling by 30 Oct (15 business days, Mon 12 .. Fri 30 Oct): dynamic programming over (day, counted profit) choosing every day a size in MULTS; lambda = 0 (breach not penalised: the absolute maximum for this edge), 0.3, 1.0.
P2  the same ceiling for 30 Nov (36 business days) and 22 Dec (52 business days).
P3  the pass curve at constant sizes (x1.2 is live): P(pass by business day d) up to one year; the first day with >= 70% per pool and for the mix.
P4  what edge 70% by each date would need: every day of the x1.2 series shifted up by delta USD (same day-to-day variability, the guard still floors a day at -2,000); the delta that gives 70% per pool;
    and the bound for ANY zero-edge strategy (optional stopping: P <= (start + loss room) / (target + loss room)).
Caveats written now: in-sample pools flattered by the 2025-26 gold trend; sizes above x1.2 exceed MT5 broker's '1% risk per trade idea' guideline (SDB 1.14% per trade at x1.2), so every dynamic policy is shown as a ceiling, not as a proposal."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np

from forex.ea_research import clean_boot_lib as L
from forex.ea_batch.mt5_mc_config import CH

A, CAPD, TARGET = L.A, L.CAPD, L.TARGET
LOCK = 8100.0
C0 = 99.68
MULTS = (1.0, 1.2, 1.5, 1.8, 2.5, 3.5, 5.0)
I12 = MULTS.index(1.2)
HORIZONS = {"30 Oct": 15, "30 Nov": 36, "22 Dec": 52}
STEP = 100.0
GRID = np.arange(-8000.0, 8000.0 + STEP, STEP)
START_DAY = np.datetime64("2026-10-12")
RNG = np.random.default_rng(20261010)
OUT = Path(__file__).resolve().parent / "PASS70_OUTPUT.txt"


def say(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True)
    with open(OUT, "a", encoding="utf-8") as f: f.write(s + "\n")


# ---------------------------------------------------------------- series with the no-hedge rule
def nohedge(tr: dict) -> tuple[dict, float]:
    o = np.argsort(tr["in_s"], kind="stable"); tr = {k: v[o] for k, v in tr.items()}; n = len(tr["in_s"]); keep = np.zeros(n, bool)
    for j in range(n):
        t = tr["in_s"][j]; clash = keep & (tr["in_s"] <= t) & (tr["out_s"] > t) & (tr["side"] != tr["side"][j])
        keep[j] = not clash.any()
    return {k: v[keep] for k, v in tr.items()}, 1.0 - keep.mean()


def series_nh(pool: str, mult: float) -> dict:
    f = L.CACHE / f"{pool}_{mult}_NOHEDGE_C.npz"
    if f.exists():
        z = np.load(f, allow_pickle=True); return {k: z[k] for k in z.files}
    src, a, b = L.POOLS[pool]; lo, hi = L.day(a), L.day(b)
    s = L.ea_trades(src, "sdb", CH["sdb"] * mult, lo); x = L.ea_trades(src, "xau5", CH["xau5"] * mult, lo); tr, drop = nohedge(L.merge(s, x))
    r = L.C.simulate(L.bars(), tr, lo, hi, None, CAPD)
    out = dict(V=r["V"], B=r["B"], Hi=r["Hi"], days=r["days"], drop=np.array([drop])); np.savez(f, **out); return out


# ---------------------------------------------------------------- dynamic programming and simulation
def counted(c, V):
    return c + np.where(V > 0, np.minimum(V, CAPD), V)


def dp(S_by_pool: list, weights, lam: float, H: int):
    nS = len(GRID); W = np.zeros((H + 1, nS)); pol = np.zeros((H, nS), int); c = GRID[:, None]
    for j in range(H - 1, -1, -1):
        best = np.full(nS, -1e9); arg = np.zeros(nS, int)
        for a in range(len(MULTS)):
            val = np.zeros(nS)
            for w, S in zip(weights, S_by_pool):
                if w == 0: continue
                V, B, Hi = S[a]["V"][None, :], S[a]["B"][None, :], S[a]["Hi"][None, :]
                breach = (B <= -0.025 * A) | (A + c + B <= 0.92 * A); cn = counted(c, V)
                win = (c + np.minimum(Hi, CAPD) >= LOCK) | (cn >= TARGET); idx = np.clip(np.rint((cn - GRID[0]) / STEP).astype(int), 0, nS - 1)
                val += w * np.where(breach, -lam, np.where(win, 1.0, W[j + 1][idx])).mean(axis=1)
            better = val > best; best = np.where(better, val, best); arg = np.where(better, a, arg)
        W[j] = best; pol[j] = arg
    return pol, W


def stationary_idx(n: int, paths: int, H: int, mean_block: float = 5.0):
    idx = np.empty((paths, H), dtype=np.int64); idx[:, 0] = RNG.integers(0, n, paths); jump = RNG.random((paths, H)) < 1.0 / mean_block; new = RNG.integers(0, n, (paths, H))
    for j in range(1, H):
        idx[:, j] = np.where(jump[:, j], new[:, j], (idx[:, j - 1] + 1) % n)
    return idx


def simulate(S: list, policy, H: int, paths: int = 20000, shift: float = 0.0, after: int = I12):
    """S: series per multiplier for ONE pool. policy: an int (constant multiplier index) or a DP table used for len(policy) days, then 'after'. Returns pass day / breach day arrays (-1 = none)."""
    n = len(S[0]["V"]); idx = stationary_idx(n, paths, H); cnt = np.full(paths, C0); st = np.zeros(paths, np.int8); day = np.full(paths, -1)
    for j in range(H):
        if isinstance(policy, (int, np.integer)): a = np.full(paths, int(policy))
        elif j < len(policy): a = policy[j][np.clip(np.rint((cnt - GRID[0]) / STEP).astype(int), 0, len(GRID) - 1)]
        else: a = np.full(paths, after)
        V = np.empty(paths); B = np.empty(paths); Hi = np.empty(paths)
        for k in range(len(MULTS)):
            m = a == k
            if m.any(): V[m], B[m], Hi[m] = S[k]["V"][idx[m, j]], S[k]["B"][idx[m, j]], S[k]["Hi"][idx[m, j]]
        if shift:
            V = np.maximum(V + shift, -CAPD); B = np.maximum(B + shift, -2100.0); Hi = np.maximum(Hi + shift, 0.0)
        act = st == 0; br = act & ((B <= -0.025 * A) | (A + cnt + B <= 0.92 * A)); st = np.where(br, 2, st); day = np.where(br, j, day); act = st == 0
        lk = act & (cnt + np.minimum(Hi, CAPD) >= LOCK); st = np.where(lk, 1, st); day = np.where(lk, j, day); act = st == 0
        cnt = np.where(act, counted(cnt, V), cnt); ps = act & (cnt >= TARGET); st = np.where(ps, 1, st); day = np.where(ps, j, day)
    return st, day


def p_by(st, day, H):
    return float(np.mean((st == 1) & (day < H))), float(np.mean((st == 2) & (day < H)))


def bday(d: int) -> str:
    return str(np.busday_offset(START_DAY, d - 1, roll="forward"))


def main():
    OUT.write_text(f"pass70 run {dt.datetime.now():%Y-%m-%d %H:%M} (local clock)\n", encoding="utf-8")
    pools = {}
    for p in ("MT5", "FT"):
        pools[p] = [series_nh(p, m) for m in MULTS]
        say(f"pool {p}: {len(pools[p][0]['V'])} days | trades skipped by the no-hedge rule {100*float(pools[p][I12]['drop'][0]):.1f}% | mean day USD by size {[round(float(s['V'].mean())) for s in pools[p]]} | sd at x1.2 {float(pools[p][I12]['V'].std()):.0f}")
    say("\n== P3 first: constant sizes, the pass curve (no-hedge, loss cap, counted cap, pass lock), up to 260 business days from Mon 12 Oct ==")
    curves = {}
    for k, m in enumerate(MULTS[:4]):
        row = {}
        for p in ("MT5", "FT"):
            st, day = simulate(pools[p], k, 260); row[p] = (st, day)
        curves[m] = row
        cum = {p: np.array([p_by(*row[p], d)[0] for d in range(1, 261)]) for p in ("MT5", "FT")}; mix = 0.5 * (cum["MT5"] + cum["FT"])
        brc = {p: p_by(*row[p], 260)[1] for p in ("MT5", "FT")}
        first = {nm: (int(np.argmax(c >= 0.70)) + 1 if (c >= 0.70).any() else None) for nm, c in (("12M", cum["MT5"]), ("2022-26", cum["FT"]), ("MIX", mix))}
        dl = " | ".join(f"{nm} {('day %d = %s' % (d, bday(d))) if d else 'never within a year'}" for nm, d in first.items())
        say(f"x{m}: P(pass) by 30 Oct / 30 Nov / 22 Dec: 12M {[round(100*cum['MT5'][h-1],1) for h in HORIZONS.values()]} | 2022-26 {[round(100*cum['FT'][h-1],1) for h in HORIZONS.values()]} | MIX {[round(100*mix[h-1],1) for h in HORIZONS.values()]} | breach within a year 12M {100*brc['MT5']:.1f}% 2022-26 {100*brc['FT']:.1f}%")
        say(f"      first business day with P >= 70%: {dl}")
    say("\n== P1 / P2: the ceiling with ANY size every day (dynamic programming), by deadline ==")
    for name, H in HORIZONS.items():
        say(f"-- deadline {name} ({H} business days)")
        for design, w in (("MIX", (0.5, 0.5)), ("12M", (1.0, 0.0)), ("2022-26", (0.0, 1.0))):
            for lam in (0.0, 0.3, 1.0):
                pol, W = dp([pools["MT5"], pools["FT"]], w, lam, H)
                r = {p: p_by(*simulate(pools[p], pol, H), H) for p in ("MT5", "FT")}
                say(f"   policy designed on {design:7s} lambda {lam:3.1f}: 12M pass {100*r['MT5'][0]:5.1f}% breach {100*r['MT5'][1]:5.1f}% | 2022-26 pass {100*r['FT'][0]:5.1f}% breach {100*r['FT'][1]:5.1f}% | MIX pass {50*(r['MT5'][0]+r['FT'][0]):5.1f}% breach {50*(r['MT5'][1]+r['FT'][1]):5.1f}%")
    say("\n== P4: the edge 70% would need, at the live size x1.2 (every day shifted up by delta USD, same variability) ==")
    for name, H in HORIZONS.items():
        out = []
        for p in ("MT5", "FT"):
            lo, hi = 0.0, 4000.0
            for _ in range(14):
                mid = 0.5 * (lo + hi); pp = p_by(*simulate(pools[p], I12, H, paths=8000, shift=mid), H)[0]
                lo, hi = (mid, hi) if pp < 0.70 else (lo, mid)
            V = pools[p][I12]["V"]; mean = float(V.mean()); sd = float(V.std())
            out.append(f"{'12M' if p == 'MT5' else '2022-26'}: +{hi:,.0f} USD/day -> mean day {mean + hi:,.0f} vs {mean:,.0f} now ({(mean + hi) / max(mean, 1):.1f}x), daily Sharpe {(mean + hi) / sd:.2f} vs {mean / sd:.2f} now")
        say(f"  70% by {name}: " + " | ".join(out))
    for nm, F in (("MT5 broker static floor 92,000", 8000.0), ("our guard floor 6.5%", 6500.0)):
        say(f"  zero-edge bound (optional stopping, no deadline), loss room = {nm}: P(pass) <= ({C0:.0f} + {F:,.0f}) / (8,000 + {F:,.0f}) = {100*(C0 + F)/(TARGET + F):.1f}%")


if __name__ == "__main__":
    main()
