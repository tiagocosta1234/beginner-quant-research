"""
Round 337 (2026-10-03, PRE-REGISTERED; ONE ledger row, k + 1): does the pre-FOMC announcement drift (Round 328's rule, unchanged) appear on the other MT5 broker markets: US30.cash, US2000.cash and XAUUSD?

Round 328 found +31 bp (Databento ES / NQ, 2020-26) and +34.5 bp (MT5 US100 / US500, 2021-10..2026-10, 40 meetings), fading from +94 bp in the first half to +15 bp in the second. If the effect is the published announcement-risk premium it should show on the other US equity indices and
possibly gold; if it is two lucky years on the Nasdaq it should not. Ledger checked first (k = 2038): row 135 (statement day long) and Round 328 only; US30, US2000 and gold are not in the ledger for this window.
DATA: MT5 M1 bid / ask for US30.cash (2021-10..2026-10), US2000.cash (2022-01..2026-10), XAUUSD (2021-10..2026-10), ALL hours (forex/early_mt5/data, via Round 321's _mt5broker_bars); scheduled FOMC statement dates from data/events/fomc_statement_dates.csv within each file's span.
RULE (one, fixed): LONG at the ASK open of the 14:00 ET bar on the trading day before the statement, EXIT at the BID close of the 13:59 ET bar on the statement day. Net bp = (exit - entry) / entry x 1e4 - 0.5 bp (slippage / commission allowance; indices have no commission, gold about 0.3 bp); real spread is paid by the ask / bid fills.
Reported, not counted: US100.cash and US500.cash with the same real-fill rule (Round 328 used bid bars and 1 bp).
CANDIDATE (fixed now), per market: mean net > 0 with date-bootstrap P(>0) >= 1 - 0.05/3 = 0.9833 (10,000 draws, seed 337) AND positive in both halves (meetings before 2024-01-01 / from 2024-01-01). A market passing is a replication on that market; a miss is inconclusive for a 35-40 meeting sample (the s.e. of the mean is about 13-17 bp).
Not widened after the run: no other windows (24-hour is the published one), assets, or exits.
DRY-RUN COUNTS (meetings only, no returns printed): US30.cash 40 meetings (18 before 2024, 22 from 2024); US2000.cash 38 (16 / 22); XAUUSD 40 (18 / 22); US100.cash 40 (18 / 22); US500.cash 40 (18 / 22). A first draft read the ask / bid columns under the wrong names (an AttributeError); fixed before any return was read.
POWER: per-meeting sd about 85-110 bp for the indices and about 60-70 bp for gold, so the s.e. of a market's mean over 38-40 meetings is about 13-17 bp (gold about 10 bp); an effect of +30 bp is about 2 s.e.; halves of 16-22 meetings carry s.e. of 20-25 bp. A miss is inconclusive, not a refutation.
"""
import os, sys, json
os.environ["ROUND_DATA"] = "mt5broker"; os.environ["ROUND_FILLS"] = "ask"
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", ".."))
import round321_long_bias_bold_play as R

R.MT5BROKER_SYMBOL.update({"XAU": "XAUUSD"})
SYMS = {"YM": "US30.cash", "RTY": "US2000.cash", "XAU": "XAUUSD", "NQ": "US100.cash", "ES": "US500.cash"}
COUNTED = ("YM", "RTY", "XAU")
SLIP = 0.5
SPLIT = pd.Timestamp("2024-01-01")


def fomc_dates():
    d = pd.read_csv(os.path.join(HERE, "..", "data", "events", "fomc_statement_dates.csv"), parse_dates=["date"])["date"]
    return [x for x in d if pd.Timestamp("2021-10-01") <= x <= pd.Timestamp("2026-10-03")]


def trades(sym):
    b = R._mt5broker_bars(sym)
    days = pd.DatetimeIndex(sorted(set(b.index.normalize())))
    rows = []
    for d in fomc_dates():
        if d not in days:
            continue
        prev = days[days < d]
        if not len(prev):
            continue
        tin, tout = prev[-1] + pd.Timedelta(hours=14), d + pd.Timedelta(hours=13, minutes=59)
        if tin in b.index and tout in b.index:
            e, x = b.ao[tin], b.c[tout]
            rows.append(dict(date=d, net=(x / e - 1) * 1e4 - SLIP, gross=(b.c[tout] / b.o[tin] - 1) * 1e4))
    return pd.DataFrame(rows)


def boot(x, rng):
    v = x.values; idx = rng.integers(0, len(v), (10000, len(v)))
    return float(v.mean()), float((v[idx].mean(1) > 0).mean())


def main(dry):
    rng = np.random.default_rng(337); out = {}
    for s in COUNTED + ("NQ", "ES"):
        t = trades(s)
        if dry:
            print(f"{SYMS[s]}: {len(t)} meetings from {t.date.min().date()} to {t.date.max().date()}, before 2024 {(t.date < SPLIT).sum()}, from 2024 {(t.date >= SPLIT).sum()}"); continue
        a, b = t[t.date < SPLIT], t[t.date >= SPLIT]
        m, p = boot(t.net, rng); ma, pa = boot(a.net, rng); mb, pb = boot(b.net, rng)
        out[SYMS[s]] = dict(n=len(t), net_bp=m, P=p, gross_bp=float(t.gross.mean()), first=ma, second=mb, sd=float(t.net.std()),
                            candidate=bool(s in COUNTED and m > 0 and p >= 1 - .05 / 3 and ma > 0 and mb > 0))
        print(SYMS[s], {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out[SYMS[s]].items()})
    if not dry:
        print("replicates on:", [k for k, v in out.items() if v["candidate"]])
        json.dump(out, open(os.path.join(HERE, "round337_results_mt5broker_ask.json"), "w"), indent=1)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
