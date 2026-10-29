"""The USDJPY London breakout (PRESAMPLE L1 rules) on the MT5 broker account from today's state (balance 97,708.08, counted -2,291.92, first day Fri 16 Oct).
Day series in R (0 on days without a fill): MT5 2022-26 from BRK_EXITS (USDJPY, X4_noTP), HistData 2020-21 from PRESAMPLE L1.
Block bootstrap (5-day blocks, 20,000 paths); MT5 broker rules: counted / balance gain capped at +2,000 a day, -2,500 a day or balance <= 92,000 = breach,
pass at counted +8,000.   python -m forex.ea_research.usdjpy_mt5sim"""
import numpy as np
import pandas as pd

START_BAL = 97_708.08
HZ = {"30 Oct": 11, "30 Nov": 32, "22 Dec": 48, "31 Mar 27": 115, "30 Jun 27": 179}
RISKS = (150, 250, 400, 600, 1000)


def pools():
    e = pd.read_parquet("data/si_ledgers/BRK_EXITS.parquet")
    e = e[e.mkt == "USDJPY"]
    days = pd.DatetimeIndex(sorted(e.day.unique()))
    r8 = e[e.kind == "BRK"].groupby("day").X4_noTP.first().reindex(days).fillna(0.0)
    p = pd.read_parquet("data/si_ledgers/PRESAMPLE.parquet")
    p = p[p.lead == "L1"]
    d20 = pd.bdate_range("2020-01-02", "2021-11-30")
    r20 = p.groupby("day").R.first().reindex(d20).fillna(0.0)
    return {"MT5 2022-26": r8.to_numpy(), "HistData 2020-21": r20.to_numpy(), "all 2020-26": np.r_[r20.to_numpy(), r8.to_numpy()]}


def simulate(x, risk, H, rng, paths=20000):
    n = len(x)
    nb = H // 5 + 2
    starts = rng.integers(0, n - 5, size=(paths, nb))
    idx = (starts[:, :, None] + np.arange(5)[None, None, :]).reshape(paths, -1)[:, :H]
    pnl = x[idx] * risk
    bal = np.full(paths, START_BAL)
    st = np.zeros(paths, np.int8)
    day = np.full(paths, -1)
    for j in range(H):
        act = st == 0
        p = pnl[:, j]
        br = act & ((p <= -2500) | (bal + np.minimum(p, 0) <= 92_000))
        st[br], day[br] = 2, j
        act = st == 0
        bal = np.where(act, bal + np.minimum(p, 2000.0), bal)
        ps = act & (bal >= 108_000)
        st[ps], day[ps] = 1, j
    return st, day


def main():
    rng = np.random.default_rng(161026)
    P = pools()
    rows = []
    for pool, x in P.items():
        print(f"{pool}: {len(x)} days, mean {x.mean():+.3f} R a day, fill rate {np.mean(x != 0):.0%}")
        for risk in RISKS:
            st, day = simulate(x, risk, max(HZ.values()), rng)
            r = dict(pool=pool, risk=risk)
            for k, h in HZ.items():
                r[f"pass {k}"] = 100 * np.mean((st == 1) & (day < h))
                r[f"breach {k}"] = 100 * np.mean((st == 2) & (day < h))
            rows.append(r)
    T = pd.DataFrame(rows)
    T.to_csv("data/si_ledgers/USDJPY_MT5SIM.csv", index=False)
    pd.set_option("display.width", 250)
    for k in HZ:
        print(f"\n{k}: pass% / breach%")
        print(T.assign(v=T[f"pass {k}"].round(1).astype(str) + " / " + T[f"breach {k}"].round(1).astype(str)).pivot(index="risk", columns="pool", values="v").to_string())


if __name__ == "__main__":
    main()
