"""Stress test with bigger price jumps (the trader 2026-10-14, after the per-tick guard test left 22 USD of margin): on the minute path of each session of the pair (x1.5, MT5 broker pool), an adverse instantaneous jump of J USD per ounce hits the open net position at every minute while positions are open and the session is unresolved;
the guard acts on the first tick after the jump. Reported: share of those (session, minute) shocks whose equity after the jump is <= -2,500 vs the day start (MT5 broker hard breach), per J and loss lock L, and how often gold moved >= J in one minute / over a weekend gap in the last 12 months.
python -m forex.self_improving.session.stress_jumps"""
import numpy as np, pandas as pd
from forex.self_improving.session import session_lab as S, session_sdbrunner as R

JS = (20, 40, 78, 120, 200, 300)


def main():
    import os; M = float(os.environ.get('M', '1.5')); tr, lo, hi = R.load_flag("MT5"); rows = []
    for L in (1500.0, 2000.0, 2400.0) if M == 1.5 else (2000.0,):
        S.COLLECT = []; df = S.run(tr, lo, hi, L, M, 0.0, 0.0, 0.0); col = S.COLLECT; S.COLLECT = None
        row = dict(L=L)
        for J in JS:
            tot = 0; bad = 0; badd = 0; days_with = 0
            for d, P, NQ in col:
                exp = np.abs(NQ); m = exp > 1e-9
                if not m.any(): continue
                days_with += 1; sh = P[m] - J * exp[m]; tot += int(m.sum()); b = (sh <= -2500.0); bad += int(b.sum()); badd += int(b.any())
            row[f"J{J}_pct_minutes"] = 100 * bad / max(tot, 1); row[f"J{J}_pct_days"] = 100 * badd / max(days_with, 1)
        rows.append(row); print({k: round(v, 1) for k, v in row.items()}, flush=True)
    o = pd.DataFrame(rows); o.to_csv(f"data/si_ledgers/STRESS_jumps{'' if M == 1.5 else '_x' + str(M)}.csv", index=False)
    tm, bc, sp = S.bars; d = np.abs(np.diff(bc)); gap = np.diff(tm); ok = (gap == 60) & ((tm[1:] % 86400) // 3600 >= 1) & ((tm[1:] % 86400) // 3600 < 23); wk = gap > 6 * 3600
    t12 = tm[1:] >= tm[-1] - 365 * 86400; yrs = (tm[-1] - tm[0]) / 86400 / 365
    print("1-minute moves >= J USD per year (all years / last 12 months):", {J: (int(((d >= J) & ok).sum() / yrs * 10) / 10, int(((d >= J) & ok & t12).sum())) for J in JS})
    print("weekend/closure gaps >= J USD per year (all years / last 12 months):", {J: (int(((d >= J) & wk).sum() / yrs * 10) / 10, int(((d >= J) & wk & t12).sum())) for J in JS}, "largest gap:", round(float(d[wk].max()), 1))


if __name__ == "__main__":
    main()
