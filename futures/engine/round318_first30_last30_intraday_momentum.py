"""
Round 318 (2026-10-03, PRE-REGISTERED): does the first 30 minutes' return predict the last 30 minutes' return (Gao, Han, Li, Zhou intraday momentum), on ES, NQ, GC and SI?

Ledger checked first (k = 2018): Round 122 (ledger 19-21) tested prev-close -> 10:00 and prev-close -> 15:30 signals on a different layout; the pure
"09:30-10:00 return -> trade 15:30-16:00" form and silver on 1-minute data are NOT in the ledger. The brainstorm that fails the pass-speed gate in advance: at most one trade a day, a
last-half-hour move of a few basis points, so even a real edge produces few R a month. This round is about whether a real edge exists, not about the 10% month.

Data: Databento 1-minute ES, NQ, GC, SI (start-stamped, UTC -> New York), 2020-01-02 .. 2026-09-25, regular days with both bars present.
SIGNAL r1 = close of the 09:59 bar / open of the 09:30 bar - 1 (the same 09:30-10:00 clock on all four; for GC and SI this is the COMEX-open-after window, noted as a weaker mechanism).
TRADE: enter at the OPEN of the 15:30 bar, exit at the CLOSE of the 15:59 bar. Net bp = direction x return x 1e4 - cost.
COST per round trip in bp (conservative, fixed before any result): ES 1.0, NQ 1.0, GC 1.5, SI 3.0.
HYPOTHESES (4, family k_new = 4): group EQ = ES + NQ pooled, group MT = GC + SI pooled; V1 = every day, direction = sign(r1) (momentum); V2 = only days with |r1| in the top third of
  its own trailing 60 days (strictly past days), direction = sign(r1). Mirrored bet (opposite sign) reported as placebo only.
SPLIT: IS = 2020-01-02 .. 2023-12-31, OOS = 2024-01-01 onward. Statistic: mean net bp per trade, date-clustered bootstrap (5,000 draws, seed 318).
CANDIDATE: net mean > 0 in IS with P(mean>0) >= 0.95 AND OOS net mean > 0 with P >= 1 - 0.05/4 (Bonferroni on the four hypotheses). Not widened after the run: no new windows,
thresholds, instruments or filters to rescue a failure. Ledger rows (4) are appended by hand after the run.

DRY-RUN COUNTS (no P&L read; hand-check: ES 2023-01-03 open 09:30 = 3881.0 matches the raw bar, r1 = -69.6 bp): trades IS / OOS: EQ V1 1,990 / 1,342 (1,000 / 671 days), EQ V2 590 / 473,
MT V1 1,921 / 1,318, MT V2 609 / 452. Mean |last-30-min move| on ES is 20.5 bp, so a fixed 1 bp cost is small against the move; the test is about direction only.
POWER: per-trade sd about 25 bp (EQ) so the s.e. of the OOS mean is about 0.7 bp (V1) and 1.1 bp (V2): an edge above about +2 bp net is detectable; the Bonferroni OOS bar needs P >= 0.9875.
NO bugs found in the dry run; the first execution of this file for P&L is the run after this commit.
"""
import os, sys, json
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "data", "databento")
COST = {"ES": 1.0, "NQ": 1.0, "GC": 1.5, "SI": 3.0}
GROUPS = {"EQ": ["ES", "NQ"], "MT": ["GC", "SI"]}
IS_END = pd.Timestamp("2023-12-31")


def days(sym):
    df = pd.read_parquet(os.path.join(DB, f"futures_{sym}.F_1m.parquet"))
    idx = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    b = pd.DataFrame({"o": df["open"].values, "c": df["close"].values}, index=idx).sort_index()
    b = b[~b.index.duplicated(keep="first")]
    b = b[b.index.dayofweek < 5]
    mins = b.index.hour * 60 + b.index.minute
    def pick(m, col):
        s = b[col][mins == m]; s.index = s.index.normalize(); return s
    o930, c959, o1530, c1559 = pick(570, "o"), pick(599, "c"), pick(930, "o"), pick(959, "c")
    d = pd.concat([o930, c959, o1530, c1559], axis=1, keys=["o930", "c959", "o1530", "c1559"]).dropna()
    d = d[d.index >= "2020-01-02"]
    d["r1"] = d.c959 / d.o930 - 1
    d["r2"] = d.c1559 / d.o1530 - 1
    d["top"] = d.r1.abs() >= d.r1.abs().rolling(60).apply(lambda x: np.quantile(x, 2 / 3), raw=True).shift(1)
    d["sym"] = sym
    return d


def trades(group, variant):
    out = []
    for s in GROUPS[group]:
        d = days(s)
        if variant == "V2":
            d = d[d.top & d.top.notna()]
        d = d.assign(net=np.sign(d.r1) * d.r2 * 1e4 - COST[s], plc=-np.sign(d.r1) * d.r2 * 1e4 - COST[s])
        out.append(d[["sym", "net", "plc"]])
    return pd.concat(out).sort_index()


def boot(x, rng):
    dates = x.index.unique()
    g = x.groupby(level=0)["net"].agg(["sum", "count"])
    sums, cnts = g["sum"].values, g["count"].values
    idx = rng.integers(0, len(g), (5000, len(g)))
    m = sums[idx].sum(1) / cnts[idx].sum(1)
    return float(x.net.mean()), float((m > 0).mean())


def main(dry):
    rng = np.random.default_rng(318)
    res = {}
    for grp in GROUPS:
        for v in ("V1", "V2"):
            t = trades(grp, v)
            ins, oos = t[t.index <= IS_END], t[t.index > IS_END]
            if dry:
                print(f"{grp} {v}: trades IS {len(ins)} OOS {len(oos)} (days IS {ins.index.nunique()} OOS {oos.index.nunique()}), symbols {dict(t.sym.value_counts())}")
                continue
            mi, pi = boot(ins, rng); mo, po = boot(oos, rng)
            pl = t.assign(net=t.plc)
            res[f"{grp}|{v}"] = dict(n_is=len(ins), n_oos=len(oos), is_bp=mi, is_P=pi, oos_bp=mo, oos_P=po,
                                   placebo_is=float(pl[pl.index <= IS_END].net.mean()), placebo_oos=float(pl[pl.index > IS_END].net.mean()),
                                   gross_oos=float(oos.net.mean() + np.mean([COST[s] for s in oos.sym])),
                                   candidate=bool(mi > 0 and pi >= .95 and mo > 0 and po >= 1 - .05 / 4))
            print(grp, v, {k: (round(x, 3) if isinstance(x, float) else x) for k, x in res[f"{grp}|{v}"].items()})
    if not dry:
        json.dump(res, open(os.path.join(HERE, "round318_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
