"""
Round 328 (2026-10-03, PRE-REGISTERED; the 2 hypotheses are logged as ONE ledger row, k + 1): the pre-FOMC announcement drift (Lucca and Moskowitz 2015) on ES and NQ, 2020-2026.

Mechanism (published, with a stated reason): equities earn an abnormal return in the ~24 hours before scheduled FOMC statements, attributed to risk-premium compensation for announcement uncertainty. Ledger checked first (k = 2030): row 135 tested
the statement DAY long (open-to-close, which includes the post-announcement reaction, IS P 1.00 / OOS 0.247); the pre-announcement window itself (14:00 the day before -> 13:59 on the day) is not in the ledger. It is sparse (about 8 trades a year),
so it cannot by itself beat the 1-Step pass rate; it is tested because it is a documented effect with a mechanism and because it would be a clean add-on sleeve.

DATA: Databento 1-minute ES and NQ INCLUDING the Globex overnight session (2020-01-02..2026-09-25); scheduled FOMC statement dates from data/events/fomc_statement_dates.csv (215 dates, 2000-2026; those in 2020-2026 are used).
H1 (24-hour window): long at the open of the 14:00 ET bar on the trading day BEFORE the statement day, exit at the close of the 13:59 ET bar on the statement day. H2 (same-day window): long at the 09:30 open of the statement day, exit at the 13:59 close.
Net bp = return x 1e4 - 1.0 (round trip). Pooled over ES + NQ (two trades per meeting, clustered by date). Missing bars on a date drop that date for that instrument.
SPLIT: first half = meetings before 2023-01-01, second half = from 2023-01-01; statistic: mean net bp, date-clustered bootstrap (10,000 draws, seed 328).
CANDIDATE (fixed now), per hypothesis: pooled mean > 0 with P >= 1 - 0.05/2 = 0.975 AND positive in both halves. (Power note: with about 50 meetings the s.e. of the mean is about 12-15 bp: only an effect near +35 bp or more can be distinguished.) Not widened after the run.
DRY-RUN COUNTS (no P&L): 53 scheduled meetings 2020-01-02..2026-09-25 with complete bars for both instruments (23 before 2023, 30 from 2023), 106 trades per hypothesis (ES 53, NQ 53). 'Previous trading day' is the previous calendar day that has
bars; statement days are Tuesdays / Wednesdays so it is never a Sunday. Unscheduled meetings (e.g. 2020-03-15) are not in the date file and are not traded.
POWER: per-trade sd about 80-110 bp over 24 hours, so the s.e. of the pooled mean over 53 clustered meetings is about 12-15 bp; an effect of +30 bp is about 2 s.e.
"""
import os, sys, json
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "data", "databento")
COST = 1.0


def bars(sym):
    if os.environ.get("ROUND_DATA") == "mt5broker":                      # MT5 M1 bid bars incl. the overnight session
        sys.path.insert(0, os.path.join(HERE, "..", ".."))
        import round321_long_bias_bold_play as R321
        return R321._mt5broker_bars(sym)[["o", "c"]]
    df = pd.read_parquet(os.path.join(DB, f"futures_{sym}.F_1m.parquet"))
    idx = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    b = pd.DataFrame({"o": df["open"].values, "c": df["close"].values}, index=idx).sort_index()
    return b[~b.index.duplicated(keep="first")]


def fomc_dates():
    d = pd.read_csv(os.path.join(HERE, "..", "data", "events", "fomc_statement_dates.csv"), parse_dates=["date"])["date"]
    return [x for x in d if pd.Timestamp("2020-01-02") <= x <= pd.Timestamp("2026-09-25")]


def trades(sym):
    b = bars(sym); rows = []
    days = pd.DatetimeIndex(sorted(set(b.index.normalize())))
    for d in fomc_dates():
        if d not in days:
            continue
        prev = days[days < d][-1]            # previous calendar day with bars (trading day)
        t_in1 = prev + pd.Timedelta(hours=14); t_out = d + pd.Timedelta(hours=13, minutes=59)
        t_in2 = d + pd.Timedelta(hours=9, minutes=30)
        for name, tin in (("H1", t_in1), ("H2", t_in2)):
            if tin in b.index and t_out in b.index:
                rows.append(dict(date=d, sym=sym, h=name, net=(b.c[t_out] / b.o[tin] - 1) * 1e4 - COST))
    return pd.DataFrame(rows)


def boot(x, rng):
    g = x.groupby("date")["net"].agg(["sum", "count"])
    idx = rng.integers(0, len(g), (10000, len(g)))
    m = g["sum"].values[idx].sum(1) / g["count"].values[idx].sum(1)
    return float(x.net.mean()), float((m > 0).mean())


def main(dry):
    df = pd.concat([trades(s) for s in ("ES", "NQ")])
    rng = np.random.default_rng(328); out = {}
    for h in ("H1", "H2"):
        x = df[df.h == h]
        a, b = x[x.date < "2023-01-01"], x[x.date >= "2023-01-01"]
        if dry:
            print(h, f"trades {len(x)} (ES {int((x.sym=='ES').sum())}, NQ {int((x.sym=='NQ').sum())}), meetings {x.date.nunique()}, first half {a.date.nunique()} meetings, second half {b.date.nunique()}"); continue
        m, p = boot(x, rng); ma, pa = boot(a, rng); mb, pb = boot(b, rng)
        out[h] = dict(n=len(x), meetings=int(x.date.nunique()), mean_bp=m, P=p, first_bp=ma, first_P=pa, second_bp=mb, second_P=pb,
                      sd=float(x.net.std()), candidate=bool(m > 0 and p >= .975 and ma > 0 and mb > 0))
        print(h, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out[h].items()})
    if not dry:
        print("candidates:", [k for k, v in out.items() if v["candidate"]])
        json.dump(out, open(os.path.join(HERE, "round328_results" + ("_mt5broker" if os.environ.get("ROUND_DATA") == "mt5broker" else "") + ".json"), "w"), indent=1)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
