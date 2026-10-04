"""
Round 326 (2026-10-03, PRE-REGISTERED; the 4 cells are logged as ONE ledger row, k + 1): does the multi-hour CONTINUATION seen post hoc on ES / NQ in 2024-2026 (Round 325 placebo: +6 to +13 bp OOS) replicate on gold and silver?

Round 325's placebo (continuation after a >= 2 sigma 120 / 180-minute move) earned +6 to +13 bp OOS but its IS counterpart was flat or negative: a sign flip between periods, found by looking at results (post hoc). The honest test of a post-hoc
pattern is an independent sample: a different asset class, same clock. No parameter is changed from Round 325 and none is tuned. Ledger checked first (k = 2028): intraday continuation on GC / SI at 2-3 hour horizons is not in the ledger.

DATA: Databento 1-minute GC and SI (2020-01-02..2026-09-25), RTH clock 09:30-15:59 ET, sigma / z / decision times exactly as Round 325 (build() reused, per-instrument costs GC 1.5 bp, SI 3.0 bp instead of 1.0).
RULES (continuation = the OPPOSITE of Round 325's reversal rules): after the first z <= -2 move over L minutes, SHORT (CONT_DOWN); after the first z >= +2, LONG (CONT_UP); hold M minutes. L in {120, 180}, M in {60, 120}: 4 cells per
direction pooled together (each cell = CONT_DOWN and CONT_UP trades of that (L, M), pooled over GC + SI). Net bp = direction x return x 1e4 - cost.
SPLIT: IS 2020-2023, OOS 2024-2026-09 (the period in which ES / NQ continuation appeared, so OOS here is NOT independent in time; the IS half is the real test: continuation must also be positive in IS).
CANDIDATE (fixed now): IS mean > 0 with P >= 0.95 AND OOS mean > 0 with P >= 1 - 0.05/4 = 0.9875. Not widened after the run.
DRY-RUN COUNTS (trade counts only): pooled GC + SI trades IS / OOS: L120 (M60 and M120 share entries) 559 / 389 (SI 483, GC 465), L180 407 / 261 (SI 336, GC 332). Cost is set through Round 325's module constant per instrument before each build.
POWER: per-trade sd about 30-45 bp, so the s.e. of an IS mean is about 1.5-2.2 bp and of an OOS mean about 1.9-2.8 bp; an edge above about +5 bp net is detectable.
"""
import os, sys, json
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import round325_intraday_dip_reversal as Q

COSTS = {"GC": 1.5, "SI": 3.0}
IS_END = pd.Timestamp("2023-12-31")


def trades():
    out = []
    for sym, c in COSTS.items():
        Q.COST = c
        d = Q.build(sym)
        d = d[d.L.isin((120, 180))].copy()
        d["net"] = d.plc          # the opposite direction of Round 325's rule at this cost
        d["sym"] = sym
        out.append(d)
    return pd.concat(out)


def main(dry):
    df = trades(); rng = np.random.default_rng(326); out = {}
    for L in (120, 180):
        for M in (60, 120):
            x = df[(df.L == L) & (df.M == M)]
            a, b = x[x.date <= IS_END], x[x.date > IS_END]
            if dry:
                print(f"L{L} M{M}: trades IS {len(a)} OOS {len(b)} (symbols {dict(x.sym.value_counts())})"); continue
            mi, pi = Q.boot(a, rng); mo, po = Q.boot(b, rng)
            out[f"L{L}|M{M}"] = dict(n_is=len(a), n_oos=len(b), is_bp=mi, is_P=pi, oos_bp=mo, oos_P=po,
                                     candidate=bool(mi > 0 and pi >= .95 and mo > 0 and po >= 1 - .05 / 4))
            print(f"L{L} M{M}", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out[f"L{L}|M{M}"].items()})
    if not dry:
        print("candidates:", [k for k, v in out.items() if v["candidate"]])
        json.dump(out, open(os.path.join(HERE, "round326_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
