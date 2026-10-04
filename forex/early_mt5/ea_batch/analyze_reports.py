"""
Round 347 (2026-10-04, PRE-REGISTERED before any report exists; ONE ledger row, k + 1): the MQL5 CodeBase MT5 Expert Advisors (all 1,659 published on 2026-10-04,
filtered by forex/early_mt5/ea_batch/build_manifest.py) run in the MetaTrader 5 Strategy Tester on the MT5 broker demo account (forex/early_mt5/ea_batch/run_batch.py, the trader's second PC), scored
against the trader's bar: pass the MT5 1-Step $100K within 30 calendar days with probability >= 70%.

  python forex/early_mt5/ea_batch/analyze_reports.py            # reads forex/early_mt5/ea_batch/results/*.csv + status.csv, writes results_summary.csv / .json

INPUT: each EA's closed deals (time, profit, commission, swap) from its tester report, default inputs, 2021-10-01..2026-09-30, model 1-minute OHLC, $100,000 deposit.
DAILY P&L: net of deals summed by tester (server) date. EAs with < 20 days with P&L in IS (2021-10..2023-12) are untestable (reported).
SCALING (the default lot is arbitrary on $100K): P&L is multiplied by lambda so that the 5th percentile of the EA's IS daily P&L (its bad days) = -x% of $100,000, x in
(0.5, 1, 1.5, 2, 2.5); the x with the highest IS 30-day pass probability is chosen (on IS only) and frozen for OOS. Linear scaling (lot steps, the EA's own sizing logic
and compounding ignored; disclosed).
30-DAY 1-STEP REPLAY: every weekday start; the scaled daily P&L of the next 30 calendar days in order; breach if a day loses more than $3,000 from its start balance or
the end-of-day balance falls to the trailing floor (highest day-start balance - $10,000); pass when balance > $110,000 with best day <= 50% of the profitable days.
Closed-deal accounting only: intraday floating losses are not visible (optimistic for EAs that sit in losing positions; grid / martingale EAs were excluded upstream).
IS starts: window ends before 2024-01-01. OOS starts: from 2024-01-01, window ends by 2026-09-30.
STATISTICS: mean scaled daily P&L IS / OOS, day-bootstrap one-sided p of the IS mean (2,000 draws, seed 347), Benjamini-Hochberg q = 0.10 over all testable EAs.
MANUAL'S BAR (fixed now): IS 30-day pass >= 70% AND OOS 30-day pass >= 70% at the IS-chosen x. Also reported: EAs above the deployed 30-day table (Round 345: 35% IS /
41% OOS) in both periods, and BH survivors with OOS mean > 0 (a statistical edge, separate from the bar). With about 1,000 EAs, the best OOS numbers are expected to be
inflated by selection; only an EA clearing the bar in BOTH periods, ideally also a BH survivor, would be a real lead; it would then need a fresh confirmation run
(real ticks, later data) before any money.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RES = Path(os.getenv("EA_BATCH_RESULTS") or HERE / "results")
OUT = Path(os.getenv("EA_BATCH_OUT") or HERE)
SPLIT, END = pd.Timestamp("2024-01-01"), pd.Timestamp("2026-09-30")
START = pd.Timestamp("2021-10-01")
XS = (0.005, 0.01, 0.015, 0.02, 0.025)
INITIAL, TARGET, DAILY, TRAIL = 100_000.0, 110_000.0, 3_000.0, 10_000.0
SEED = 347


def daily_pnl(f: Path) -> pd.Series:
    d = pd.read_csv(f)
    if d.empty:
        return pd.Series(dtype=float)
    t = pd.to_datetime(d["time"].astype(str).str.replace(".", "-", regex=False), errors="coerce")
    net = d["profit"] + d["commission"] + d["swap"]
    return net.groupby(t.dt.normalize()).sum().sort_index()


def pass30(pnl: pd.Series, starts) -> np.ndarray:
    days, vals = pnl.index.values, pnl.values
    out = np.zeros(len(starts))
    for n, s in enumerate(starts):
        lo, hi = np.searchsorted(days, np.datetime64(s)), np.searchsorted(days, np.datetime64(s + pd.Timedelta(days=30)))
        bal, hwm, pos, best = INITIAL, INITIAL, 0.0, 0.0
        for v in vals[lo:hi]:
            hwm = max(hwm, bal)
            if v < -DAILY:
                break
            bal += v
            if bal <= hwm - TRAIL:
                break
            if v > 0:
                pos += v; best = max(best, v)
            if bal > TARGET and best <= 0.5 * pos:
                out[n] = 1; break
    return out


def boot_p(x: np.ndarray, rng) -> float:
    if len(x) < 2:
        return float("nan")
    idx = rng.integers(0, len(x), (2000, len(x)))
    return float((x[idx].mean(1) <= 0).mean())


def bh(p, q=0.10):
    p = np.asarray(p); n = len(p); o = np.argsort(p); ok = p[o] <= q * np.arange(1, n + 1) / n
    k = np.max(np.flatnonzero(ok)) + 1 if ok.any() else 0
    keep = np.zeros(n, bool); keep[o[:k]] = True
    return keep


def main():
    rng = np.random.default_rng(SEED)
    wd = pd.bdate_range(START, END)
    is_starts = [s for s in wd if s + pd.Timedelta(days=30) < SPLIT]
    oos_starts = [s for s in wd if s >= SPLIT and s + pd.Timedelta(days=30) <= END]
    status = pd.read_csv(RES / "status.csv", dtype={"id": str}).drop_duplicates("id", keep="last") if (RES / "status.csv").exists() else pd.DataFrame(columns=["id"])
    rows = []
    for f in sorted(RES.glob("*.csv")):
        if f.name == "status.csv":
            continue
        eid = f.stem
        raw = daily_pnl(f)
        r = dict(id=eid, days=len(raw), days_IS=int((raw.index < SPLIT).sum()), testable=False)
        if r["days_IS"] < 20:
            rows.append(r); continue
        q5 = np.percentile(raw[raw.index < SPLIT].values, 5)
        if not q5 < 0:
            rows.append(dict(r, note="no IS losing days")); continue
        best = None
        for x in XS:
            lam = x * INITIAL / -q5
            p_is = pass30(raw * lam, is_starts).mean()
            if best is None or p_is > best[0]:
                best = (p_is, x, lam)
        p_is, x, lam = best
        s = raw * lam
        p_oos = pass30(s, oos_starts).mean()
        is_v, oos_v = s[s.index < SPLIT].values, s[s.index >= SPLIT].values
        rows.append(dict(r, testable=True, x=x, pass30_IS=p_is, pass30_OOS=p_oos, mean_IS=float(is_v.mean()), mean_OOS=float(oos_v.mean()) if len(oos_v) else float("nan"),
                         p_IS=boot_p(is_v, rng), net_default=float(raw.sum())))
    out = pd.DataFrame(rows)
    if out.empty:
        print("no results yet"); return
    out = out.merge(status[["id", "title", "symbol", "period"]] if "title" in status else status, on="id", how="left")
    t = out.testable.fillna(False).astype(bool)
    out["bh"] = False
    out.loc[t, "bh"] = bh(out.loc[t, "p_IS"].values)
    out["edge"] = out.bh & (out.mean_OOS > 0)
    out["beats_table"] = t & (out.pass30_IS >= 0.35) & (out.pass30_OOS >= 0.41)
    out["meets_70"] = t & (out.pass30_IS >= 0.70) & (out.pass30_OOS >= 0.70)
    out.sort_values("pass30_OOS", ascending=False).to_csv(OUT / "results_summary.csv", index=False)
    summ = dict(EAs_with_results=int(len(out)), testable=int(t.sum()), bh_survivors=int(out.bh.sum()), edge=int(out.edge.sum()),
                beats_30day_table=int(out.beats_table.sum()), meets_70=int(out.meets_70.sum()),
                top10_OOS=out[t].sort_values("pass30_OOS", ascending=False).head(10)[["id", "title", "symbol", "pass30_IS", "pass30_OOS"]].to_dict("records"))
    json.dump(summ, open(OUT / "results_summary.json", "w"), indent=1, default=str)
    print(json.dumps(summ, indent=1, default=str))


if __name__ == "__main__":
    main()
