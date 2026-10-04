"""
Round 323 (2026-10-03, PRE-REGISTERED, descriptive scale: no ledger rows until a candidate exists; the 18 cells are logged as ONE ledger row at the end, k + 1): can any causal pre-open call of the 09:30-15:59 direction be right
often enough to matter inside the deployed 1-Step table?

Round 322 sized the target: +1 point of daily hit rate is worth about +2.8 points of pass probability near 50% (NQ 40.7% at 50%, 52.4% at 54%, 57.9% at 56%). Ledger checked first (k = 2025): prior-day follow / fade,
overnight-return follow / fade and trend-filter direction rules exist in pieces on MNQ and CFDs (Rounds 120-165, 282-284, 298) but not as a pre-open direction call scored on NQ and ES session proxies together.

DATA: Round 321's NQ and ES session proxy (Databento 1-minute, 09:30-15:59 ET, 2020-01-02..2026-09-25, 1,635 / 1,649 sessions) plus daily ^VIX; every predictor uses information dated before the 09:30 open.
PREDICTORS (9, one fixed form each, NO parameter tuning): P1 follow the prior session's close-to-close sign; P2 fade it; P3 follow the overnight move (prior 15:59 close -> 09:30 open); P4 fade it; P5 long if the prior session closed in the
upper half of its range, else short; P6 the opposite; P7 long after a VIX rise on the prior day (VIX close up), short after a fall; P8 long if the prior close is above its 20-session mean, else short; P9 long if above the 200-session mean, else short.
SCORE per predictor and instrument: hit rate = P(direction == sign(15:59 close - 09:30 open)), exact binomial one-sided p vs 0.5; and P(pass 57 days) in the Round 321 table run (20 draws not needed, deterministic), by period.
CANDIDATE (fixed now): hit rate >= 53.0% on BOTH NQ and ES AND P(pass 57d) at least 8 points above that instrument's COIN baseline (Round 321: 41.0 / 37.5) on both AND positive uplift in both periods (2020-22, 2023-26).
18 cells; the plain binomial Bonferroni bar (p < 0.0028) is reported for each cell. Not widened after the run: no new predictors, thresholds or windows to rescue a failure.
DRY-RUN COUNTS (no hit rate printed): NQ 1,635 sessions, non-missing predictions P1 1,634, P3 1,633, P5 1,635, P7 1,628, P8 1,635, P9 1,513 (200-session mean needs history); ES 1,649 sessions, P1 1,642,
P3 1,641, P5 1,649, P7 1,642, P8 1,649, P9 1,522. Timing hand-checked by reading: every feature is built from the PREVIOUS session's values (shift(1)) or from the 09:30 open vs the prior close (P3 / P4); the VIX change used
is the one into the previous session's date. (Lesson from Round 321's leak: no same-session value is used.)
POWER: at n about 1,640 the standard error of a hit rate is 1.23 points, so the Bonferroni cutoff (18 cells, p < 0.0028, z = 2.77) is a hit rate of about 53.4%; the pre-registered bar is 53.0% on BOTH instruments, a
joint event whose chance under all-null predictors is below 0.01 for any one predictor.
"""
import os, sys, json
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import round321_long_bias_bold_play as R
from mt5broker import onestep as OS

D = os.path.join(HERE, "..", "data", "daily") + os.sep
BASE = {"NQ": 0.410, "ES": 0.375}


def features(sym):
    df = R.day_table(sym)                      # R_{side}_{k}, z3, prior (already shifted), dow
    b = R.load(sym)
    g = b.groupby(b.index.normalize())
    o = g.o.first(); c = g.c.last(); h = g.h.max(); l = g.l.min()
    o, c, h, l = (x.reindex(df.index) for x in (o, c, h, l))
    full = pd.concat([g.o.first(), g.c.last(), g.h.max(), g.l.min()], axis=1, keys=list("ochl")).sort_index()
    pc = full.c.shift(1).reindex(df.index)
    ph, pl_ = full.h.shift(1).reindex(df.index), full.l.shift(1).reindex(df.index)
    pret = np.log(full.c).diff().shift(1).reindex(df.index)
    ma20 = full.c.rolling(20).mean().shift(1).reindex(df.index)
    ma200 = full.c.rolling(200).mean().shift(1).reindex(df.index)
    vix = pd.read_csv(D + "^VIX_yahoo_daily.csv", parse_dates=["date"]).set_index("date").close
    vprev = vix.diff().shift(1).reindex(df.index, method="ffill")     # change into the previous session's date
    f = pd.DataFrame(index=df.index)
    f["P1"] = np.sign(pret); f["P2"] = -f.P1
    ov = (o / pc - 1); f["P3"] = np.sign(ov); f["P4"] = -f.P3
    loc = (full.c.shift(1) - full.l.shift(1)) / (full.h.shift(1) - full.l.shift(1)); loc = loc.reindex(df.index)
    f["P5"] = np.where(loc > 0.5, 1.0, -1.0); f["P5"] = f.P5.where(loc.notna()); f["P6"] = -f.P5
    f["P7"] = np.sign(vprev)
    f["P8"] = np.where(pc > ma20, 1.0, -1.0); f["P8"] = f.P8.where(ma20.notna())
    f["P9"] = np.where(pc > ma200, 1.0, -1.0); f["P9"] = f.P9.where(ma200.notna())
    f["real"] = np.sign(c - o)
    return df, f


def main(dry):
    pol = OS.Policy(); out = {}
    for sym in ("NQ", "ES"):
        df, f = features(sym)
        preds = [f"P{i}" for i in range(1, 10)]
        if dry:
            print(sym, "sessions", len(df), "non-missing:", {p: int(f[p].notna().sum() - (f[p] == 0).sum()) for p in preds})
            continue
        recs = df.reset_index().to_dict("records")
        for i, r in enumerate(recs):
            r["f"] = {p: f[p].iloc[i] for p in preds}
        rng = np.random.default_rng(323)
        half = df.index < pd.Timestamp("2023-01-01")
        for p in preds:
            ok = f[p].notna() & (f[p] != 0) & (f.real != 0)
            n = int(ok.sum()); k = int((f[p][ok] == f.real[ok]).sum())
            fn = lambda r, g, p=p: 0 if not np.isfinite(r["f"][p]) or r["f"][p] == 0 else int(r["f"][p])
            starts = range(0, len(recs) - 57)
            res = np.array([R.run_window(recs, s, 57, fn, pol, rng)[0] == "pass" for s in starts], dtype=float)
            hs = np.array(list(starts)); hf = half[hs]
            z = (k - n / 2) / (np.sqrt(n) / 2)
            out[f"{sym}|{p}"] = dict(n=n, hit=k / n, z=float(z), P_pass=float(res.mean()), uplift=float(res.mean() - BASE[sym]),
                                     up_2020_22=float(res[hf].mean() - BASE[sym]), up_2023_26=float(res[~hf].mean() - BASE[sym]))
        print(sym, {p: (round(out[f"{sym}|{p}"]["hit"] * 100, 1), round(out[f"{sym}|{p}"]["P_pass"] * 100, 1)) for p in preds}, flush=True)
    if dry: return
    cand = []
    for p in [f"P{i}" for i in range(1, 10)]:
        a, b_ = out[f"NQ|{p}"], out[f"ES|{p}"]
        ok = all(x["hit"] >= 0.53 and x["uplift"] >= 0.08 and x["up_2020_22"] > 0 and x["up_2023_26"] > 0 for x in (a, b_))
        out[f"cand|{p}"] = bool(ok)
        if ok: cand.append(p)
    print("candidates:", cand)
    json.dump(out, open(R.result_path(HERE, "round323_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
