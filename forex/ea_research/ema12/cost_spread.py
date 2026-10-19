"""the trader: the 0.50-1.00 USD is the ask-bid spread, NOT slippage. Re-cost his 30 trades with spread 0.48 / 0.50 / 0.75 / 1.00 and no extra slippage, then the 1-trade-a-day Monte Carlo."""
import numpy as np, pandas as pd
exec(open("cost_now.py").read().split("# Monte Carlo")[0].split('print("30 trades')[0])          # loads O, M, SP0, adj
win = (M.res == "W").to_numpy(); SP0 = 0.28
print("spread (USD) | mean R | t | break-even win rate (his 80%)")
for sp in (0.28, 0.48, 0.50, 0.75, 1.00):
    d = sp - SP0; R = np.where(win, M.rr - d / M.risk, -1.0 - d / M.risk); cw = (d / M.risk).mean()
    be = (1 + cw) / (1 + cw + M.rr.mean() - cw)
    print("   %.2f      | %+.3f | %+.2f | %.1f%%" % (sp, R.mean(), R.mean() / (R.std(ddof=1) / np.sqrt(len(R))), 100 * be))
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
print("\nMonte Carlo (win rate uncertain, mean 78%): pass / breach / mean business days")
for sp in (0.28, 0.48, 0.75, 1.00):
    d = sp - SP0; R = np.where(win, M.rr - d / M.risk, -1.0 - d / M.risk); Wr, Wm, Lr = R[win], M.mae_R.to_numpy()[win], R[~win]
    for risk in (1000, 2000):
        for tpd in ("1", "mix"):
            st, de = run(Wr, Wm, Lr, pdraw, risk, tpd); ps = st == 1; br = st == 2
            print("  spread %.2f  risk %4d  %-3s trades/day: pass %3.0f%%  breach %3.0f%%  mean %.0f days" % (sp, risk, tpd, 100 * ps.mean(), 100 * br.mean(), de[ps].mean() if ps.any() else float("nan")))
