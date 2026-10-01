"""
Round 251 (2026-10-01): ONE hypothesis from Round 250, tested only on data never used for it.
the trader: "one last cheap check". PRE-REGISTRATION -- written before any of the data below is read.

THE RULE (exactly Round 250's strongest lean, X2 / slot 11, continuation): at 15:00 New York, let
X = price at the 15:00 bar open - price at the 09:30 bar open. If X > 0 go long, if X < 0 go short,
from the 15:00 bar open to the 15:29 bar close. Days without all three bars (early closes,
gaps) are skipped. Returns are divided by the trailing 60-session sd of this slot's return
(>= 40 sessions, known before the day), as in Round 250.

UNTOUCHED SAMPLES (none was used by Round 250, which saw US100.cash 2021-10..2025-06 only):
  NQ   Databento NQ.F 1-min, 2019-10-01 .. 2021-09-30 (before the CFD history starts). Gross, and net of
       MNQ's $2.24 round trip = 1.12 NQ points.
  ES   Databento ES.F 1-min, same period -- replication on a different market. Net of MES's $3.74
       = 0.748 ES points.
  CFD  MT5 US100.cash, 2025-07-01 .. 2026-09-30 (Round 250's untouched OOS), real bid/ask fills
       (long: ask at the 15:00 open -> bid at the 15:29 close; short: mirror), Round 250's slot table.
Futures are unadjusted continuous front months: days inside a roll window (roll Thursday, 8 days
before the third Friday of Mar/Jun/Sep/Dec, +-2 days) are excluded. Timestamps are UTC
start-stamped -> New York.

CONFIRMED (all three, one-sided bootstrap P(mean > 0), 20,000 resamples, seed 251):
  (a) NQ gross mean > 0 with P >= 0.95;
  (b) ES gross mean > 0 with P >= 0.90;
  (c) CFD net mean > 0 with P >= 0.95.
Anything less: NOT confirmed. Also reported (descriptive): net for NQ/ES, trade counts, and the
daily Sharpe the rule would add. A confirmed result is a LEAD to combine with the POC leg in a later
pre-registered round, not a strategy on its own.

POWER NOTES (--dry-run, counts only): NQ 422 trades and ES 428 (2019-11-26..2021-09-30,
after the 40-session sd warm-up and the roll windows); CFD 312 (2025-07-01..2026-09-30).
If the true effect were Round 250's IS estimate (+0.113 sd gross), NQ would show t ~ 2.3;
Round 250's number is the maximum of 76, so the true effect is likely smaller (winner's curse)
and a pass on all three is unlikely unless the effect is real and sizeable.
"""
import os, sys, json, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import numpy as np
import pandas as pd
import idea_harness as H
import round250_us100_slot_scan as R250

FUT = {"NQ": dict(file="futures_NQ.F_1m.parquet", cost_pts=2.24 / 2.0), "ES": dict(file="futures_ES.F_1m.parquet", cost_pts=3.74 / 5.0)}
FUT_START, FUT_END = pd.Timestamp("2019-10-01"), pd.Timestamp("2021-09-30")
CFD_START = pd.Timestamp("2025-07-01")
SD_WIN, SD_MIN, N_BOOT, SEED = 60, 40, 20_000, 251


def roll_days():
    out = set()
    for y in range(2019, 2027):
        for m in (3, 6, 9, 12):
            first = pd.Timestamp(y, m, 1)
            thu = first + pd.Timedelta(days=(4 - first.weekday()) % 7 + 14) - pd.Timedelta(days=8)
            for k in range(-2, 3):
                out.add((thu + pd.Timedelta(days=k)).normalize())
    return out


