"""Sizing table for the daily card as traded (gold London, then Nasdaq NY), from today's account state (balance 97,708.08).
Day P&L series from CARD_EXPECTATIONS logic at $1 = risk unit; block bootstrap (5 days); MT5: +2,000 counted a day, pass at counted +8,000
(+10,291.92 from today), static floor 92,000, -2,500 day = breach.   python -m forex.ea_research.card_sizing"""
import numpy as np
import pandas as pd


def day_series(trend_only):
    g = pd.concat([pd.read_parquet("data/si_ledgers/ORB_REFINE_XAUUSD.parquet")[["day", "R"]], pd.read_parquet("data/si_ledgers/ORB_TREND_2026_XAUUSD.parquet")[["day", "R"]]]).groupby("day").R.first()
    n = pd.concat([pd.read_parquet("data/si_ledgers/ORB_REFINE_NSDQ.parquet")[["day", "R", "side", "trend"]], pd.read_parquet("data/si_ledgers/ORB_TREND_2026_NSDQ.parquet")[["day", "R", "side", "trend"]]])
    nq = (n[n.side == n.trend] if trend_only else n).groupby("day").R.first()
    days = pd.bdate_range("2022-01-03", "2026-10-02")
    return pd.DataFrame({"g": g.reindex(days), "n": nq.reindex(days)})


def simulate(df, risk, horizon, rng, N=20000):
    G, Nq = df.g.to_numpy(), df.n.to_numpy()
    n = len(G); passed = breached = 0
    for _ in range(N):
        bal, counted, d = 97_708.08, -2_291.92, 0
        while d < horizon:
            s = rng.integers(0, n - 5)
            for i in range(s, s + 5):
                if d >= horizon:
                    break
                p = risk * G[i] if not np.isnan(G[i]) else 0.0
                if p < 2 * risk - 1e-9 and not np.isnan(Nq[i]) and p > -1.95 * risk:
                    p += min(risk, 2 * risk + p) * Nq[i]
                if p <= -2500 or bal + p <= 92_000:
                    breached += 1; d = 10**9; break
                bal += p; counted += min(p, 2000.0); d += 1
                if counted >= 8000:
                    passed += 1; d = 10**9; break
    return passed / N, breached / N


def main():
    rng = np.random.default_rng(7)
    rows = []
    for trend_only in (False, True):
        df = day_series(trend_only)
        for pool, sub in (("2025-26", df[df.index >= "2025-01-01"]), ("2022-26", df)):
            for risk in (150, 250, 500, 1000):
                for hz, h in (("30 Oct", 11), ("22 Dec", 48), ("31 Mar 27", 115)):
                    p, b = simulate(sub, risk, h, rng)
                    rows.append(dict(version="trend-only Nasdaq" if trend_only else "Nasdaq both sides", pool=pool, risk=risk, horizon=hz, P_pass=p, P_breach=b))
    R = pd.DataFrame(rows)
    R.to_csv("data/si_ledgers/CARD_SIZING.csv", index=False)
    pd.set_option("display.width", 220)
    t = R.pivot_table(index=["version", "pool", "risk"], columns="horizon", values=["P_pass", "P_breach"])
    print((t * 100).round(1).to_string())


if __name__ == "__main__":
    main()
