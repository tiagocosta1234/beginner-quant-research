"""BRK-MT5SIM (breakout day round 14): MT5 broker pass / breach odds from today's account state for the least-bad breakout systems found today.
Daily R series from today's rows; block bootstrap (5-day blocks) of trading days; MT5 Pro rules: counted profit capped at +2,000 a day,
target counted +8,000 on the 100,000 start (from today's balance 97,708.08 -> +10,291.92 needed), static floor 92,000, daily loss 2,500
from the day's starting balance (approximated on the daily sum; several trades a day can breach intraday earlier, so breach is understated).
   python -m forex.ea_research.brk_mt5sim"""
import numpy as np
import pandas as pd

START, TARGET, FLOOR, DAYLIM, CAP = 97_708.08, 108_000.0, 92_000.0, 2_500.0, 2_000.0
HORIZONS = {"to 30 Oct (11 days)": 11, "to 22 Dec (48 days)": 48, "to 31 Mar 2027 (115 days)": 115}
RISKS = (250, 500, 1000)
N = 20_000


def series():
    out = {}
    a = pd.read_parquet("D:/finance/si_ledgers/ORB_REFINE_NSDQ.parquet")
    b = pd.read_parquet("D:/finance/si_ledgers/ORB_TREND_2026_NSDQ.parquet")
    nq = pd.concat([a[a.side == a.trend][["day", "R"]], b[b.side == b.trend][["day", "R"]]])
    out["S1 card Nasdaq trend-direction (half-box stop, 2R)"] = nq.groupby("day").R.sum()
    e = pd.read_parquet("D:/finance/si_ledgers/BRK_EXITS.parquet")
    us = e[(e.kind == "BRK") & e.mkt.isin(["SP", "NSDQ", "DOW"])]
    out["S2 US index session ORB, hold to close"] = us.groupby("day").X4_noTP.sum()
    an = pd.read_parquet("D:/finance/si_ledgers/BRK_ANATOMY.parquet")
    k2 = an[(an.kind == "BRK") & (an.box_spreads >= 40)]
    out["S3 any market, box >= 40 spreads, hold to close"] = k2.groupby("day").close_R.sum()
    return out


def bdays(s):
    idx = pd.bdate_range(s.index.min(), s.index.max())
    return s.reindex(idx, fill_value=0.0)


def simulate(daily_r, risk, horizon, rng):
    x = daily_r.to_numpy()
    n = len(x)
    passed = breached = 0
    for _ in range(N):
        bal, counted = START, START - 100_000.0
        days = 0
        while days < horizon:
            st = rng.integers(0, max(n - 5, 1))
            for v in x[st:st + 5]:
                if days >= horizon:
                    break
                pnl = v * risk
                if pnl <= -DAYLIM or bal + pnl <= FLOOR:
                    breached += 1; days = 10**9; break
                bal += pnl
                counted += min(pnl, CAP)
                days += 1
                if counted >= TARGET - 100_000.0:
                    passed += 1; days = 10**9; break
    return passed / N, breached / N


def main():
    rng = np.random.default_rng(42)
    S = series()
    rows = []
    for name, s in S.items():
        s = bdays(s.sort_index())
        for pool, sub in (("recent 2025-26", s[s.index >= "2025-01-01"]), ("all 2022-26", s)):
            mu, sd = sub.mean(), sub.std()
            for risk in RISKS:
                for hz, h in HORIZONS.items():
                    p, b = simulate(sub, risk, h, rng)
                    rows.append(dict(system=name, pool=pool, risk=risk, horizon=hz, P_pass=p, P_breach=b, mean_R_day=mu, sd_R_day=sd))
    R = pd.DataFrame(rows)
    R.to_csv("D:/finance/si_ledgers/BRK_MT5SIM.csv", index=False)
    pd.set_option("display.width", 250)
    for name in S:
        print(f"\n{name}  (mean / sd of the daily R: recent {R[(R.system == name) & (R.pool == 'recent 2025-26')].mean_R_day.iloc[0]:+.3f} / {R[(R.system == name) & (R.pool == 'recent 2025-26')].sd_R_day.iloc[0]:.2f}, all {R[(R.system == name) & (R.pool == 'all 2022-26')].mean_R_day.iloc[0]:+.3f})")
        t = R[R.system == name].pivot_table(index=["pool", "risk"], columns="horizon", values=["P_pass", "P_breach"])
        print((t * 100).round(1).to_string())


if __name__ == "__main__":
    main()
