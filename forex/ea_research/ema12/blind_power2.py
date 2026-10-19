"""Power of the two-look blind-replay design (PREREG_BLIND2026 Amendment 2) against the single-look design of the first draft. python blind_power2.py
Same null world as blind_power.py (MT5 2023-25 prices, random London entry minutes, his stop/target distances, random side averages -0.05 R). Blocks of scorable trades: Jan 2026 18, sealed batch 26, two extension windows 18 + 18 (cumulative 18 / 44 / 62 / 80).
Design 1 (first draft): futility after Jan (excess < +0.05), one read at n = 44: supported iff mean R >= +0.10 and z >= 1.645 (P <= 0.05).
Design 2 (Amendment 2): the same futility; Look 1 at n = 44 and Look 2 at n = 80, each: supported iff mean R >= +0.10 and z >= 1.875 (P <= 0.0304, Pocock for two looks at one-sided 0.05); stop at Look 1 for futility (excess < +0.05)."""
import numpy as np, pandas as pd
from blind_score import load_days, run, CLOSE_HM
rng = np.random.default_rng(7); days = load_days("2023-01-01", "2025-12-31"); keys = [k for k in days if k.weekday() < 5 and len(days[k]) > 600]
O = pd.read_csv("replay_mt5.csv"); risks = O[O.ses == "London"].risk.to_numpy(); pairs = []
for _ in range(6000):
    g = days[keys[rng.integers(len(keys))]]; idx = g.index[(g.hm >= 601) & (g.hm <= 615)]
    if len(idx) < 10: continue
    i0 = int(rng.choice(idx)); rk = float(rng.choice(risks)); pairs.append((run(g, i0, "L", rk, 0.525 * rk, CLOSE_HM["London"]), run(g, i0, "S", rk, 0.525 * rk, CLOSE_HM["London"])))
P = np.array(pairs); RL, RS = P[:, 0], P[:, 1]
better = np.where(RL > RS, RL, np.where(RS > RL, RS, np.where(rng.random(len(P)) < .5, RL, RS)))
def stats(i, pick, n):
    j = slice(0, n); m = pick[j].mean(); mu = ((RL[i[j]] + RS[i[j]]) / 2).mean(); sd = np.sqrt(((RL[i[j]] - RS[i[j]]) ** 2).sum() / 4) / n
    return m, m - mu, (m - mu) / sd
def sim(s, trials=6000):
    out = dict(d1=0, d2_l1=0, d2_l2=0, fut_jan=0, fut_l1=0, trades1=0, trades2=0)
    for _ in range(trials):
        i = rng.integers(len(P), size=80); pick = np.where(rng.random(80) < s, better[i], np.where(rng.random(80) < .5, RL[i], RS[i]))
        m18, e18, _z = stats(i, pick, 18); m44, e44, z44 = stats(i, pick, 44); m80, e80, z80 = stats(i, pick, 80)
        if e18 < 0.05: out["fut_jan"] += 1; out["trades1"] += 18; out["trades2"] += 18; continue
        out["d1"] += (m44 >= 0.10) and (z44 >= 1.645); out["trades1"] += 44
        if (m44 >= 0.10) and (z44 >= 1.875): out["d2_l1"] += 1; out["trades2"] += 44; continue
        if e44 < 0.05: out["fut_l1"] += 1; out["trades2"] += 44; continue
        out["trades2"] += 80; out["d2_l2"] += (m80 >= 0.10) and (z80 >= 1.875)
    return {k: v / trials for k, v in out.items()}
print("expected mean R of his side | design 1: P(supported), trades | design 2: P(supported at Look 1), P(supported at Look 2), overall, P(futility stop after Jan), P(futility stop at Look 1), trades")
for s in (0.0, 0.2, 0.3, 0.4, 0.5, 0.6):
    i = rng.integers(len(P), size=200000); pick = np.where(rng.random(200000) < s, better[i], np.where(rng.random(200000) < .5, RL[i], RS[i])); r = sim(s)
    print("  %+.2f | %.2f, %.0f | %.2f, %.2f, %.2f, %.2f, %.2f, %.0f" % (pick.mean(), r["d1"], r["trades1"], r["d2_l1"], r["d2_l2"], r["d2_l1"] + r["d2_l2"], r["fut_jan"], r["fut_l1"], r["trades2"]))
