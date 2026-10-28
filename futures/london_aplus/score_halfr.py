"""Score the FX Replay half-R test. Usage: py score_halfr.py HALFR_LOG.csv --risk 1000
CSV needs a result column in USD (pnl / profit / net_pnl / result_usd) and optionally 'date'. R = result / risk."""
import sys, math, csv
import numpy as np

BASELINE = 0.65          # random 0.5R bracket win rate (HALF_R_GROSS_OUTPUT.txt)
WIN_BAR, N_BAR, P_BAR = 0.74, 200, 0.05
COLS = ("pnl", "profit", "net_pnl", "result_usd", "result")

path = sys.argv[1]
risk = float(sys.argv[sys.argv.index("--risk") + 1]) if "--risk" in sys.argv else 1000.0
rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
col = next((c for c in rows[0] if c.strip().lower() in COLS), None) if rows else None
if col is None:
    sys.exit("no result column found; expected one of " + ", ".join(COLS))
usd = np.array([float(str(r[col]).replace("$", "").replace(",", "")) for r in rows if str(r[col]).strip() not in ("", "nan")])
cost_r = float(sys.argv[sys.argv.index("--cost-r") + 1]) if "--cost-r" in sys.argv else 0.05   # FX Replay has no fees: subtract 0.05 R a trade
R = usd / risk - cost_r
n = len(R)
if n < 2:
    sys.exit("need at least 2 trades")
wins = int((R > 0).sum())
rng = np.random.default_rng(20261027)
boot = rng.choice(R, size=(10000, n), replace=True).mean(axis=1)
p_boot = float((boot <= 0).mean())
lo, hi = np.percentile(boot, [2.5, 97.5])
p_binom = sum(math.comb(n, k) * BASELINE ** k * (1 - BASELINE) ** (n - k) for k in range(wins, n + 1))
print(f"trades {n}  wins {wins}  win rate {wins / n:.1%}  mean R {R.mean():+.3f}  total {usd.sum():+,.0f} USD")
print(f"95% interval of mean R: {lo:+.3f} .. {hi:+.3f}   P(mean R <= 0) {p_boot:.3f}")
print(f"win rate vs {BASELINE:.0%} random 0.5R baseline: exact binomial P {p_binom:.3f}")
for i in range(0, n, 100):
    blk = R[i:i + 100]
    print(f"  block {i // 100 + 1}: n {len(blk)}  win {(blk > 0).mean():.1%}  mean R {blk.mean():+.3f}")
if n < N_BAR:
    print(f"VERDICT: not yet (n {n} < {N_BAR}); progress read only")
else:
    ok = wins / n >= WIN_BAR and R.mean() > 0 and p_boot <= P_BAR
    print("VERDICT:", "SUPPORTED (a lead, not a licence)" if ok else "NOT SHOWN")
