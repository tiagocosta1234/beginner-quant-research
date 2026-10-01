"""
Round 286 (2026-10-01, PRE-REGISTERED): INDEPENDENT-DATA CONFIRMATION of Round 285's lead -- "long a 2-sigma 3-day dip, held one day". the trader approved the data
download ("yes, download it and run it"). The rule below is Round 285's, copied exactly and NOT re-tuned; the sample is different: eight cash-index daily histories from
Yahoo Finance (S&P 500, Nasdaq-100, DJIA, DAX, FTSE 100, CAC 40, Nikkei 225, Hang Seng; futures/data/external_index_daily, MANIFEST.json), 1990-01-01 .. 2017-12-27,
i.e. everything BEFORE the MT5 CFD history (which starts 2017-12-28) that produced the lead. (Stooq was tried first and blocked behind a JavaScript bot check; it was not bypassed.)

THE LEAD (Round 285, fixed): z3_t = ln(close_t / close_t-3) / (sigma60_t x sqrt(3)), sigma60 = standard deviation of the previous-60-days' simple returns including day t (>= 40 observations);
LONG at the close of day t when z3 <= -Z, exit at the close of the next trading day (H = 1). Weekend rule: the exit weekday must be later than the entry weekday and at most 3 calendar days after
(entries Monday-Thursday, holidays shift it). One position per index at a time. No trend filter. NET bps = next-day return x 10,000 - COST. COST = 5.0 bps per trade, fixed now: the
index CFD's one night of swap (long -8%/yr = -3.3 bps) + the entry and exit spreads and a margin of slippage; the cash-index close is not the CFD's 17:00 NY close (disclosed difference).
CELLS (3, long only, H = 1): Z = 2.0 (PRIMARY, the lead), Z = 1.5 and Z = 1.0 (the dose-response). Unit of inference: the date (daily mean over the indices with a trade), 4,000-draw bootstrap, seed 2861.
BASELINE: for each index, the mean net return of the unconditional trade (every eligible day) in the same window; EXCESS = net - that mean. Sub-periods: 1990-2003 and 2004-2017-12-27.
CONFIRMATION RULE (fixed now; a single pre-specified hypothesis plus two dose-response cells, so Bonferroni over 3): the lead is CONFIRMED only if, for the PRIMARY cell on the pooled sample,
(a) mean net > 0 AND P(net > 0) >= 1 - 0.01/3 = 0.9967, (b) P(excess > 0) >= 0.9967, (c) mean excess > 0 in BOTH sub-periods, (d) mean net rises with the dip size across Z = 1.0 < 1.5 < 2.0,
and (e) the mean excess is positive in at least 6 of the 8 indices. Otherwise "NOT CONFIRMED" (a partial result is reported as such). Ledger rows 895-897 (k = 894 + 3 = 897).
DESCRIPTIVE (not part of the rule): the same cells on 2018-01-01 .. 2025-09-30 of the cash-index data (overlapping the CFD window) to see how close the cash index is to the CFD result.
PRIOR (stated now): the short-term reversal effect in equity indices was documented on exactly these decades and widely traded; an honest expectation is a smaller, partly decayed effect; a clean
confirmation at 0.9967 is demanding. POWER_NOTES: ~28 years x 8 indices at Z = 2 give roughly 1,500-2,500 trades, a standard error of the mean of ~5-8 bps at a per-trade sd of ~150-250 bps.
"""
import os, sys, json, time, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

DATA = os.path.join(ROOT, "futures", "data", "external_index_daily")
NAMES = ["spx", "ndx", "dji", "dax", "ftse", "cac", "n225", "hsi"]
FROM, TO = pd.Timestamp("1990-01-01"), pd.Timestamp("2017-12-27")
SPLIT = pd.Timestamp("2004-01-01")
ZS, H, COST = (2.0, 1.5, 1.0), 1, 5.0
SEED, BOOT = 2861, 4000
K_TOTAL = 897
BONF = 1 - 0.01 / 3


def load(name):
    d = pd.read_csv(os.path.join(DATA, name + ".csv"), parse_dates=["date"]).set_index("date").sort_index()
    c = d["close"].astype(float)
    r = c.pct_change()
    r = r.mask(r.abs() > 0.5, 0.0)
    sd = r.rolling(60, min_periods=40).std()
    lp = np.log(c)
    z3 = (lp - lp.shift(3)) / (sd * np.sqrt(3))
    return dict(d=c.index, r=r.fillna(0.0).values, z3=z3.values, wd=c.index.weekday.values)


def eligible(S, i):
    d = S["d"]
    return i + 1 < len(d) and S["wd"][i + 1] > S["wd"][i] and (d[i + 1] - d[i]).days <= H + 2


def nets(S, lo, hi, Z=None):
    out = []
    i = 70
    n = len(S["d"])
    while i < n - 1:
        ok = lo <= S["d"][i] <= hi and eligible(S, i) and np.isfinite(S["z3"][i])
        if ok and Z is not None:
            ok = S["z3"][i] <= -Z
        if ok:
            out.append((S["d"][i], S["r"][i + 1] * 1e4 - COST))
        i += 1                                   # H = 1: the next entry may be taken at the exit close, as in Round 285 (i += H)
    return out


