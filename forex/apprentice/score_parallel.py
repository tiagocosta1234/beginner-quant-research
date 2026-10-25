"""Score PARALLEL_LOG.csv per PREREG_PARALLEL_FORWARD.md + AMENDMENT1. Read-only.  Usage: python score_parallel.py [log.csv]"""
import csv, math, sys
from collections import defaultdict
import numpy as np

COST = {"MGC": 0.32, "MNQ": 1.1, "MES": 0.74, "MYM": 4.4}
path = sys.argv[1] if len(sys.argv) > 1 else "PARALLEL_LOG.csv"


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


A, B, M = defaultdict(list), defaultdict(list), defaultdict(list)
with open(path, newline="", encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        a, c = f(r["a_R_net"]), f(r["claude_R_net"])
        if a is None:
            continue
        risk = abs((f(r["a_entry"]) or 0) - (f(r["a_stop"]) or 0))
        cost = COST.get(r["symbol"], 0.0)
        A[r["date"]].append(a)
        M[r["date"]].append(-a - 2 * cost / risk if risk > 0 else -a)
        if c is not None:
            B[r["date"]].append(c)

days = sorted(A)
n = len(days)
print(f"days logged: {n} of 40")
if n < 2:
    print("not enough days yet")
    sys.exit(0)
a = np.array([np.mean(A[d]) for d in days]); m = np.array([np.mean(M[d]) for d in days])
rng = np.random.default_rng(20261026)
flip = rng.random((20000, n)) < 0.5
p = float((np.where(flip, m, a).mean(axis=1) >= a.mean()).mean())
se = a.std(ddof=1) / math.sqrt(n)
print(f"track A: mean daily net R {a.mean():+.3f}  SE {se:.3f}  random-side P {p:.4f}  symbols/day {np.mean([len(A[d]) for d in days]):.1f}")
if B:
    b = np.array([np.mean(B[d]) for d in sorted(B)])
    print(f"track B (Claude): mean daily net R {b.mean():+.3f} over {len(b)} days")
if n >= 20 and a.mean() >= 0.45 and p <= 0.02:
    print("GATE: EARLY PASS (day-20 rule): the trader may buy ONE account")
elif n >= 20 and a.mean() <= -0.40:
    print("GATE: EARLY STOP: drop the indicator")
elif n >= 40 and a.mean() >= 0.25 and p <= 0.05:
    print("GATE: PASS (day-40 rule): the trader may buy ONE account")
elif n >= 40:
    print("GATE: NOT MET: no purchase on this indicator")
else:
    print("GATE: not decided yet" + (" (past day 20 without an early result: continue to day 40)" if n >= 20 else ""))
