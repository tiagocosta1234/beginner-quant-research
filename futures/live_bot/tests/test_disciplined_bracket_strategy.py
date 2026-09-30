"""Plain-Python tests for disciplined_bracket_strategy.py's timestamp handling
(no pytest dependency).

Run with: python live_bot/tests/test_disciplined_bracket_strategy.py

Added 2026-09-30 after confirming against the real BrokerAPI Practice feed that
live bars arrive tz-aware in Central time (`-05:00`), while the strategy's
RTH_START/RTH_END/entry-grace logic is New York wall-clock. These tests build
the same synthetic market twice -- stamped New York-naive and stamped Central
tz-aware -- and require identical decisions.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from live_bot.disciplined_bracket_strategy import DisciplinedBracketStrategy  # noqa: E402
from live_bot.strategy_interface import SignalAction  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, condition, detail))


def prior_session(day: dt.date, seed: int) -> pd.DataFrame:
    """One completed RTH session (09:30-15:59 NY), tight around 20,000."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range(f"{day} 09:30", f"{day} 15:59", freq="1min")
    close = 20_000.0 + np.round(rng.normal(0, 4, len(idx))) * 0.25
    return pd.DataFrame(
        {"open": close, "high": close + 0.5, "low": close - 0.5, "close": close,
         "volume": rng.integers(50, 150, len(idx)).astype(float)},
        index=idx,
    )


def today_bars(day: dt.date, first: str, last: str, open_px: float = 19_950.0) -> pd.DataFrame:
    idx = pd.date_range(f"{day} {first}", f"{day} {last}", freq="1min")
    px = np.full(len(idx), open_px)
    return pd.DataFrame(
        {"open": px, "high": px + 0.5, "low": px - 0.5, "close": px, "volume": np.full(len(idx), 100.0)},
        index=idx,
    )


def to_polars(ny_naive: pd.DataFrame, central: bool) -> pl.DataFrame:
    df = ny_naive.sort_index().copy()
    if central:
        df.index = df.index.tz_localize("America/New_York").tz_convert("America/Chicago")
    df.index.name = "timestamp"
    return pl.from_pandas(df.reset_index())


def build(today_first: str, today_last: str, extra_premarket: bool = False) -> pd.DataFrame:
    d1, d2, today = dt.date(2026, 9, 28), dt.date(2026, 9, 29), dt.date(2026, 9, 30)
    parts = [prior_session(d1, 1), prior_session(d2, 2), today_bars(today, today_first, today_last)]
    if extra_premarket:
        # A 09:29 NY (08:29 CT) pre-open bar at a very different price: must NOT
        # be picked up as the session open.
        parts.append(today_bars(today, "09:29", "09:29", open_px=19_000.0))
    return pd.concat(parts)


def main() -> int:
    # 1. Baseline: NY-naive stamps, inside the entry window -> VA-rejection long.
    ny = DisciplinedBracketStrategy().on_bar(to_polars(build("09:30", "09:32"), central=False))
    check("NY-naive: enters long inside the grace window", ny.action == SignalAction.ENTER_LONG, f"{ny.action} {ny.reason}")

    # 2. The bug: same market, Central tz-aware stamps -> must decide identically.
    ct = DisciplinedBracketStrategy().on_bar(to_polars(build("09:30", "09:32"), central=True))
    check("Central tz-aware: enters long inside the grace window", ct.action == SignalAction.ENTER_LONG, f"{ct.action} {ct.reason}")
    check("Central vs NY: identical stop", ct.stop_loss_price == ny.stop_loss_price, f"{ct.stop_loss_price} vs {ny.stop_loss_price}")
    check("Central vs NY: identical take-profit", ct.take_profit_price == ny.take_profit_price, f"{ct.take_profit_price} vs {ny.take_profit_price}")

    # 3. Pre-open bar must not become the session open (open is the 09:30 NY bar).
    pre = DisciplinedBracketStrategy().on_bar(to_polars(build("09:30", "09:32", extra_premarket=True), central=True))
    check("Pre-open 09:29 NY bar is not the session open", pre.action == SignalAction.ENTER_LONG and pre.stop_loss_price == ny.stop_loss_price,
          f"{pre.action} sl={pre.stop_loss_price} expected {ny.stop_loss_price}")

    # 4. Grace window is measured in NY time: 20 minutes past the 09:30 NY open -> no trade.
    late = DisciplinedBracketStrategy().on_bar(to_polars(build("09:30", "09:50"), central=True))
    check("Central: past entry grace window -> HOLD", late.action == SignalAction.HOLD and "grace" in late.reason, f"{late.action} {late.reason}")

    # 5. Before the NY open there are no RTH bars today -> HOLD.
    early = DisciplinedBracketStrategy().on_bar(to_polars(build("09:00", "09:20"), central=True))
    check("Central: before 09:30 NY -> no RTH bars yet today", early.action == SignalAction.HOLD and "no RTH bars yet today" in early.reason,
          f"{early.action} {early.reason}")

    # 6. VA switch: this market only triggers the VA-rejection fallback (2 prior sessions,
    # too few for the POC leg's 10-session range), so VA off -> no trade, default -> trade.
    off = DisciplinedBracketStrategy(disable_va=True).on_bar(to_polars(build("09:30", "09:32"), central=True))
    check("VA off: VA-only setup -> HOLD", off.action == SignalAction.HOLD and "neither leg fired" in off.reason, f"{off.action} {off.reason}")
    on = DisciplinedBracketStrategy(disable_va=False).on_bar(to_polars(build("09:30", "09:32"), central=True))
    check("VA on (explicit): same setup still trades", on.action == SignalAction.ENTER_LONG and "VA-rejection" in on.reason, f"{on.action}")
    check("default is VA on (original behavior)", DisciplinedBracketStrategy().disable_va is False)

    # 7. None / empty input still safe.
    check("None bars -> HOLD", DisciplinedBracketStrategy().on_bar(None).action == SignalAction.HOLD)

    failed = [r for r in RESULTS if not r[1]]
    for name, ok, detail in RESULTS:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if not ok else ""))
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
