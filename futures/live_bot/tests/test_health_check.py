"""Plain-Python tests for health_check.py's data-freshness check (no pytest dependency).

Run with: python live_bot/tests/test_health_check.py

Added 2026-09-30: the freshness check compared a Polars Series and raised
"truth value of a Series is ambiguous" on every real poll, so it never ran.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from live_bot.health_check import CENTRAL_TZ, HealthCheck, HealthStatus  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, condition, detail))


class FakeBroker:
    is_connected = True

    def __init__(self, bars):
        self._bars = bars

    async def get_bars(self, bars: int = 200, timeframe: str = "5min"):
        return self._bars

    def get_account_balance(self):
        return 150_000.0


def frame(ts: datetime) -> pl.DataFrame:
    return pl.DataFrame({"timestamp": [ts], "open": [1.0], "high": [1.0], "low": [1.0], "close": [1.0], "volume": [1.0]})


def run(bars) -> "HealthReport":  # noqa: F821
    return asyncio.run(HealthCheck(FakeBroker(bars), None).check())


def main() -> int:
    now = datetime.now(tz=CENTRAL_TZ)

    fresh = run(frame(now - timedelta(seconds=30)))
    check("fresh tz-aware Polars bar -> healthy", fresh.overall_status == HealthStatus.HEALTHY and fresh.data_fresh, str(fresh.issues))

    stale = run(frame(now - timedelta(minutes=10)))
    check("stale Polars bar -> flagged as stale", not stale.data_fresh and any("Data stale" in i for i in stale.issues), str(stale.issues))
    check("stale data alone is degraded, not critical", stale.overall_status == HealthStatus.DEGRADED, stale.overall_status.value)

    naive = run(frame(now.replace(tzinfo=None) - timedelta(seconds=30)))
    check("naive timestamp treated as Central -> healthy", naive.overall_status == HealthStatus.HEALTHY, str(naive.issues))

    none = run(None)
    check("None bars -> 'No bars returned'", any("No bars returned" in i for i in none.issues), str(none.issues))

    empty = run(frame(now).clear())
    check("empty frame -> 'No bars returned'", any("No bars returned" in i for i in empty.issues), str(empty.issues))

    check("no 'Series is ambiguous' error in any case",
          not any("ambiguous" in i for r in (fresh, stale, naive, none, empty) for i in r.issues))

    failed = [r for r in RESULTS if not r[1]]
    for name, ok, detail in RESULTS:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if not ok else ""))
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
