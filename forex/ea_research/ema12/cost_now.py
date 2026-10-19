"""the trader's 30 trades (MT5 broker replay, Apr-May 2025 spread 0.28) re-costed for today's gold: spread 0.47 plus slippage s on the entry (market) and on stop exits; targets are limits (no slippage).
Then the 1-trade-a-day Monte Carlo. python cost_now.py"""
import numpy as np, pandas as pd
O = pd.read_csv("replay_mt5.csv"); M = pd.read_csv("mae_mt5.csv").merge(O[["k", "risk", "rew"]], on="k")
SP0, SPN = 0.28, 0.47
def adj(R_base_win, rr, risk, win, s, spread_now=SPN):
    d = spread_now - SP0
    return np.where(win, rr - (d + s) / risk, -1.0 - (d + 2 * s) / risk)
win = (M.res == "W").to_numpy()
print("30 trades, MT5 broker bid/ask replay re-costed: mean R, t, break-even win rate (average risk $%.2f, reward $%.2f)" % (M.risk.mean(), M.rew.mean()))
for sp in (SP0, SPN):
    for s in (0.0, 0.25, 0.5, 0.75, 1.0):
        R = adj(None, M.rr.to_numpy(), M.risk.to_numpy(), win, s, sp)
        print("  spread %.2f  slippage %.2f: mean R %+.3f  t %+.2f | cost per trade %.3f R | break-even win rate %.1f%%" % (sp, s, R.mean(), R.mean() / (R.std(ddof=1) / np.sqrt(len(R))), (SPN - SP0 if sp == SPN else 0) / M.risk.mean() + s / M.risk.mean(), 100 * (1 + (SPN - SP0 + 2*s)/M.risk.mean()) / (1 + M.rr.mean() - (SPN - SP0 + s)/M.risk.mean() + (SPN - SP0 + 2*s)/M.risk.mean())))
print("\ntoday's trade (risk 11.49, reward 6.13, 0.534 R): net R if it wins / loses with spread 0.47")
for s in (0, 0.5, 1.0): print("  slippage %.2f: win %+.3f R, loss %.3f R" % (s, (6.13 - 0.19 - s) / 11.49, -1 - (0.19 + 2 * s) / 11.49))
# Monte Carlo
START, TARGET, FLOOR, DAYLOSS, CAP = 95472.14, 108000.0, 92000.0, -2500.0, 2000.0
def run(Wr, Wm, Lr, p, risk, tpd, N=30000, H=250, seed=1):
    rng = np.random.default_rng(seed); bal = np.full(N, START); st = np.zeros(N, np.int8); de = np.full(N, -1)
    for day in range(1, H + 1):
        act = st == 0
        if not act.any(): break
        n = rng.integers(1, 3, N) if tpd == "mix" else np.full(N, int(tpd)); real = np.zeros(N)
        for t in (1, 2):
            use = act & (st == 0) & (n >= t)
            if not use.any(): continue
            iswin = rng.random(N) < p; iw = rng.integers(0, len(Wr), N); il = rng.integers(0, len(Lr), N)
            R = np.where(iswin, Wr[iw], Lr[il]); mae = np.where(iswin, Wm[iw], 1.0); low = real - mae * risk
            br = use & ((low <= DAYLOSS) | (bal + low <= FLOOR)); st[br] = 2; de[br] = day
            real = np.where(use & ~br, real + R * risk, real)
        act = st == 0; bal = np.where(act, bal + np.where(real > 0, np.minimum(real, CAP), real), bal)
        br2 = act & (bal <= FLOOR); st[br2] = 2; de[br2] = day
        ps = act & (st == 0) & (bal >= TARGET); st[ps] = 1; de[ps] = day
    return st, de
rng = np.random.default_rng(7); pdraw = rng.beta(25, 7, 30000)
print("\nMonte Carlo, win rate uncertain (Beta 25,7: mean 78%), 1 trade a day, pass / breach / mean business days to pass:")
for s in (0.0, 0.5, 1.0):
    R = adj(None, M.rr.to_numpy(), M.risk.to_numpy(), win, s); Wr, Wm = R[win], M.mae_R.to_numpy()[win]; Lr = R[~win]
    for risk in (1000, 2000):
        for tpd in ("1", "mix"):
            st, de = run(Wr, Wm, Lr, pdraw, risk, tpd); ps = st == 1; br = st == 2
            print("  slippage %.2f  risk %4d  %-3s trades/day: pass %4.0f%%  breach %4.0f%%  mean %.0f days" % (s, risk, tpd, 100 * ps.mean(), 100 * br.mean(), de[ps].mean() if ps.any() else float("nan")))
