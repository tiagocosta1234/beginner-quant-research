"""Upper bound of P(pass by 30 Oct 2026) under MT5 Pro rules for ANY daily strategy (dynamic programming over the balance).
Each day the trader picks a two-outcome day: win +g (g <= 2,000 counted) or lose -L (L <= 2,400, under the 2,500 hard line),
with win probability set by the edge: p*g - (1-p)*L = edge * L. Optimal choice per state; floor 92,000 static; target 108,000.
   python -m forex.ea_research.pass_ceiling_oct"""
import numpy as np

STEP = 100
START, TARGET, FLOOR = 97_700, 108_000, 92_000
G = np.arange(STEP, 2001, STEP); L = np.arange(STEP, 2401, STEP)


def ceiling(days, edge):
    n = (TARGET - FLOOR) // STEP
    V = np.zeros(n + 1); V[n] = 1.0                           # value after the last day: passed or not
    for _ in range(days):
        W = V.copy()
        for i in range(1, n):
            best = V[i]                                       # option: do not trade
            for g in G:
                up = min(n, i + g // STEP)
                for l in L:
                    p = (edge * l + l) / (g + l)
                    if p >= 1: continue
                    dn = i - l // STEP
                    v = p * V[up] + (1 - p) * (V[dn] if dn > 0 else 0.0)
                    if v > best: best = v
            W[i] = best
        V = W
    return V[(START - FLOOR) // STEP]


if __name__ == "__main__":
    for days in (11,):
        for edge in (0.0, 0.05, 0.10, 0.20, 0.30):
            print(f"{days} trading days (16-30 Oct), edge {edge:.2f} R a day: max P(pass) = {ceiling(days, edge):.1%}")
