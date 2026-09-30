"""Plain-Python tests for update_history.py and the shared session-completeness rule
(daily_history.completed_sessions). No pytest dependency, no network (a fake broker
fetch), temporary files only -- never the real seeds or state.

Run with: python live_bot/tests/test_update_history.py

Added 2026-09-30 with the daily updater. The completeness checks fail on the old
"a bar at/after 15:55" rule: it dropped 13:00 early-close sessions (the Databento
seeds include ~9 a year) and let in a session the feed window cut off at the start.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

TMP = Path(tempfile.mkdtemp())
for k, name in (("COMBINED_SESSION_SEED", "s_seed.csv"), ("COMBINED_SESSION_HISTORY", "s_state.csv"),
                ("BRACKET_DAILY_SEED", "d_seed.csv"), ("BRACKET_DAILY_HISTORY", "d_state.csv")):
    os.environ[k] = str(TMP / name)                   # isolate from the real files

from live_bot import update_history as U  # noqa: E402
from live_bot.daily_history import DailyHistory, completed_sessions  # noqa: E402
from live_bot.session_history import COLUMNS, SessionHistory, session_row  # noqa: E402

NY = U.NY
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(condition), detail))


def session(day: dt.date, seed: int, open_px: float, start="09:30", end="15:59") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range(f"{day} {start}", f"{day} {end}", freq="1min")
    close = open_px + np.cumsum(np.round(rng.normal(0, 6, len(idx))) * 0.25)
    return pd.DataFrame({"open": close, "high": close + 1.0, "low": close - 1.0, "close": close,
                         "volume": rng.integers(50, 150, len(idx)).astype(float)}, index=idx)


def market(days: list[dt.date], early: set[dt.date] = frozenset()) -> pd.DataFrame:
    """RTH sessions plus a little overnight trading (which the updater must ignore)."""
    parts, px = [], 20_000.0
    for i, d in enumerate(days):
        s = session(d, i, px, end="12:59" if d in early else "15:59")
        night = session(d, 1000 + i, float(s["close"].iloc[-1]), start="18:00", end="18:30")
        parts += [s, night]
        px = float(s["close"].iloc[-1]) + (40.0 if i % 3 == 0 else -35.0)
    return pd.concat(parts)


def central_polars(ny_naive: pd.DataFrame) -> pl.DataFrame:
    """The broker's shape: Polars, tz-aware Central timestamps."""
    df = ny_naive.copy()
    df.index = df.index.tz_localize("America/New_York").tz_convert("America/Chicago")
    df.index.name = "timestamp"
    return pl.from_pandas(df.reset_index())


def write_seeds(m: pd.DataFrame, upto: dt.date) -> None:
    rows, drows = [], []
    r = m[(m.index.time >= dt.time(9, 30)) & (m.index.time < dt.time(16, 0))]
    for d, g in r.groupby(r.index.date):
        if d > upto:
            break
        rows.append(session_row(g, pd.DataFrame(rows, columns=COLUMNS)))
        drows.append(dict(date=d, open=g["open"].iloc[0], high=g["high"].max(), low=g["low"].min(), close=g["close"].iloc[-1]))
    s = pd.DataFrame(rows, columns=COLUMNS)
    s["date"] = s["date"].map(lambda x: x.isoformat())
    s.to_csv(os.environ["COMBINED_SESSION_SEED"], index=False)
    pd.DataFrame(drows).assign(date=lambda x: x["date"].map(lambda v: v.isoformat())).to_csv(
        os.environ["BRACKET_DAILY_SEED"], index=False)
    for k in ("COMBINED_SESSION_HISTORY", "BRACKET_DAILY_HISTORY"):
        Path(os.environ[k]).unlink(missing_ok=True)


def fake_fetch(m: pd.DataFrame, contract: str = "CON.F.US.MNQ.Z26", calls: list | None = None):
    async def fetch(symbol, start, end):
        if calls is not None:
            calls.append((symbol, start, end))
        lo, hi = start.astimezone(NY).replace(tzinfo=None), end.astimezone(NY).replace(tzinfo=None)
        w = m[(m.index >= lo) & (m.index <= hi - dt.timedelta(minutes=1))]   # partial=False: no bar still open
        return central_polars(w), contract
    return fetch


def at(day: dt.date, hhmm: str) -> dt.datetime:
    return dt.datetime.combine(day, dt.time.fromisoformat(hhmm), NY)


class Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record):
        self.lines.append(f"{record.levelname} {record.getMessage()}")


