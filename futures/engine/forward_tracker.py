"""
Forward paper-tracking for the two open leads CURRENT_STATE.md flags as the
only test left that past data can't replace, and that costs nothing:
  (1) the dip-buy family (Connors RSI(2) < 10, long the next day, on ES/YM/RTY/NQ)
  (2) fading the first break of the 08:30 news range (Round 152's exact rule)
Both are pre-registered, unchanged, exactly as committed in Rounds 142/152 --
this script only ever ADDS rows for real days that occur strictly after
TRACKING_START (2026-09-26, the day both leads were named as worth logging).
It never edits a past row and never changes either rule after seeing a result.

Run this periodically (each session is fine) once real trading days have
passed. It pulls whatever local data is on disk -- run
`refresh_extended_forward.py`-equivalent (a fresh BrokerAPI pull merged into
data/nasdaq_extended and data/gold_extended) first if the files are stale;
this script does not fetch anything itself, so it is safe to run offline.

Output: appends to futures/docs/FORWARD_TRACKING_LOG.md, a plain,
append-only ledger separate from IDEA_LEDGER.md (that one is for backtests;
this one is for real, live walk-forward days that were literally in the
future when each lead was named).
"""
import os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
from round142_batch_j import connors
from round145_batch_l import ohlc_frame
from round151_batch_q import NEWS_T, NEWS_END, MAX_COST_R
from round152_news_fade import news_fade

TRACKING_START = pd.Timestamp("2026-09-26")
LOG_PATH = os.path.join(H.HERE, "..", "docs", "FORWARD_TRACKING_LOG.md")


def already_logged_dates():
    if not os.path.exists(LOG_PATH):
        return set()
    out = set()
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            if line.startswith("| ") and line[2:12].count("-") == 2:
                out.add(line[2:12])
    return out


def check_news_fade():
    """Round 152's exact rule, re-run only on days after TRACKING_START."""
    data = {}
    for sym in ("MNQ", "MGC"):
        days = [d for d in H.load_days(sym) if d["tday"] > TRACKING_START]
        if not days:
            continue
        data[sym] = (days, H.bars_from_days(days, "all"))
    if not data:
        return []
    tr = news_fade(data)
    tr = tr[pd.to_datetime(tr["entry_ts"]) > TRACKING_START]
    rows = []
    for r in tr.itertuples(index=False):
        rows.append((pd.Timestamp(r.entry_ts).date(), "08:30 news fade", r.sym if hasattr(r, "sym") else "?",
                     f"pnl ${r.pnl:+.2f} ({r.r:+.2f}R)"))
    return rows


def check_dip_buy_family():
    """Connors RSI(2) < 10, exactly as Round 142/144 defined it: a real position
    series (enter when RSI(2)<10 & price>MA200, exit when price>MA5 or after 10
    days), not a single next-day trade. Reports each new real day's own
    contribution: whether the strategy was in position that day (a position
    opened on day t-1's signal earns day t's return), and that day's real r."""
    rows = []
    for sym in ("ES=F", "YM=F", "RTY=F", "NQ=F"):
        f = ohlc_frame(sym)  # needs the FULL history for RSI2/MA200 to be correct
        pos = connors(f, 10)
        recent_days = f.index[f.index > TRACKING_START]
        for d in recent_days:
            i = f.index.get_loc(d)
            in_position = bool(pos.iloc[i])
            day_r = float(f["r"].iloc[i])
            rows.append((d.date(), "dip-buy (Connors RSI(2)<10)", sym,
                         f"in_position={in_position}, day_r={day_r:+.4f}"
                         + (f", contributed {day_r*100:+.3f}%" if in_position else "")))
    return rows


if __name__ == "__main__":
    logged = already_logged_dates()
    new_rows = check_news_fade() + check_dip_buy_family()
    new_rows = [r for r in new_rows if str(r[0]) not in logged]

    print(f"Tracking start: {TRACKING_START.date()}. Real days available beyond it: checked live.")
    if not new_rows:
        print("No new forward-tracking rows yet -- no qualifying real trading day has occurred "
              "since the tracking start date, or the local data hasn't caught up to it.")
    else:
        write_header = not os.path.exists(LOG_PATH)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            if write_header:
                f.write("# Forward Tracking Log\n\n"
                        "Real, walk-forward days for the two open leads named in "
                        "`Knowledge_Base/CURRENT_STATE.md` (2026-09-26) -- never backtested, "
                        "added only after each real day actually happened. Append-only; a row "
                        "is never edited after it's written.\n\n"
                        "| date | lead | market | result |\n|---|---|---|---|\n")
            for d, lead, sym, result in sorted(new_rows):
                f.write(f"| {d} | {lead} | {sym} | {result} |\n")
                print(f"  logged: {d} | {lead} | {sym} | {result}")
        print(f"\nAppended {len(new_rows)} new row(s) to {LOG_PATH}")
