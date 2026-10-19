"""Power of the blind-replay decision rule (PREREG_BLIND2026.md), simulated on MT5 2023-25 prices (nothing from 2026 is read).
World: random London entry minute (10:01-10:15 server), stop/target distances drawn from his 17 London trades (target = 0.525 x stop), both sides replayed on MT5 broker bid/ask.
Skill s: with probability s he picks the side that wins at that entry, otherwise a random side. Rule: mean R >= +0.10 and P(random side >= his mean) <= 0.05 (normal approximation of the permutation test)."""
import numpy as np, pandas as pd
from blind_score import load_days, run, CLOSE_HM
rng = np.random.default_rng(3); days = load_days("2023-01-01", "2025-12-31"); keys = [k for k in days if k.weekday() < 5 and len(days[k]) > 600]
O = pd.read_csv("replay_mt5.csv"); risks = O[O.ses == "London"].risk.to_numpy(); pairs = []
for _ in range(6000):
    g = days[keys[rng.integers(len(keys))]]; idx = g.index[(g.hm >= 601) & (g.hm <= 615)]
    if len(idx) < 10: continue
    i0 = int(rng.choice(idx)); rk = float(rng.choice(risks)); pairs.append((run(g, i0, "L", rk, 0.525 * rk, CLOSE_HM["London"]), run(g, i0, "S", rk, 0.525 * rk, CLOSE_HM["London"])))
P = np.array(pairs); RL, RS = P[:, 0], P[:, 1]; print("pairs %d | random-side mean R %+.3f | share where L wins %.2f, S wins %.2f, both win %.2f, both lose %.2f" % (
    len(P), ((RL + RS) / 2).mean(), (RL > 0).mean(), (RS > 0).mean(), ((RL > 0) & (RS > 0)).mean(), ((RL < 0) & (RS < 0)).mean()))
better = np.where(RL > RS, RL, np.where(RS > RL, RS, np.where(rng.random(len(P)) < .5, RL, RS)))
def exper(s, n, trials=4000):
    ok = 0; mean_all = []
    for _ in range(trials):
        i = rng.integers(len(P), size=n); pick = np.where(rng.random(n) < s, better[i], np.where(rng.random(n) < .5, RL[i], RS[i]))
        m = pick.mean(); mu = ((RL[i] + RS[i]) / 2).mean(); sd = np.sqrt(((RL[i] - RS[i]) ** 2).sum() / 4) / n
        ok += (m >= 0.10) and ((m - mu) / sd >= 1.645); mean_all.append(m)
    return ok / trials, float(np.mean(mean_all))
def futility(s, n=18, trials=4000):
    """stop after batch 1: raw rule (mean R < 0) and the amended rule (mean R minus the random-side mean on the same entries < +0.05)"""
    raw = exc = 0
    for _ in range(trials):
        i = rng.integers(len(P), size=n); pick = np.where(rng.random(n) < s, better[i], np.where(rng.random(n) < .5, RL[i], RS[i]))
        raw += pick.mean() < 0; exc += (pick.mean() - ((RL[i] + RS[i]) / 2).mean()) < 0.05
    return raw / trials, exc / trials
print("skill s | expected mean R of his side | P(supported) at n=35 | at n=25 | at n=45 | P(stop after 18 trades): raw rule mean R < 0 | amended rule excess over random side < +0.05")
for s in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8):
    p35, m = exper(s, 35); p25, _ = exper(s, 25); p45, _ = exper(s, 45)
    f_raw, f_exc = futility(s); print("  %.1f | %+.3f | %.2f | %.2f | %.2f | %.2f | %.2f" % (s, m, p35, p25, p45, f_raw, f_exc))