def boot_p(x, seed=SEED):
    x = np.asarray(x, float)
    if len(x) < 5:
        return float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), (BOOT, len(x)))
    return float(np.mean(x[idx].mean(axis=1) > 0))


def run_window(Ss, lo, hi, Z):
    rows = []
    for name, S in Ss.items():
        base = nets(S, lo, hi, None)
        b = float(np.mean([v for _, v in base])) if base else np.nan
        for d, v in nets(S, lo, hi, Z):
            rows.append((name, d, v, v - b))
    return pd.DataFrame(rows, columns=["idx", "date", "net", "ex"])


def summarize(tr):
    if len(tr) < 5:
        return dict(n=int(len(tr)), mean=float("nan"), excess=float("nan"), win=float("nan"), P=float("nan"), Pex=float("nan"))
    d = tr.groupby("date")[["net", "ex"]].mean()
    return dict(n=int(len(tr)), mean=float(tr["net"].mean()), excess=float(tr["ex"].mean()), win=float((tr["net"] > 0).mean()), P=boot_p(d["net"].values), Pex=boot_p(d["ex"].values))


def dry_run():
    Ss = {n: load(n) for n in NAMES}
    for n, S in Ss.items():
        m = (S["d"] >= FROM) & (S["d"] <= TO)
        print(f"{n:>5}: {int(m.sum())} days in 1990..2017-12-27, first {S['d'][m][0].date()}, signals (z3 <= -2): {int(np.sum(S['z3'][m] <= -2))}")
    rng = np.random.default_rng(1)
    tr = run_window(Ss, FROM, TO, 2.0)
    allb = [(n, d, v) for n, S in Ss.items() for d, v in nets(S, FROM, TO, None)]
    pick = rng.choice(len(allb), size=len(tr), replace=False)
    b_all = float(np.mean([allb[j][2] for j in pick]))
    print(f"{len(tr)} primary-cell trades; placebo: {len(tr)} random eligible entries have mean net {b_all:+.1f} bps vs unconditional {np.mean([v for _, _, v in allb]):+.1f} bps")
    assert all(S["wd"][i + 1] > S["wd"][i] for S in Ss.values() for i in range(70, len(S["d"]) - 1) if eligible(S, i))
    print("weekend-rule assertion passed")
    print("DRY RUN OK")


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    Ss = {n: load(n) for n in NAMES}
    out = {"cells": {}}
    print(f"{'Z':>4} | {'window':>14} {'n':>6} {'mean net':>9} {'excess':>8} {'win':>6} {'P(net>0)':>9} {'P(exc>0)':>9}")
    for Z in ZS:
        for wname, lo, hi in (("1990-2017", FROM, TO), ("1990-2003", FROM, SPLIT - pd.Timedelta(days=1)), ("2004-2017", SPLIT, TO), ("2018-2025 (desc.)", pd.Timestamp("2018-01-01"), pd.Timestamp("2025-09-30"))):
            tr = run_window(Ss, lo, hi, Z)
            s = summarize(tr)
            out["cells"][f"{Z}|{wname}"] = s
            print(f"{Z:>4.1f} | {wname:>14} {s['n']:>6} {s['mean']:>+9.1f} {s['excess']:>+8.1f} {s['win']:>6.1%} {s['P']:>9.3f} {s['Pex']:>9.3f}", flush=True)
    tr = run_window(Ss, FROM, TO, 2.0)
    per = {}
    print("\nPRIMARY cell (Z = 2.0) by index, 1990-2017:")
    for n in NAMES:
        t = tr[tr["idx"] == n]
        per[n] = dict(n=int(len(t)), mean=float(t["net"].mean()) if len(t) else float("nan"), excess=float(t["ex"].mean()) if len(t) else float("nan"))
        print(f"   {n:>5}: {per[n]['n']:>4} trades, mean net {per[n]['mean']:+7.1f} bps, excess {per[n]['excess']:+7.1f} bps")
    out["per_index"] = per
    c = out["cells"]
    a = c["2.0|1990-2017"]["mean"] > 0 and c["2.0|1990-2017"]["P"] >= BONF
    b = c["2.0|1990-2017"]["Pex"] >= BONF
    cc = c["2.0|1990-2003"]["excess"] > 0 and c["2.0|2004-2017"]["excess"] > 0
    d = c["1.0|1990-2017"]["mean"] < c["1.5|1990-2017"]["mean"] < c["2.0|1990-2017"]["mean"]
    e = sum(1 for v in per.values() if v["excess"] > 0) >= 6
    ok = a and b and cc and d and e
    out["verdict"] = dict(a_net=bool(a), b_excess=bool(b), c_both_subperiods=bool(cc), d_dose_response=bool(d), e_six_of_eight=bool(e), confirmed=bool(ok))
    print(f"\nCONFIRMATION RULE: (a) mean net > 0 and P >= {BONF:.4f}: {a}; (b) P(excess) >= {BONF:.4f}: {b}; (c) excess > 0 in both sub-periods: {cc}; (d) dose-response: {d}; (e) >= 6 of 8 indices positive: {e} -> "
          f"{'CONFIRMED' if ok else 'NOT CONFIRMED'}")
    json.dump(out, open(os.path.join(HERE, "round286_results.json"), "w"), indent=1, default=float)
    print("Saved round286_results.json")


if __name__ == "__main__":
    main()
