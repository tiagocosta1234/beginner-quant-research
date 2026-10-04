"""
Round 331 (2026-10-03, PRE-REGISTERED, PROVISIONAL: Yahoo daily futures closes, not MT5 broker data; ONE ledger row, k + 1): daily cross-sectional reversal among the four US index futures.

Mechanism: relative performance among near-identical indices (ES, NQ, YM, RTY) mean-reverts within a day or two (liquidity / flow noise, no information difference). Ledger checked first (k = 2032): Rounds 283-284 tested 5-day reversal rebalanced weekly
and spread reversion on MT5 CFDs; a 1-day-rank reversal rebalanced daily on the four US futures is not in the ledger. High turnover, so costs decide.

DATA: Yahoo daily closes ES=F, NQ=F, YM=F, RTY=F (futures/data/daily), common dates 2017-07-10..2026-09-18 (RTY's start). Day t close: rank the four 1-day log returns; LONG the lowest, SHORT the highest, equal dollars, held to the close of t+1; one rebalance a day.
Net bp = (r_long - r_short) next day x 1e4 minus 2.0 bp (1 bp a leg round trip, ES-class futures; fixed now). Variants (3): the lowest vs the highest (V1), the lowest two vs the highest two (V2), V1 only on days whose cross-sectional spread (max - min) is in
the top third of its trailing 60 days (V3). Placebo: momentum (the opposite) reported.
SPLIT: IS 2017-07..2021-12, OOS 2022-01..2026-09. Statistic: mean net bp a day, 20-day-block bootstrap (5,000 draws, seed 331).
CANDIDATE (fixed now): IS mean > 0 with P >= 0.95 AND OOS mean > 0 with P >= 1 - 0.05/3 = 0.9833 AND the momentum placebo's OOS mean <= 0. Not widened after the run.
DRY-RUN COUNTS (no P&L): V1 / V2 2,314 days (IS 1,129 from 2017-07-11, OOS 1,185 to 2026-09-18), V3 761 (IS 372, OOS 389). Provisional until re-run on MT5 US100 / US500 / US30 / US2000 bars (US2000.cash exists in the MT5 broker instrument list).
POWER: the daily spread return has sd about 60-90 bp, so the s.e. of an IS / OOS mean is about 2 bp (V1, V2) and 3.5-4.5 bp (V3); an edge above about +6 bp a day net (V1) is detectable; the cost of 2 bp a day is about 500 bp a year of drag.
"""
import os, sys, json
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "data", "daily") + os.sep
COST = 2.0
SPLIT = pd.Timestamp("2022-01-01")


def ld(n):
    return pd.read_csv(f"{D}{n}_yahoo_daily.csv", parse_dates=["date"]).set_index("date").close


def frame():
    c = pd.concat({n: ld(f"{n}=F") for n in ("ES", "NQ", "YM", "RTY")}, axis=1, sort=True).dropna()
    r = np.log(c).diff()
    nxt = r.shift(-1)
    return r.iloc[1:-1], nxt.iloc[1:-1]


def variants():
    r, nxt = frame()
    rank = r.rank(axis=1, method="first")
    out = {}
    lo1, hi1 = (rank == 1), (rank == 4)
    out["V1"] = ((nxt * lo1).sum(1) - (nxt * hi1).sum(1)) * 1e4 - COST
    lo2, hi2 = (rank <= 2), (rank >= 3)
    out["V2"] = (((nxt * lo2).sum(1) - (nxt * hi2).sum(1)) / 2) * 1e4 - COST
    spread = r.max(axis=1) - r.min(axis=1)
    top = spread >= spread.rolling(60).quantile(2 / 3).shift(1)
    out["V3"] = out["V1"].where(top)
    plc = {k: -(v + COST) - COST for k, v in out.items()}
    return out, plc


def boot(x, rng):
    v = x.dropna().values; nb = len(v) // 20
    blocks = v[: nb * 20].reshape(nb, 20).mean(1)
    idx = rng.integers(0, nb, (5000, nb))
    return float(v.mean()), float((blocks[idx].mean(1) > 0).mean())


def main(dry):
    out, plc = variants(); rng = np.random.default_rng(331); res = {}
    for k in out:
        s, p = out[k].dropna(), plc[k].dropna()
        a, b = s[s.index < SPLIT], s[s.index >= SPLIT]
        if dry:
            print(k, f"days {len(s)} IS {len(a)} OOS {len(b)} from {s.index[0].date()} to {s.index[-1].date()}"); continue
        mi, pi = boot(a, rng); mo, po = boot(b, rng); pl = float(p[p.index >= SPLIT].mean())
        res[k] = dict(n_is=len(a), n_oos=len(b), is_bp=mi, is_P=pi, oos_bp=mo, oos_P=po, gross_oos=mo + COST, placebo_oos=pl,
                      candidate=bool(mi > 0 and pi >= .95 and mo > 0 and po >= 1 - .05 / 3 and pl <= 0))
        print(k, {a_: (round(v, 3) if isinstance(v, float) else v) for a_, v in res[k].items()})
    if not dry:
        print("candidates:", [k for k, v in res.items() if v["candidate"]])
        json.dump(res, open(os.path.join(HERE, "round331_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
