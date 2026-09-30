"""
Health Check: periodic broker connectivity and data freshness validation.

Monitors:
- Broker connection status (async heartbeat)
- Data feed freshness (last bar timestamp vs. now)
- Account balance availability
- Position staleness

Reports health status each cycle; alerts on degradation.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, TYPE_CHECKING

from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from live_bot.broker_client import BrokerClient
    from live_bot.risk_governor import AccountConfig

CENTRAL_TZ = ZoneInfo("America/Chicago")


class HealthStatus(Enum):
    """Health state of the bot."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"


@dataclass
class HealthReport:
    """Snapshot of bot health at a point in time."""
    timestamp: datetime
    overall_status: HealthStatus
    broker_connected: bool
    data_fresh: bool  # last bar within FRESHNESS_THRESHOLD
    account_balance_available: bool
    last_check_duration_ms: float
    issues: list[str]  # human-readable warnings/errors


class HealthCheck:
    """
    Periodic health monitoring: broker, data feed, account state.

    NOT thread-safe; must be driven by a single async event loop.
    Call check() from the main polling loop every POLL_INTERVAL or less.

    Usage:
        health = HealthCheck(broker, account_config, logger)
        report = await health.check()
        if report.overall_status == HealthStatus.CRITICAL:
            # take action
    """

    # Data is stale if the last bar is older than this
    FRESHNESS_THRESHOLD = timedelta(seconds=120)

    # Account balance check can fail for a few cycles before raising alert
    MAX_BALANCE_CHECK_FAILURES = 3

    def __init__(
        self,
        broker: "BrokerClient",
        account_config: "AccountConfig",
        logger: Optional[logging.Logger] = None,
    ):
        self.broker = broker
        self.account_config = account_config
        self.logger = logger or logging.getLogger("HealthCheck")

        self.consecutive_balance_failures = 0
        self.last_healthy_report: Optional[HealthReport] = None

    async def check(self) -> HealthReport:
        """
        Run a full health check cycle.

        Returns:
            HealthReport with current status, issue list, and diagnostics.
            Does NOT raise exceptions; all errors are captured in report.issues.
        """
        check_start = datetime.now(tz=CENTRAL_TZ)
        issues: list[str] = []

        # --- Broker connectivity ---
        broker_ok = self.broker.is_connected
        if not broker_ok:
            issues.append("Broker not connected")

        # --- Data freshness ---
        data_fresh = True
        if broker_ok:
            try:
                bars = await asyncio.wait_for(
                    self.broker.get_bars(bars=1, timeframe="1min"),
                    timeout=5.0,
                )
                if bars is None or len(bars) == 0:
                    issues.append("No bars returned from broker")
                    data_fresh = False
                else:
                    # Get the last bar's timestamp. BUGFIX (2026-09-30): get_bars()
                    # returns a Polars DataFrame, where `bars[-1]["timestamp"]` is a
                    # Series, so the staleness comparison below raised "truth value of
                    # a Series is ambiguous" every cycle and the freshness check never
                    # ran. Read the column's last element instead.
                    ts_col = bars["timestamp"]
                    last_bar_time = ts_col.iloc[-1] if hasattr(ts_col, "iloc") else ts_col[-1]
                    if hasattr(last_bar_time, "to_pydatetime"):  # pandas Timestamp
                        last_bar_time = last_bar_time.to_pydatetime()
                    if isinstance(last_bar_time, datetime) and last_bar_time.tzinfo is None:
                        last_bar_time = last_bar_time.replace(tzinfo=CENTRAL_TZ)
                    now = datetime.now(tz=CENTRAL_TZ)

                    if isinstance(last_bar_time, str):
                        # Parse ISO format
                        try:
                            last_bar_time = datetime.fromisoformat(last_bar_time)
                            if last_bar_time.tzinfo is None:
                                last_bar_time = last_bar_time.replace(tzinfo=CENTRAL_TZ)
                        except ValueError:
                            issues.append(f"Could not parse bar timestamp: {last_bar_time}")
                            data_fresh = False

                    if data_fresh and (now - last_bar_time) > self.FRESHNESS_THRESHOLD:
                        issues.append(
                            f"Data stale: last bar {(now - last_bar_time).total_seconds():.0f}s old"
                        )
                        data_fresh = False
            except asyncio.TimeoutError:
                issues.append("get_bars() timed out (5s)")
                data_fresh = False
            except Exception as e:
                issues.append(f"get_bars() error: {type(e).__name__}: {str(e)}")
                data_fresh = False

        # --- Account balance availability ---
        balance_ok = False
        if broker_ok:
            try:
                balance = self.broker.get_account_balance()
                if balance is not None:
                    balance_ok = True
                    self.consecutive_balance_failures = 0
                else:
                    self.consecutive_balance_failures += 1
                    if self.consecutive_balance_failures > self.MAX_BALANCE_CHECK_FAILURES:
                        issues.append(
                            f"Account balance unavailable ({self.consecutive_balance_failures} failures)"
                        )
            except Exception as e:
                self.consecutive_balance_failures += 1
                if self.consecutive_balance_failures > self.MAX_BALANCE_CHECK_FAILURES:
                    issues.append(f"get_account_balance() error: {str(e)}")

        # --- Determine overall status ---
        if len(issues) == 0:
            overall_status = HealthStatus.HEALTHY
        elif len(issues) <= 2 and not any("not connected" in i for i in issues):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.CRITICAL

        check_duration_ms = (datetime.now(tz=CENTRAL_TZ) - check_start).total_seconds() * 1000

        report = HealthReport(
            timestamp=check_start,
            overall_status=overall_status,
            broker_connected=broker_ok,
            data_fresh=data_fresh,
            account_balance_available=balance_ok,
            last_check_duration_ms=check_duration_ms,
            issues=issues,
        )

        # Log changes in status
        if self.last_healthy_report is None or report.overall_status != self.last_healthy_report.overall_status:
            level = (
                logging.WARNING if report.overall_status == HealthStatus.DEGRADED
                else logging.ERROR if report.overall_status == HealthStatus.CRITICAL
                else logging.INFO
            )
            self.logger.log(
                level,
                f"Health status: {report.overall_status.value}. "
                f"Issues: {', '.join(report.issues) if report.issues else 'none'}. "
                f"Check took {report.last_check_duration_ms:.1f}ms",
            )

        self.last_healthy_report = report
        return report

    def is_healthy(self) -> bool:
        """Quick check: is the last report healthy?"""
        if self.last_healthy_report is None:
            return False  # no report yet, assume unhealthy until proven otherwise
        return self.last_healthy_report.overall_status == HealthStatus.HEALTHY
