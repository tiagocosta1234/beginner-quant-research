"""
Daily history updater (2026-09-30): tops up both live_bot history caches from the
broker's 1-minute history, whether or not a bot is running.

Why: live_bot/daily_history.py (the bracket bot's Round 244 POC filter) and
live_bot/session_history.py (the Combined bot's meta-model inputs) only grew while a
bot that uses them was running. The broker keeps 1-minute history for the active
contract only (about two months, less right after a roll), so a stretch with neither
bot running longer than that leaves a hole the broker can no longer fill -- and the
Combined bot would then read the wrong previous session and trailing win rate
without noticing. Run once a day after the close (register_history_updater.ps1 sets
up a Windows scheduled task) and the caches stay continuous.

Read-only: logs in with the BrokerAPI REST client and reads the instrument's contract
id and History/retrieveBars. No realtime hub, no TradingSuite, no orders, no position
or account calls -- safe to run while a bot is trading.

    python -m live_bot.update_history             # update both caches
    python -m live_bot.update_history --dry-run   # report what would be added, write nothing

Exit codes: 0 caches up to date; 1 no bars from the broker; 2 a hole in a cache that
the broker can no longer fill (the log names the dates; rebuild the seeds from fresh
Databento data with futures/engine/build_daily_rth_seed.py and
build_session_seed.py).
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from live_bot.daily_history import (  # noqa: E402
    RTH_END, RTH_START, DailyHistory, completed_sessions, poc_filter_features,
)
from live_bot.session_history import SessionHistory  # noqa: E402

NY = ZoneInfo("America/New_York")
SETTLED = dt.time(16, 5)                  # a session's last bar is final by then
MAX_DAYS = 90                             # the broker holds ~2 months of 1-minute bars anyway
META_PATH = HERE / "state" / "history_updater.json"
LOG_PATH = HERE / "logs" / "update_history.log"
log = logging.getLogger("update_history")


def session_cutoff(now_ny: dt.datetime) -> dt.date:
    """The first session date that is not over yet: today until 16:05 ET, then tomorrow."""
    return now_ny.date() + dt.timedelta(days=1) if now_ny.time() >= SETTLED else now_ny.date()


def to_rth_ny(bars) -> pd.DataFrame:
    """Broker bars (Polars or pandas, with a `timestamp` column or a time index; the SDK
    stamps them tz-aware Central) -> pandas indexed by naive New York time, regular
    session only. Naive timestamps are taken as New York already."""
    df = bars.to_pandas() if hasattr(bars, "to_pandas") else bars.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_convert(NY).tz_localize(None)
    df = df[~df.index.duplicated(keep="last")]
    return df.between_time(RTH_START, RTH_END, inclusive="left")[["open", "high", "low", "close", "volume"]]


def holes(last_known: dt.date | None, new_dates: list[dt.date]) -> list[tuple[dt.date, dt.date, int]]:
    """(from, to, weekdays missing) wherever consecutive sessions are more than one
    weekday apart. One missing weekday is an exchange holiday: in the Databento seed
    only New Year's Day, Good Friday, Christmas and 2025-01-09 are missing -- the other
    US holidays are 13:00 early-close sessions and are present."""
    seq = ([last_known] if last_known is not None else []) + list(new_dates)
    out = []
    for a, b in zip(seq, seq[1:]):
        n = len(pd.bdate_range(a, b)) - 2
        if n > 1:
            out.append((a, b, n))
    return out


async def fetch_from_broker(symbol: str, start: dt.datetime, end: dt.datetime):
    """(1-minute bars, contract id) from the BrokerAPI REST API. Read-only."""
    from dotenv import load_dotenv
    load_dotenv(HERE / ".env")
    from brokerapi_py import BrokerAPI
    async with BrokerAPI.from_env() as client:
        await client.authenticate()
        instrument = await client.get_instrument(symbol)
        bars = await client.get_bars(symbol, interval=1, unit=2, partial=False,
                                     start_time=start.astimezone(dt.timezone.utc),
                                     end_time=end.astimezone(dt.timezone.utc))
    return bars, getattr(instrument, "id", None)


def run(fetch=fetch_from_broker, now: dt.datetime | None = None, dry_run: bool = False,
        symbol: str = "MNQ", max_days: int = MAX_DAYS, meta_path: Path = META_PATH) -> int:
    now_ny = (now or dt.datetime.now(dt.timezone.utc)).astimezone(NY)
    cutoff = session_cutoff(now_ny)
    tag = "DRY RUN: " if dry_run else ""
    daily, sessions = DailyHistory(), SessionHistory(logger=log)
    if dry_run:                                       # read the real files, write to a temp dir
        tmp = Path(tempfile.mkdtemp())
        daily.state_path, sessions.state_path = tmp / "daily.csv", tmp / "sessions.csv"
    last_d = daily.df["date"].iloc[-1] if len(daily.df) else None
    last_s = sessions.df["date"].iloc[-1] if len(sessions.df) else None

    # From the older cache's last session (so the feed can show it is contiguous), at
    # midnight so every session in the window is covered from its open.
    floor = now_ny.date() - dt.timedelta(days=max_days)
    since = max(min(d for d in (last_d, last_s, now_ny.date()) if d is not None), floor)
    start = dt.datetime.combine(since, dt.time(0, 0), NY)
    try:
        bars, contract = asyncio.run(fetch(symbol, start, now_ny))
    except Exception as exc:                          # network, auth, SDK errors
        log.error("%sno bars from the broker: %s: %s", tag, type(exc).__name__, exc)
        return 1
    if bars is None or len(bars) == 0:
        log.error("%sno bars from the broker for %s since %s", tag, symbol, start)
        return 1

    rth = to_rth_ny(bars)
    feed = [d for d, _ in completed_sessions(rth, cutoff)]
    new_d = [d for d in feed if last_d is None or d > last_d]
    new_s = [d for d in feed if last_s is None or d > last_s]
    gaps = {"daily": holes(last_d, new_d), "session": holes(last_s, new_s)}
    changed_d = daily.merge_live(rth, cutoff)
    added_s = sessions.update_from_bars(rth, cutoff)

    log.info("%s%s contract %s | feed %s..%s | %d complete sessions (%s..%s)", tag, symbol, contract,
             rth.index[0] if len(rth) else "-", rth.index[-1] if len(rth) else "-",
             len(feed), feed[0] if feed else "-", feed[-1] if feed else "-")
    log.info("%sdaily cache: +%d new, %d updated from the broker -> %d sessions, last %s",
             tag, len(new_d), changed_d - len(new_d), len(daily.df), daily.df["date"].iloc[-1])
    log.info("%ssession cache: +%d -> %d sessions, last %s, %d POC trades", tag, added_s, len(sessions.df),
             sessions.df["date"].iloc[-1], int(sessions.df["poc_outcome"].notna().sum()))
    feats = poc_filter_features(daily.before(cutoff))
    if feats:
        log.info("%sPOC filter for the session after %s: %s (narrow=%s, lowvol=%s)", tag, feats["last_session"],
                 "PASS" if feats["passed"] else "FAIL", feats["narrow"], feats["lowvol"])

    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    if meta.get("contract") and contract and meta["contract"] != contract:
        log.warning("%scontract changed %s -> %s: sessions from here on come from %s, so the first one "
                    "opens with a price jump against the cached ones. The Databento seed has the same "
                    "jump at every roll (133.75 points on 2025-12-11), and so does the backtest.",
                    tag, meta["contract"], contract, contract)
    for name, found in gaps.items():
        for a, b, n in found:
            log.error("%s%s cache: %d weekdays missing between %s and %s -- the broker no longer has "
                      "them; rebuild the seed from fresh Databento data", tag, name, n, a, b)
    code = 2 if any(gaps.values()) else 0
    if not dry_run:
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(dict(
            run_at=now_ny.isoformat(timespec="seconds"), contract=contract or meta.get("contract"),
            daily_last=str(daily.df["date"].iloc[-1]), session_last=str(sessions.df["date"].iloc[-1]),
            holes=[f"{n}: {a}..{b}" for n, found in gaps.items() for a, b, _ in found], exit_code=code), indent=1))
    return code


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="report what would be added; write nothing")
    ap.add_argument("--max-days", type=int, default=MAX_DAYS)
    args = ap.parse_args(argv)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [logging.FileHandler(LOG_PATH, encoding="utf-8")]
    if sys.stdout is not None:                        # None under pythonw (the scheduled task)
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=handlers)
    for noisy in ("brokerapi_py", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    from dotenv import load_dotenv
    load_dotenv(HERE / ".env")                        # BOT_INSTRUMENT and the API credentials
    try:
        return run(dry_run=args.dry_run, symbol=os.getenv("BOT_INSTRUMENT", "MNQ"), max_days=args.max_days)
    except Exception:                                 # under pythonw nobody sees stderr: keep it in the log
        log.exception("update_history crashed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