def futures_trades(sym):
    df = pd.read_parquet(os.path.join(HERE, "..", "data", "databento", FUT[sym]["file"]), columns=["ts", "open", "close"])
    t = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    s = pd.DataFrame({"open": df["open"].to_numpy(), "close": df["close"].to_numpy()}, index=pd.DatetimeIndex(t))
    s = s[~s.index.duplicated(keep="first")]
    hm = s.index.strftime("%H:%M")
    o930 = s["open"][hm == "09:30"]; o1500 = s["open"][hm == "15:00"]; c1529 = s["close"][hm == "15:29"]
    o930.index, o1500.index, c1529.index = (x.index.normalize() for x in (o930, o1500, c1529))
    d = pd.concat([o930.rename("o930"), o1500.rename("o1500"), c1529.rename("c1529")], axis=1).dropna()
    d["r"] = d["c1529"] - d["o1500"]
    d["sd"] = d["r"].shift(1).rolling(SD_WIN, min_periods=SD_MIN).std()
    d["x"] = d["o1500"] - d["o930"]
    rolls = roll_days()
    d = d[(d.index >= FUT_START) & (d.index <= FUT_END) & ~d.index.isin(list(rolls))].dropna()
    d = d[d["x"] != 0]
    sg = np.sign(d["x"])
    return pd.DataFrame({"gross": sg * d["r"] / d["sd"], "net": (sg * d["r"] - FUT[sym]["cost_pts"]) / d["sd"]}, index=d.index)


def cfd_trades():
    df = R250.load()
    T = R250.slot_table(df)
    days, W, sd, X, P = R250.add_predictors(T)
    x = X["X2_day_so_far"][11]
    ok = x.notna() & (x != 0) & sd[11].notna() & W[11].notna() & (days >= CFD_START)
    sg = np.sign(x[ok])
    net = np.where(sg > 0, P["long_net"][11][ok], P["short_net"][11][ok]) / sd[11][ok]
    return pd.DataFrame({"gross": sg * W[11][ok] / sd[11][ok], "net": net}, index=x[ok].index)


def boot_p(v):
    v = np.asarray(v, float)
    rng = np.random.default_rng(SEED)
    return float((rng.choice(v, (N_BOOT, len(v))).mean(1) > 0).mean())


def main(dry):
    samples = {"NQ": futures_trades("NQ"), "ES": futures_trades("ES"), "CFD": cfd_trades()}
    for k, v in samples.items():
        print(f"{k}: {len(v)} trades, {v.index.min().date()}..{v.index.max().date()}")
    if dry:
        return
    res = {}
    for k, v in samples.items():
        res[k] = dict(n=len(v), gross=float(v["gross"].mean()), net=float(v["net"].mean()),
                      p_gross=boot_p(v["gross"]), p_net=boot_p(v["net"]), sharpe_trade_net=float(v["net"].mean() / v["net"].std()))
        print(f"  {k}: gross {res[k]['gross']:+.4f} sd (P {res[k]['p_gross']:.3f}) | net {res[k]['net']:+.4f} sd (P {res[k]['p_net']:.3f}) "
              f"| per-trade Sharpe net {res[k]['sharpe_trade_net']:+.3f}")
    checks = {"a_NQ_gross_P>=0.95": res["NQ"]["gross"] > 0 and res["NQ"]["p_gross"] >= 0.95,
              "b_ES_gross_P>=0.90": res["ES"]["gross"] > 0 and res["ES"]["p_gross"] >= 0.90,
              "c_CFD_net_P>=0.95": res["CFD"]["net"] > 0 and res["CFD"]["p_net"] >= 0.95}
    verdict = "CONFIRMED (lead)" if all(checks.values()) else "NOT confirmed"
    print("=== Pre-registered ===")
    for c, v in checks.items():
        print(f"  {c}: {'PASS' if v else 'FAIL'}")
    print(f"  VERDICT: {verdict}")
    json.dump(dict(results=res, checks=checks, verdict=verdict), open(os.path.join(HERE, "round251_results.json"), "w"), indent=1)
    print("Saved round251_results.json")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    main(ap.parse_args().dry_run)
