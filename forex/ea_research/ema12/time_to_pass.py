"""How long would the trader's 12 EMA trades take to pass MT5 broker from 95,472 (spread 0.48, MT5 broker rules incl. equity-based -2,500 day, +2,000 counted cap)? Business days from 19 Oct (31 to 30 Nov, 47 to 22 Dec)."""
import numpy as np, pandas as pd
O = pd.read_csv("replay_mt5.csv"); M = pd.read_csv("mae_mt5.csv").merge(O[["k", "risk", "rew"]], on="k")
win = (M.res == "W").to_numpy(); d = 0.48 - 0.28
R = np.where(win, M.rr - d / M.risk, -1.0 - d / M.risk); Wr, Wm, Lr = R[win], M.mae_R.to_numpy()[win], R[~win]
START, TARGET, FLOOR, DAYLOSS, CAP = 95472.14, 108000.0, 92000.0, -2500.0, 2000.0
def run(p, risk, tpd, N=30000, H=250, seed=3):
    rng = np.random.default_rng(seed); bal = np.full(N, START); st = np.zeros(N, np.int8); de = np.full(N, -1)
    for day in range(1, H + 1):
        act = st == 0
        if not act.any(): break
        n = rng.integers(1, 3, N) if tpd == "mix" else np.full(N, int(tpd)); real = np.zeros(N)
        for t in (1, 2):
            use = act & (st == 0) & (n >= t)
            if not use.any(): continue
            iswin = rng.random(N) < p; iw = rng.integers(0, len(Wr), N); il = rng.integers(0, len(Lr), N)
            r = np.where(iswin, Wr[iw], Lr[il]); mae = np.where(iswin, Wm[iw], 1.0); low = real - mae * risk
            br = use & ((low <= DAYLOSS) | (bal + low <= FLOOR)); st[br] = 2; de[br] = day
            real = np.where(use & ~br, real + r * risk, real)
        act = st == 0; bal = np.where(act, bal + np.where(real > 0, np.minimum(real, CAP), real), bal)
        br2 = act & (bal <= FLOOR); st[br2] = 2; de[br2] = day
        ps = act & (st == 0) & (bal >= TARGET); st[ps] = 1; de[ps] = day
    return st, de
rng = np.random.default_rng(7); beta = rng.beta(25, 7, 30000)
print("win rate scenario | risk per trade | trades/day | pass % | breach % | median / mean business days to pass | pass by 30 Nov (31 d) | by 22 Dec (47 d)")
for name, p in (("sample 78% (uncertain)", beta), ("72% fixed", 0.72), ("68% fixed (~break-even)", 0.68)):
    for risk in (500, 1000, 1500, 2000):
        for tpd in ("1", "mix"):
            st, de = run(p, risk, tpd); ps = st == 1; br = st == 2
            print("%-24s| %4d | %-3s | %3.0f | %3.0f | %s | %3.0f | %3.0f" % (name, risk, tpd, 100 * ps.mean(), 100 * br.mean(), ("%3.0f / %3.0f" % (np.median(de[ps]), de[ps].mean())) if ps.sum() > 30 else "   -   ", 100 * np.mean(ps & (de <= 31)), 100 * np.mean(ps & (de <= 47))))
