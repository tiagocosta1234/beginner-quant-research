"""Checks every number in docs/statistics.md by formula and by simulation:  python docs/check_statistics.py"""
import numpy as np
from scipy.stats import norm

rng = np.random.default_rng(7)


def hit_target_first(k, paths=40_000, step=0.02):
    """Share of driftless random walks that reach +k before -1 (both in units of the stop)."""
    x = np.zeros(paths)
    alive = np.ones(paths, dtype=bool)
    won = np.zeros(paths, dtype=bool)
    while alive.any():
        x[alive] += rng.normal(0, step, alive.sum())
        up, down = alive & (x >= k), alive & (x <= -1)
        won |= up
        alive &= ~(up | down)
    return won.mean()


print("1. Win rate of a random walk with a stop of 1R and a target of kR")
for k in (0.5, 1.0, 2.0):
    print(f"   k={k}: formula 1/(1+k) = {1 / (1 + k):.3f}, simulated {hit_target_first(k):.3f}")
c = 0.11
print(f"   break-even win rate at k=0.5 with costs of {c}R: (1+c)/(1+k) = {(1 + c) / 1.5:.3f}")

print("\n2. Many tests on pure noise")
m, alpha, days = 200, 0.05, 250
print(f"   chance of at least one false pass in {m} tests at 5%: {1 - (1 - alpha) ** m:.5f}")
r = rng.normal(0, 1, size=(m, days))
t = r.mean(axis=1) / r.std(axis=1, ddof=1) * np.sqrt(days)
print(f"   simulated: {int((t > norm.ppf(1 - alpha)).sum())} of {m} noise strategies have t above {norm.ppf(1 - alpha):.3f}")
print(f"   one-sided bar for 4 variants at 5% overall (Bonferroni): {norm.ppf(1 - alpha / 4):.2f}")

print("\n3. How much a Sharpe ratio can be trusted")
for sr, years in ((0.9, 0.75), (0.9, 1.0), (0.87, 16.8)):
    print(f"   Sharpe {sr} over {years} years: standard error about 1/sqrt(years) = {1 / np.sqrt(years):.2f}, t = {sr * np.sqrt(years):.2f}")
print(f"   chance a true-Sharpe-0.9 strategy loses money in a given year: {norm.cdf(-0.9):.3f}")
yearly = rng.normal(0.9 / np.sqrt(252), 1, size=(20_000, 252)).sum(axis=1)
print(f"   simulated: {(yearly < 0).mean():.3f}")
