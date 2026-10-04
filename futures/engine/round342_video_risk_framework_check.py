"""
Round 342 (2026-10-04, DESCRIPTIVE, no ledger row): check the 'optimal risk per trade' video (Monte Carlo of account tests: 40% win rate, 2:1 reward, 2 phases +10% / +5%, 10% max drawdown, $500 fee, $100K)
and apply its framework to the real MT5 broker numbers.
PART A: reproduce the video's example: fixed-fractional risk r of the INITIAL balance per trade (win +2r with p = 0.40, lose -r), static drawdown 10% from the initial balance, phase 1 target +10%, phase 2 target +5% (each phase restarts from 100K).
Reported per r: pass probability of both phases, trades per attempt, expected attempts (1 / p), expected cost (fee x attempts), expected trades to funding (trades per attempt / p, counting failures), the video's 'budget 90% of the time' (attempts needed for 90% confidence: ln(0.1)/ln(1-p)).
PART B: our case (MT5 1-Step, one try): fixed risk r of the balance per day on the real net R series (bootstrap, iid draws) of (1) the coin-flip direction on the US100 10:30 session table and (2) the 10:30 follow lead; target +10% (balance above 110,000), daily loss 3% (cannot bind at one trade a day while r < 3%), end-of-day trailing 10% floor, horizon 57 trading days.
"""
import os, sys
os.environ["ROUND_DATA"] = "mt5broker"; os.environ["ROUND_FILLS"] = "ask"
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", ".."))
rng = np.random.default_rng(342)

def phase(r, target, p=0.40, rr=2.0, dd=0.10, n=60000, cap=5000):
    """balance in units of the initial balance; returns pass flag and trades used."""
    bal = np.ones(n); trades = np.zeros(n); done = np.zeros(n, bool); ok = np.zeros(n, bool)
    for t in range(cap):
        alive = ~done
        if not alive.any(): break
        win = rng.random(n) < p
        bal = np.where(alive, bal + np.where(win, rr * r, -r), bal); trades += alive
        hit = alive & (bal >= 1 + target); lose = alive & (bal <= 1 - dd + 1e-9)
        ok |= hit; done |= hit | lose
    return ok, trades

print("PART A: the video's example (40% win, 2:1, 2 phases +10% / +5%, 10% static DD, $500 fee)")
print(f"{'risk':>5}{'pass P1':>9}{'pass both':>10}{'trades/attempt':>15}{'attempts E':>11}{'cost E':>8}{'trades to funding':>19}{'attempts for 90%':>17}")
for r in (0.005, 0.01, 0.02, 0.03, 0.04, 0.05):
    ok1, t1 = phase(r, 0.10); ok2, t2 = phase(r, 0.05)
    p1, p2 = ok1.mean(), ok2.mean(); p = p1 * p2
    tr = t1[ok1].mean() + t2[ok2].mean() if ok1.any() and ok2.any() else float("nan")
    tr_att = p1 * (t1[ok1].mean()) + (1 - p1) * t1[~ok1].mean() + p1 * (p2 * t2[ok2].mean() + (1 - p2) * t2[~ok2].mean()) if (~ok1).any() and (~ok2).any() else tr
    print(f"{r*100:>4.1f}%{p1*100:>8.0f}%{p*100:>9.0f}%{tr_att:>15.0f}{1/p:>11.2f}{500/p:>8.0f}{tr_att/p:>19.0f}{np.log(0.1)/np.log(1-p) if p < 1 else 1:>17.1f}")

print("\nPART B: MT5 1-Step on real net R (US100 10:30 table, k = 2.5), one trade a day, 57 trading days, fixed risk r")
import round324_post_open_drive_entry as Q
df = Q.day_table_T("NQ", Q.TS["1030"]); df = df[df.move != 0]
s = np.sign(df.move.values); Rl, Rs = df["R_1_2.5"].values, df["R_-1_2.5"].values
series = {"coin flip": np.r_[Rl, Rs], "follow lead": np.where(s > 0, Rl, Rs)}
print(f"mean net R: coin {series['coin flip'].mean():+.3f}, follow {series['follow lead'].mean():+.3f}")
def onestep(R, r, days=57, n=40000):
    bal = np.ones(n); hwm = np.ones(n); st = np.zeros(n, int)   # 0 open, 1 pass, 2 breach
    for d in range(days):
        a = st == 0
        pnl = R[rng.integers(0, len(R), n)] * r
        bal = np.where(a, bal + pnl * bal, bal)
        st = np.where(a & (bal >= 1.10), 1, st)
        breach = a & ((bal <= hwm - 0.10) | (pnl * 1.0 <= -0.03))
        st = np.where(breach & (st == 0), 2, st)
        hwm = np.maximum(hwm, np.where(st == 0, bal, hwm))
    return (st == 1).mean(), (st == 2).mean(), (st == 0).mean()
print(f"{'risk':>5}  " + "  ".join(f"{k:>34}" for k in series))
for r in (0.005, 0.01, 0.015, 0.02, 0.03, 0.04, 0.05):
    row = []
    for k, R in series.items():
        p, b, o = onestep(R, r); row.append(f"pass {p*100:4.1f}% breach {b*100:4.1f}% open {o*100:4.1f}%")
    print(f"{r*100:>4.1f}%  " + "  ".join(f"{x:>34}" for x in row))
