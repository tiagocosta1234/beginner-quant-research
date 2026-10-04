"""
Round 319 (2026-10-03, PRE-REGISTERED): half-hour slot scan on gold (GC) and silver (SI) futures over the whole 24-hour day, causal prior-slot predictors, BH-controlled.

Goal context (the trader: "keep backtesting and refining until you find something better than our current best"): current best = the validated dip-reversal lead (about +35 bp a trade, sparse,
no intraday edge) and the coin-flip bold play (about 40% 1-Step pass by 31 Dec, 26% on harsh costs). A candidate must be a real edge, so the bar stays the ledger's, not lowered.
Ledger checked first (k = 2022): US100 slot scans (Round 298, 421, 188) exist; a 24-hour metals slot scan on 1-minute Databento GC and SI is NOT in the ledger.

Data: Databento 1-minute GC, SI (start-stamped, UTC -> New York), 2020-01-02 .. 2026-09-25, Monday-Friday, bars with volume only; slots = 48 half-hours of the New York clock (00:00-23:30).
Slots with fewer than 400 usable days in IS are dropped before any P&L is read (dry run prints which).
HYPOTHESES: per instrument x slot s x rule in {FOLLOW, FADE} the trade is: enter at the OPEN of slot s, exit at the CLOSE of its last minute; direction = +/- sign(return of slot s-1 on the same day), no trade
if slot s-1's return is zero. Return = close of last minute / open of first minute - 1. Cost per round trip: GC 1.5 bp, SI 3.0 bp (fixed now). Family size m = 2 x 48 x 2 = 192 minus dropped slots.
SPLIT: IS 2020-01-02..2023-12-31 (selection), OOS 2024-01-01.. (touched only for IS survivors). Selection: Benjamini-Hochberg q = 0.10 on the IS one-sided p-values of mean net bp > 0
(date-block bootstrap, 2,000 draws, seed 319). CANDIDATE: BH survivor in IS AND OOS net mean > 0 with one-sided P >= 0.99 AND the opposite rule (placebo) not also positive in OOS.
Not widened after the run. Ledger rows (summary: 1 row for the whole scan, k + 1) appended by hand after the run.
DRY-RUN COUNTS (no P&L read): 44 slots per instrument remain (slots 34-36 are the 17:00-18:00 NY maintenance break and the slot after it, which has no valid previous slot); IS days per slot 586-1,019, OOS days 441-696; none dropped
by the 400-day floor; family m = 44 x 2 x 2 = 176. A bug found in the first dry run (KeyError on the missing break slots) was fixed before any P&L was read.
POWER: IS per-trade sd about 12-25 bp, n about 900, so the s.e. of an IS mean is about 0.4-0.8 bp: a real edge of +3 bp net would be found; with 176 tests BH q = 0.10 lets about 10% of survivors be false by construction, so
the OOS stage (P >= 0.99, opposite rule not positive) is the real filter.
"""
import os, sys, json
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "data", "databento")
COST = {"GC": 1.5, "SI": 3.0}
IS_END = pd.Timestamp("2023-12-31")
MIN_IS_DAYS = 400


def slot_returns(sym):
    df = pd.read_parquet(os.path.join(DB, f"futures_{sym}.F_1m.parquet"))
    idx = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    b = pd.DataFrame({"o": df["open"].values, "c": df["close"].values, "v": df["volume"].values}, index=idx).sort_index()
    b = b[~b.index.duplicated(keep="first")]
    b = b[(b.index.dayofweek < 5) & (b.index >= "2020-01-02") & (b.v > 0)]
    slot = (b.index.hour * 2 + b.index.minute // 30).astype(int)
    day = b.index.normalize()
    g = b.groupby([day, slot])
    first_o = g["o"].first(); last_c = g["c"].last(); n = g["c"].count()
    r = (last_c / first_o - 1)
    r = r[n >= 20]                       # a slot needs at least 20 of its 30 minutes
    return r.unstack()                   # index day, columns slot 0..47


def build(sym):
    R = slot_returns(sym)
    out = {}
    for s in range(48):
        prev = (s - 1) % 48
        if s not in R.columns or prev not in R.columns:
            continue                      # slots inside the daily maintenance break have no bars
        if s == 0:
            prevr = R[47].shift(1)       # slot 47 of the previous calendar day
        else:
            prevr = R[prev]
        d = pd.DataFrame({"r": R[s], "p": prevr}).dropna()
        d = d[d.p != 0]
        out[s] = d
    return out


def main(dry):
    rng = np.random.default_rng(319)
    rows = []
    for sym in COST:
        slots = build(sym)
        for s, d in slots.items():
            n_is = int((d.index <= IS_END).sum())
            if n_is < MIN_IS_DAYS:
                if dry: print(f"{sym} slot {s:2d} dropped (IS days {n_is})")
                continue
            if dry:
                print(f"{sym} slot {s:2d} IS days {n_is} OOS days {int((d.index > IS_END).sum())}"); continue
            for rule, sg in (("FOLLOW", 1), ("FADE", -1)):
                net = sg * np.sign(d.p) * d.r * 1e4 - COST[sym]
                a, b_ = net[net.index <= IS_END], net[net.index > IS_END]
                bs = a.values[rng.integers(0, len(a), (2000, len(a)))].mean(1)
                p_is = float((bs <= 0).mean())          # one-sided p of mean > 0
                bo = b_.values[rng.integers(0, len(b_), (2000, len(b_)))].mean(1)
                rows.append(dict(sym=sym, slot=s, rule=rule, n_is=len(a), n_oos=len(b_), is_bp=float(a.mean()), p_is=p_is,
                                 oos_bp=float(b_.mean()), P_oos=float((bo > 0).mean())))
    if dry: return
    df = pd.DataFrame(rows).sort_values("p_is").reset_index(drop=True)
    m = len(df); q = 0.10
    df["bh"] = df.p_is <= (np.arange(1, m + 1) / m) * q
    k = int(df.bh[::-1].cummax()[::-1].sum()) if m else 0       # BH: all up to the largest passing rank
    surv = df.iloc[:k] if k else df.iloc[:0]
    # placebo = opposite rule on the same sym/slot
    def opp(r):
        o = df[(df.sym == r.sym) & (df.slot == r.slot) & (df.rule != r.rule)].iloc[0]
        return o.oos_bp
    df["cand"] = False
    for i in range(k):
        r = df.iloc[i]
        df.loc[i, "cand"] = bool(r.oos_bp > 0 and r.P_oos >= 0.99 and opp(r) <= 0)
    print(f"hypotheses m={m}; BH survivors in IS: {k}; candidates: {int(df.cand.sum())}")
    print(df.head(12).round(3).to_string())
    print("mean IS net bp over all hypotheses", round(df.is_bp.mean(), 2), " mean OOS", round(df.oos_bp.mean(), 2))
    df.to_csv(os.path.join(HERE, "round319_grid.csv"), index=False)
    json.dump(dict(m=m, bh_survivors=k, candidates=int(df.cand.sum()), mean_is=float(df.is_bp.mean()), mean_oos=float(df.oos_bp.mean())),
              open(os.path.join(HERE, "round319_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