def main() -> int:
    cap = Capture()
    U.log.addHandler(cap)
    U.log.setLevel(logging.INFO)
    U.log.propagate = False

    # --- the shared completeness rule
    d0 = dt.date(2026, 11, 24)
    parts = {
        dt.date(2026, 11, 24): session(dt.date(2026, 11, 24), 1, 20_000.0),                    # regular
        dt.date(2026, 11, 25): session(dt.date(2026, 11, 25), 2, 20_000.0, start="11:46"),     # window starts mid-session
        dt.date(2026, 11, 27): session(dt.date(2026, 11, 27), 3, 20_000.0, end="13:14"),       # early close
        dt.date(2026, 11, 30): session(dt.date(2026, 11, 30), 4, 20_000.0, end="11:09"),       # cut off mid-morning
        dt.date(2026, 12, 1): session(dt.date(2026, 12, 1), 5, 20_000.0),                      # today
    }
    rth = pd.concat(parts.values())
    got = [d for d, _ in completed_sessions(rth, dt.date(2026, 12, 1))]
    check("regular session complete", d0 in got, str(got))
    check("early-close session (13:00 ET) complete", dt.date(2026, 11, 27) in got, str(got))
    check("session the window starts mid-way through is not complete", dt.date(2026, 11, 25) not in got, str(got))
    check("session cut off mid-morning is not complete", dt.date(2026, 11, 30) not in got, str(got))
    check("today is never complete", dt.date(2026, 12, 1) not in got, str(got))

    # --- both caches take the early close; the next day reads it as its previous session
    days = [d.date() for d in pd.bdate_range("2026-10-01", "2026-12-02") if d.date() != dt.date(2026, 11, 26)]
    m = market(days, early={dt.date(2026, 11, 27)})
    write_seeds(m, dt.date(2026, 11, 20))
    rth_all = U.to_rth_ny(m)
    s = SessionHistory()
    s.update_from_bars(rth_all, dt.date(2026, 12, 1))
    check("session cache appends the early close", dt.date(2026, 11, 27) in set(s.df["date"]))
    check("next day's previous session is the early close", s.before(dt.date(2026, 11, 30))["date"].iloc[-1] == dt.date(2026, 11, 27))
    dh = DailyHistory()
    dh.merge_live(rth_all, dt.date(2026, 12, 1))
    check("daily cache appends the early close", dt.date(2026, 11, 27) in set(dh.df["date"]))
    gap_seed = m[m.index.date <= dt.date(2026, 10, 30)]
    write_seeds(gap_seed, dt.date(2026, 10, 30))
    s2 = SessionHistory()
    cut = rth_all[rth_all.index >= pd.Timestamp("2026-11-10 11:46")]
    s2.update_from_bars(cut, dt.date(2026, 11, 20))
    check("after a gap, the window's cut-off first session is not appended",
          dt.date(2026, 11, 10) not in set(s2.df["date"]) and dt.date(2026, 11, 11) in set(s2.df["date"]))

    # --- the updater end to end (fake broker)
    write_seeds(m, dt.date(2026, 11, 20))
    meta = TMP / "meta.json"
    calls: list = []
    code = U.run(fetch=fake_fetch(m, calls=calls), now=at(dt.date(2026, 12, 1), "15:30"), meta_path=meta)
    s3, d3 = SessionHistory(), DailyHistory()
    check("run before the close: exit 0", code == 0, str(code))
    check("run before the close: every closed session added, today not",
          s3.df["date"].iloc[-1] == dt.date(2026, 11, 30) and d3.df["date"].iloc[-1] == dt.date(2026, 11, 30),
          f"{s3.df['date'].iloc[-1]} {d3.df['date'].iloc[-1]}")
    check("fetch starts at midnight of the last cached session",
          calls and calls[0][1] == at(dt.date(2026, 11, 20), "00:00"), str(calls[:1]))
    full = SessionHistory(os.environ["COMBINED_SESSION_SEED"], TMP / "unused.csv")
    one_pass = []
    for d, g in completed_sessions(rth_all, dt.date(2026, 12, 1)):
        one_pass.append(session_row(g, pd.DataFrame(one_pass, columns=COLUMNS)))
    ref = pd.DataFrame(one_pass, columns=COLUMNS)
    ref = ref[ref["date"] <= dt.date(2026, 11, 30)].reset_index(drop=True)
    check("updater rows equal the rows built in one pass",
          len(s3.df) == len(ref) and np.allclose(s3.df[["range", "poc", "val", "vah"]].to_numpy(float),
                                                 ref[["range", "poc", "val", "vah"]].to_numpy(float))
          and s3.df["poc_outcome"].fillna(-1).tolist() == ref["poc_outcome"].fillna(-1).tolist(),
          f"{len(s3.df)} vs {len(ref)}")
    check("overnight bars ignored (daily high/low are RTH only)",
          abs(d3.df.set_index("date").loc[dt.date(2026, 11, 30), "high"]
              - m[(m.index.date == dt.date(2026, 11, 30)) & (m.index.time < dt.time(16, 0))]["high"].max()) < 1e-9)
    mj = json.loads(meta.read_text())
    check("meta records contract and last sessions", mj["contract"] == "CON.F.US.MNQ.Z26" and mj["session_last"] == "2026-11-30", str(mj))

    code = U.run(fetch=fake_fetch(m), now=at(dt.date(2026, 12, 1), "16:30"), meta_path=meta)
    check("run after 16:05 ET adds today's session", SessionHistory().df["date"].iloc[-1] == dt.date(2026, 12, 1) and code == 0)
    n_before = len(SessionHistory().df)
    U.run(fetch=fake_fetch(m), now=at(dt.date(2026, 12, 1), "22:30"), meta_path=meta)
    check("second run the same day adds nothing", len(SessionHistory().df) == n_before)

    # dry run: reports, writes nothing
    write_seeds(m, dt.date(2026, 11, 20))
    cap.lines.clear()
    code = U.run(fetch=fake_fetch(m), now=at(dt.date(2026, 12, 1), "15:30"), dry_run=True, meta_path=TMP / "meta_dry.json")
    check("dry run writes no state and no meta",
          not Path(os.environ["COMBINED_SESSION_HISTORY"]).exists() and not Path(os.environ["BRACKET_DAILY_HISTORY"]).exists()
          and not (TMP / "meta_dry.json").exists())
    check("dry run reports what it would add", code == 0 and any("DRY RUN: session cache: +5" in l for l in cap.lines),
          " | ".join(cap.lines))

    # hole: the cache ends before the broker's history starts
    write_seeds(m, dt.date(2026, 10, 9))
    late = m[m.index >= pd.Timestamp("2026-11-02")]
    cap.lines.clear()
    code = U.run(fetch=fake_fetch(late), now=at(dt.date(2026, 12, 1), "15:30"), meta_path=TMP / "meta_hole.json")
    check("hole the broker cannot fill: exit 2", code == 2, str(code))
    check("hole named in the log", any("between 2026-10-09 and 2026-11-02" in l for l in cap.lines), " | ".join(cap.lines))

    # holidays are not holes: Thanksgiving is missing from this market, Good-Friday-style single days are fine
    write_seeds(m, dt.date(2026, 11, 20))
    check("single missing weekday is a holiday, not a hole", U.holes(dt.date(2026, 11, 25), [dt.date(2026, 11, 27)]) == [])
    check("two missing weekdays is a hole", U.holes(dt.date(2026, 11, 23), [dt.date(2026, 11, 27)]) != [])

    # contract roll is reported
    cap.lines.clear()
    U.run(fetch=fake_fetch(m, contract="CON.F.US.MNQ.H27"), now=at(dt.date(2026, 12, 1), "15:30"), meta_path=meta)
    check("contract change warned", any("contract changed CON.F.US.MNQ.Z26 -> CON.F.US.MNQ.H27" in l for l in cap.lines),
          " | ".join(cap.lines))

    # broker failures
    async def boom(symbol, start, end):
        raise ConnectionError("gateway down")

    async def empty(symbol, start, end):
        return pl.DataFrame(), "X"
    check("fetch error: exit 1", U.run(fetch=boom, now=at(dt.date(2026, 12, 1), "15:30"), meta_path=TMP / "m1.json") == 1)
    check("no bars: exit 1", U.run(fetch=empty, now=at(dt.date(2026, 12, 1), "15:30"), meta_path=TMP / "m2.json") == 1)

    check("cutoff before 16:05 ET is today", U.session_cutoff(at(dt.date(2026, 12, 1), "16:04")) == dt.date(2026, 12, 1))
    check("cutoff from 16:05 ET is tomorrow", U.session_cutoff(at(dt.date(2026, 12, 1), "16:05")) == dt.date(2026, 12, 2))

    failed = [r for r in RESULTS if not r[1]]
    for name, ok, detail in RESULTS:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"   [{detail[:300]}]" if not ok else ""))
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
