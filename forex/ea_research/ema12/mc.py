import numpy as np, pandas as pd
M = pd.read_csv("mae_mt5.csv")
W = M[M.res == "W"]; L = M[M.res == "L"]
wr, wm = W.rr.to_numpy(), W.mae_R.to_numpy(); lm = np.ones(len(L))
START, TARGET, FLOOR, DAYLOSS, CAP = 95472.14, 108000.0, 92000.0, -2500.0, 2000.0
def run(p, risk, tpd, N=40000, H=250, seed=1):
    rng = np.random.default_rng(seed)
    bal = np.full(N, START); st = np.zeros(N, np.int8); day_end = np.full(N, -1)
    for day in range(1, H+1):
        act = st == 0
        if not act.any(): break
        n = rng.integers(1, 3, N) if tpd == "mix" else np.full(N, int(tpd))
        real = np.zeros(N)
        for t in (1, 2):
            use = act & (st == 0) & (n >= t)
            if not use.any(): continue
            iswin = rng.random(N) < p
            iw = rng.integers(0, len(W), N); il = rng.integers(0, len(L), N)
            R = np.where(iswin, wr[iw], -1.0); mae = np.where(iswin, wm[iw], 1.0)
            low = real - mae*risk
            br = use & ((low <= DAYLOSS) | (bal + low <= FLOOR))
            st[br] = 2; day_end[br] = day
            ok = use & ~br
            real = np.where(ok, real + R*risk, real)
        act = (st == 0)
        counted = np.where(real > 0, np.minimum(real, CAP), real)
        bal = np.where(act, bal + counted, bal)
        br2 = act & (bal <= FLOOR); st[br2] = 2; day_end[br2] = day
        ps = act & (st == 0) & (bal >= TARGET); st[ps] = 1; day_end[ps] = day
    return st, day_end
def summ(p, risk, tpd):
    st, de = run(p, risk, tpd)
    ps = st == 1; br = st == 2
    def by(k): return 100*np.mean(ps & (de <= k))
    return dict(p=p, risk=risk, tpd=tpd, pass31=by(31), pass47=by(47), pass_ever=100*ps.mean(), breach=100*br.mean(), open=100*np.mean(st == 0),
                mean_days=de[ps].mean() if ps.any() else np.nan, med_days=np.median(de[ps]) if ps.any() else np.nan,
                med_breach_day=np.median(de[br]) if br.any() else np.nan)
rows = []
for risk in (2000,):
    for tpd in ("mix", "2", "1"):
        for p in (0.80, 0.70, 0.656, 0.60):
            rows.append(summ(p, risk, tpd))
R = pd.DataFrame(rows); pd.set_option("display.width", 220)
print(R.round(1).to_string(index=False))
print("\ncomparison at other risk sizes (tpd=mix):")
rows = []
for risk in (500, 1000, 1500, 2000):
    for p in (0.80, 0.70):
        rows.append(summ(p, risk, "mix"))
print(pd.DataFrame(rows).round(1).to_string(index=False))
