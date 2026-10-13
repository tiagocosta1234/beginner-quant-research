"""Diagnostic for V1 (pre-FOMC drift), NOT a trial: is +47 bp per event just the bull market? The same 14:02 ET (day before) -> 13:55 ET window on every other business day, 2022-2025 (2026 not touched).
   python -m forex.ea_research.event_macro_placebo"""
import numpy as np
import pandas as pd

from forex.ea_research import event_macro as V

cal = pd.read_csv(V.CAL); fomc = set(cal[cal.kind == "FOMC"].date)
days = [str(d) for d in pd.bdate_range("2022-01-04", "2025-12-31").date]
rows = []
for D in days:
    ti, tx = V.server_s(V.prev_bday(D), 14, 2), V.server_s(D, 13, 55); legs = []
    for m in V.V1_MKTS:
        qi, qx = V.quote(m, ti), V.quote(m, tx)
        if qi is None or qx is None: continue
        legs.append((qx[0] / qi[1] - 1.0) * 1e4 - 2 * V.SLIP * 1e4)
    if len(legs) == 3: rows.append(dict(date=pd.Timestamp(D), net=float(np.mean(legs)), fomc=D in fomc))
X = pd.DataFrame(rows); F, N = X[X.fomc], X[~X.fomc]
print(f"windows with all three indices: {len(X)} (FOMC {len(F)}, other {len(N)})")
for y in (2022, 2023, 2024, 2025, None):
    f = F if y is None else F[F.date.dt.year == y]; n = N if y is None else N[N.date.dt.year == y]
    d = f.net.mean() - n.net.mean(); se = np.sqrt(f.net.var(ddof=1) / len(f) + n.net.var(ddof=1) / len(n))
    print(f"{'2022-25' if y is None else y}: FOMC windows {len(f):3d} mean {f.net.mean():+7.2f} bp | other windows {len(n):4d} mean {n.net.mean():+6.2f} bp (sd {n.net.std():5.1f}) | difference {d:+7.2f} bp, Welch t {d/se:+5.2f}")
rk = (N.net.values[None, :] >= F.net.values[:, None]).mean(axis=1)
print(f"rank of each FOMC window among the other windows (share of others at or above it), mean {rk.mean():.3f} (0.5 = ordinary); FOMC windows in the top decile of all windows: {int((rk <= 0.10).sum())} of {len(F)}")
rng = np.random.default_rng(3); sims = np.array([rng.choice(N.net.values, len(F), replace=False).mean() for _ in range(20000)])
print(f"random-day placebo: mean of {len(F)} random non-FOMC windows exceeds the FOMC mean in {100*(sims >= F.net.mean()).mean():.2f}% of 20,000 draws")
