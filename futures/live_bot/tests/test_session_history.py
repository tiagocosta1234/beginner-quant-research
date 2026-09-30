"""Plain-Python tests for session_history.py and CombinedStrategy's use of it.
No pytest dependency. Uses only temporary files -- never the real seed or state.

Run with: python live_bot/tests/test_session_history.py

The main check is equivalence: on the same synthetic market, a Combined bot reading
a history cache (built with session_row from the same sessions) must decide exactly
what the original bars-only bot decides when the bars window holds enough history.
"""

from __future__ import annotations

import datetime as dt
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from live_bot.session_history import COLUMNS, SessionHistory, session_row  # noqa: E402

TMP = Path(tempfile.mkdtemp())
os.environ["COMBINED_SESSION_SEED"] = str(TMP / "no_seed.csv")        # isolate from the real files
os.environ["COMBINED_SESSION_HISTORY"] = str(TMP / "no_state.csv")

from live_bot.combined_strategy import CombinedStrategy  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, condition, detail))


def session(day: dt.date, seed: int, open_px: float) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range(f"{day} 09:30", f"{day} 15:59", freq="1min")
    close = open_px + np.cumsum(np.round(rng.normal(0, 6, len(idx))) * 0.25)
    return pd.DataFrame({"open": close, "high": close + 1.0, "low": close - 1.0, "close": close,
                         "volume": rng.integers(50, 150, len(idx)).astype(float)}, index=idx)


def market(n_sessions: int, today: dt.date, today_last: str = "09:32") -> pd.DataFrame:
    days = [d.date() for d in pd.bdate_range(end=today - dt.timedelta(days=1), periods=n_sessions)]
    parts, px = [], 20_000.0
    for i, d in enumerate(days):
        s = session(d, i, px)
        parts.append(s)
        px = float(s["close"].iloc[-1]) + (40.0 if i % 3 == 0 else -35.0)
    idx = pd.date_range(f"{today} 09:30", f"{today} {today_last}", freq="1min")
    parts.append(pd.DataFrame({"open": px, "high": px + 1, "low": px - 1, "close": px, "volume": 100.0}, index=idx))
    return pd.concat(parts)


def to_polars(df: pd.DataFrame) -> pl.DataFrame:
    d = df.copy()
    d.index.name = "timestamp"
    return pl.from_pandas(d.reset_index())


def build_seed(m: pd.DataFrame, upto: dt.date, path: Path) -> None:
    rows = []
    for d, g in m.groupby(m.index.date):
        if d >= upto:
            break
        rows.append(session_row(g, pd.DataFrame(rows, columns=COLUMNS)))
    out = pd.DataFrame(rows, columns=COLUMNS)
    out["date"] = out["date"].map(lambda x: x.isoformat())
    out.to_csv(path, index=False)


def main() -> int:
    today = dt.date(2026, 10, 1)
    m = market(60, today)
    seed = TMP / "seed.csv"
    build_seed(m, today, seed)
    sh = SessionHistory(seed, TMP / "state_a.csv")
    check("seed loads 60 sessions", len(sh.df) == 60, str(len(sh.df)))
    check("seed has POC trades with outcomes", sh.df["poc_outcome"].notna().sum() >= 20, str(sh.df["poc_outcome"].notna().sum()))

    bars_bot = CombinedStrategy(history_source="bars")
    cache_bot = CombinedStrategy(history_source="bars")
    cache_bot._history = SessionHistory(seed, TMP / "state_b.csv")
    a, b = bars_bot.on_bar(to_polars(m)), cache_bot.on_bar(to_polars(m))
    same = (a.action == b.action and a.stop_loss_price == b.stop_loss_price and a.take_profit_price == b.take_profit_price
            and a.size == b.size)
    check("cache bot decides exactly like the bars bot (60 sessions of bars)", same, f"{a.action} {a.reason[:90]} | {b.action} {b.reason[:90]}")
    tw = lambda s: s.reason.split("trail_winrate=")[1][:4] if "trail_winrate=" in (s.reason or "") else None
    check("same trail_winrate", tw(a) == tw(b), f"{tw(a)} vs {tw(b)}")

    # with only 15 sessions of bars the bars bot must hold, the cache bot (60-session seed) still decides
    short = m[m.index.date >= sorted(set(m.index.date))[-16]]
    a2 = CombinedStrategy(history_source="bars").on_bar(to_polars(short))
    c2 = CombinedStrategy(history_source="bars")
    c2._history = SessionHistory(seed, TMP / "state_c.csv")
    b2 = c2.on_bar(to_polars(short))
    check("short window: bars bot holds for lack of history", "reconstructed" in (a2.reason or "") or "prior sessions" in (a2.reason or ""), a2.reason)
    check("short window: cache bot still reaches the same decision as the full-bars bot",
          b2.action == a.action and b2.stop_loss_price == a.stop_loss_price, f"{b2.action} {b2.reason[:120]}")

    # live sessions newer than the history are appended (completed only) and persisted
    seed_old = TMP / "seed_old.csv"
    build_seed(m, sorted(set(m.index.date))[-5], seed_old)          # seed stops 4 sessions early
    state = TMP / "state_d.csv"
    h = SessionHistory(seed_old, state)
    rth = m[m.index.date < today]
    n = h.update_from_bars(rth, today)
    check("4 newer completed sessions appended", n == 4, str(n))
    h2 = SessionHistory(seed_old, state)
    check("appended sessions persisted", len(h2.df) == 60)
    full = SessionHistory(seed, TMP / "unused.csv").df
    check("appended rows equal the rows built in one pass",
          np.allclose(h2.df[["range", "poc", "val", "vah"]].to_numpy(float), full[["range", "poc", "val", "vah"]].to_numpy(float))
          and h2.df["poc_outcome"].fillna(-1).tolist() == full["poc_outcome"].fillna(-1).tolist())
    partial = m[(m.index.date == sorted(set(m.index.date))[-2])].iloc[:100]
    h3 = SessionHistory(seed_old, TMP / "state_e.csv")
    check("an incomplete session is not appended", h3.update_from_bars(partial, today) == 0)

    failed = [r for r in RESULTS if not r[1]]
    for name, ok, detail in RESULTS:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"   [{detail[:220]}]" if not ok else ""))
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
