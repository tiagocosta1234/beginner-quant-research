"""
Round 171: the trader exported real 1-minute data from Databento for ES, NQ, GC
and SI (full-size futures, continuous front-month), 2019-06/10 through
2026-09-25 -- verified clean before using it: zero duplicate timestamps,
zero zero-volume bars, and the only >3% 1-minute moves cluster on genuinely
volatile real days (2020-03 COVID crash, 2025-04-06), not on a quarterly
roll schedule -- no unhandled roll-jump artifact. This is a real upgrade,
not just more of the same: SI in particular has been the campaign's weakest
data source all along (Yahoo daily SI=F is usable only in 2011 per this
repo's own documented gotcha; the BrokerAPI SIL pull is ~2 months). This
gives SI ~7 years of clean 1-minute data for the first time.

The single highest-value use of it right now: Round 167 found a real
dose-response for volume-confirmed opening-range breakouts on MNQ+MGC, but
Rounds 168-169 found it doesn't generalize to other levels and doesn't
survive extending its own threshold past 2.5x -- weakening, without
killing, the finding. This data makes a genuine out-of-sample replication
possible for the first time: ES/NQ/GC track MNQ/MGC almost exactly (same
underlying, different contract size) and SI is a new instrument entirely,
and importantly most of this data (2019-06 through 2022-12) PRE-DATES
MNQ/MGC's own extended history and was never touched by Round 167-169 in
any way -- a real replication, not a re-slice of the same trades.

Rule: identical to Round 167/169's ORB (round167.orb_signals, unmodified):
first 15-min RTH range (09:30-09:45 ET), first breakout confirmed by volume
>= a multiple of the range's own average bar volume, stop at the opposite
side, target = 2x that stop (Round 167's best-performing exit), flat by
16:00 ET. Same 3 volume thresholds as Round 167 (0/1.5x/2.5x), not re-picked.
ES/NQ/GC/SI point values and tick sizes (real CME full-size contract specs,
not the Broker micros already in idea_harness.PV/TK): ES $50/pt tick 0.25;
NQ $20/pt tick 0.25; GC $100/pt tick 0.10; SI $5,000/pt tick 0.005.

Two cuts per symbol: the full 2019-2026 span, and the 2019-2022-12 slice
that pre-dates every MNQ/MGC test in this ledger -- the cleanest possible
out-of-sample check on whether the ORB volume effect is real.

4 symbols x 3 vol thresholds x 2 cuts = 24 variants. Ledger k=250 -> 274;
OOS bar 1 - 0.01/274 at the last variant.

Candidate (each variant): idea_harness.test_idea's own rule (positive net
and gross; IS P(edge>0) >= 0.95; OOS P(edge>0) >= the bar at that variant's k).
Note: idea_harness.test_idea's own IS/OOS split (2025-07-01) still applies
within each cut -- the "pre-2022-12" cut's own internal split just has a
much smaller OOS tail (2025-07 to 2022-12-31 doesn't exist, so within that
cut IS ends up being almost everything and OOS is empty/tiny for it; report
descriptively for that cut and let the FULL 2019-2026 cut carry the formal
candidate judgment, exactly as every other round in this ledger does).
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
from round167_volume_confirmed_orb import orb_signals

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(HERE, "..", "data", "databento")
FLAT_TIME = dt.time(16, 0)

# Real CME full-size contract specs (not the Broker micros already in idea_harness.PV/TK).
H.PV.update({"ES": 50.0, "NQ": 20.0, "GC": 100.0, "SI": 5000.0})
H.TK.update({"ES": 0.25, "NQ": 0.25, "GC": 0.10, "SI": 0.005})
FILES = {"ES": "futures_ES.F_1m.parquet", "NQ": "futures_NQ.F_1m.parquet",
         "GC": "futures_GC.F_1m.parquet", "SI": "futures_SI.F_1m.parquet"}

_DAYS_CACHE = {}


def load_days_databento(sym):
    if sym in _DAYS_CACHE:
        return _DAYS_CACHE[sym]
    df = pd.read_parquet(os.path.join(DB_DIR, FILES[sym]))
    idx = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    bars = pd.DataFrame({"open": df["open"].values, "high": df["high"].values, "low": df["low"].values,
                         "close": df["close"].values, "vol": df["volume"].values}, index=idx).sort_index()
    bars = bars[~bars.index.duplicated(keep="first")]
    bars["tday"] = (bars.index + pd.Timedelta(hours=6)).normalize()
    t = bars.index.time
    is_rth = (t >= H.T_RTH_OPEN) & (t <= H.T_RTH_CLOSE)
    days = [dict(tday=tday, on=g[~is_rth[bars.index.get_indexer(g.index)]],
                session=g[is_rth[bars.index.get_indexer(g.index)]])
            for tday, g in bars.groupby(bars["tday"])]
    _DAYS_CACHE[sym] = days
    return days


def build_trades(sym, vol_mult, rr, cutoff=None):
    days = load_days_databento(sym)
    if cutoff is not None:
        days = [d for d in days if d["tday"] < cutoff]
    if not days:
        return pd.DataFrame(columns=["entry_ts", "exit_ts", "direction", "contracts", "pnl", "r"]), days
    bars = pd.concat([d[k] for d in days for k in ("on", "session")]).sort_index()
    sig = orb_signals(days, sym, vol_mult, rr)
    tr = H.resolve_bracket(sig, bars, sym, flat_time=FLAT_TIME)
    tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
    return tr, days


RR = 2.0
VOL_MULTS = [0.0, 1.5, 2.5]
PRE_2023 = pd.Timestamp("2023-01-01")

if __name__ == "__main__":
    dry = "--dry-run" in sys.argv

    if dry:
        for sym in FILES:
            days = load_days_databento(sym)
            print(f"{sym}: {len(days)} days, {days[0]['tday'].date()} -> {days[-1]['tday'].date()}")
            for vm in VOL_MULTS:
                tr, _ = build_trades(sym, vm, RR)
                pre_tr, pre_days = build_trades(sym, vm, RR, cutoff=PRE_2023)
                print(f"  vol>={vm}x: {len(tr)} trades full-span, {len(pre_tr)} trades pre-2023 "
                      f"({len(pre_days)} pre-2023 days)")
        print("\n--dry-run: counts only (trades ARE resolved for real, just not logged). Hand-check before the real run.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    rows = []
    for sym in FILES:
        for vm in VOL_MULTS:
            for cutoff, cut_label in [(None, "full 2019-2026"), (PRE_2023, "pre-2023 (never used before)")]:
                tr, days = build_trades(sym, vm, RR, cutoff=cutoff)
                if tr.empty:
                    continue
                k = H.ledger_count() + 1
                all_days = [d["tday"] for d in days]
                name = f"VCORB 2R, >={vm}x OR-avg vol, {sym} (Databento, {cut_label})"
                r = H.test_idea(name, tr, all_days, sym, k)
                rows.append(r)
                lines = H.ledger_rows([r], "Round 171 (pre-registered, out-of-sample ORB replication on Databento data)",
                                       commit, date="2026-09-27")
                with open(H.LEDGER, "a", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round171_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
