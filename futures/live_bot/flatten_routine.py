"""
3:10 PM CT Flatten Routine: scheduled daily position closure and trading lockout.

Uses APScheduler to execute at 3:10 PM CT every trading day. Performs:
1. Pre-flatten verification (check for open positions)
2. Market-order flatten (close all with retry)
3. Post-flatten verification (verify all closed)
4. Trading lockout (prevent new entries)
5. Compliance logging

All operations are async-compatible (integrates with the main event loop).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from live_bot.broker_client import BrokerClient
    from live_bot.pnl_tracker import PnlTracker
    from live_bot.risk_governor import AccountConfig

CENTRAL_TZ = ZoneInfo("America/Chicago")


class FlattenStatus(Enum):
    """State of a flatten routine execution."""

    PENDING = "pending"
    PRE_CHECK_PASSED = "pre_check_passed"
    PRE_CHECK_FAILED = "pre_check_failed"
    FLATTEN_IN_PROGRESS = "flatten_in_progress"
    FLATTEN_SUCCESS = "flatten_success"
    FLATTEN_FAILED = "flatten_failed"
    TRADING_LOCKED = "trading_locked"


@dataclass
class FlattenEvent:
    """Immutable record of a daily flatten routine execution."""

    timestamp: datetime
    status: FlattenStatus
    positions_before_count: Optional[int]
    positions_after_count: Optional[int]
    pnl_at_flatten: Optional[float]
    error_message: Optional[str] = None
    retry_count: int = 0
    manual_override_applied: bool = False


class AlertHandler:
    """Sends a real email on a risk breach/compliance event, in addition to
    the normal logging every caller already gets. Implemented 2026-09-24 --
    this was a pure no-op stub before (`# TODO: Implement with real alert
    backends`), meaning tonight's real events (the $250K breach, the
    reconcile_balance() test) would have produced zero external notification
    even if every other check had worked perfectly.

    Email only, gated on env vars -- no Slack/PagerDuty (would need their own
    credentials/setup this repo doesn't have yet). Config is optional and
    fails soft: if SMTP_HOST/SMTP_USER/SMTP_PASS/ALERT_EMAIL_TO aren't all
    set, `alert()` logs a CRITICAL line noting email is not configured and
    returns -- it never raises, since a broken alert path must not be able to
    interfere with the actual risk-handling flow that calls it (flatten,
    lockout, etc. must proceed regardless of whether the notification send
    succeeds).

    UNVERIFIED against a real send as of this implementation -- no SMTP
    credentials have been configured/tested yet. Set the four env vars below
    and trigger a real `alert()` call (e.g. via a deliberate test breach in
    Practice mode) before trusting this for an unattended live run.
    """

    def __init__(self) -> None:
        self._smtp_host = os.getenv("SMTP_HOST")
        self._smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self._smtp_user = os.getenv("SMTP_USER")
        self._smtp_pass = os.getenv("SMTP_PASS")
        self._to_addr = os.getenv("ALERT_EMAIL_TO")

    def _is_configured(self) -> bool:
        return all([self._smtp_host, self._smtp_user, self._smtp_pass, self._to_addr])

    async def alert(self, level: str, title: str, message: str) -> None:
        """Send alert to configured channels. Never raises -- logs and
        returns on any failure, since the caller's own risk-handling must
        not depend on a notification succeeding."""
        logger = logging.getLogger(__name__)
        if not self._is_configured():
            logger.critical(
                "ALERT [%s] %s: %s  (no email sent -- SMTP_HOST/SMTP_USER/"
                "SMTP_PASS/ALERT_EMAIL_TO not all set in the environment)",
                level, title, message,
            )
            return
        try:
            await asyncio.to_thread(self._send_email_sync, level, title, message)
            logger.info("Alert email sent to %s: [%s] %s", self._to_addr, level, title)
        except Exception as e:
            logger.critical(
                "ALERT [%s] %s: %s  (email send FAILED: %s)",
                level, title, message, e,
            )

    def _send_email_sync(self, level: str, title: str, message: str) -> None:
        """Runs in a worker thread (smtplib is blocking) -- see alert()."""
        import smtplib
        from email.mime.text import MIMEText

        msg = MIMEText(message)
        msg["Subject"] = f"[live_bot {level}] {title}"
        msg["From"] = self._smtp_user
        msg["To"] = self._to_addr
        with smtplib.SMTP(self._smtp_host, self._smtp_port, timeout=15) as server:
            server.starttls()
            server.login(self._smtp_user, self._smtp_pass)
            server.send_message(msg)


class FlattenRoutine:
    """
    Daily 3:10 PM CT flatten routine: close all open positions.

    NOT thread-safe; must be driven by a single async event loop.
    All broker operations are async.

    Usage:
        routine = FlattenRoutine(broker, account_config, pnl_tracker, alert_handler, logger)
        await routine.schedule(scheduler)
        # scheduler fires execute() automatically every day at 3:10 PM CT
    """

    def __init__(
        self,
        broker: "BrokerClient",
        account_config: "AccountConfig",
        pnl_tracker: "PnlTracker",
        alert_handler: Optional[AlertHandler] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.broker = broker
        self.account_config = account_config
        self.pnl_tracker = pnl_tracker
        self.alert_handler = alert_handler or AlertHandler()
        self.logger = logger or logging.getLogger("FlattenRoutine")

        # Today's flatten state
        self.flatten_event: Optional[FlattenEvent] = None
        self.trading_locked_today: bool = False

        # APScheduler instance (set by schedule())
        self.scheduler: Optional[AsyncIOScheduler] = None

    async def schedule(self, scheduler: AsyncIOScheduler) -> None:
        """
        Register the daily flatten job at 3:10 PM CT.

        Args:
            scheduler: AsyncIOScheduler instance (e.g., from main.py)
        """
        self.scheduler = scheduler

        # 3:10 PM = 15:10 in 24-hour time
        scheduler.add_job(
            self.execute,
            "cron",
            hour=15,
            minute=10,
            timezone=CENTRAL_TZ,
            id="daily_flatten_3pm",
            name="Daily 3:10 PM CT Flatten",
            replace_existing=True,
        )

        self.logger.info("Flatten routine scheduled for 3:10 PM CT")

    async def execute(self) -> None:
        """
        Main entry point: called every day at 3:10 PM CT by the scheduler.

        Flow:
        1. Pre-flatten check: verify open positions exist
        2. Flatten execution: market-order close all
        3. Post-flatten: verify all closed, lock trading
        4. Compliance logging

        Does NOT raise exceptions; all errors are logged + alerted.
        """
        now = datetime.now(tz=CENTRAL_TZ)
        self.logger.info(f"[{now.isoformat()}] Starting 3:10 PM flatten routine")

        try:
            # --- PRE-FLATTEN CHECK ---
            await self._pre_flatten_check()

            if self.flatten_event.status == FlattenStatus.PRE_CHECK_FAILED:
                self.logger.error(
                    f"Pre-flatten check failed: {self.flatten_event.error_message}"
                )
                await self.alert_handler.alert(
                    level="ERROR",
                    title="Flatten Pre-Check Failed",
                    message=self.flatten_event.error_message or "Unknown error",
                )
                return

            # If no positions open, still mark as success
            if self.flatten_event.positions_before_count == 0:
                self.flatten_event.status = FlattenStatus.FLATTEN_SUCCESS
                self.logger.info("No open positions at 3:10 PM; nothing to flatten")
                # Still lock trading and log (end-of-day protocols)
            else:
                # --- FLATTEN EXECUTION ---
                await self._flatten_with_retry(max_retries=3, backoff_seconds=5)

                if self.flatten_event.status == FlattenStatus.FLATTEN_FAILED:
                    self.logger.error(
                        f"Flatten execution failed: {self.flatten_event.error_message}"
                    )
                    await self.alert_handler.alert(
                        level="CRITICAL",
                        title="FLATTEN FAILED - Manual Override Required",
                        message=(
                            f"{self.flatten_event.error_message}\n"
                            f"Retries exhausted: {self.flatten_event.retry_count}. "
                            f"Manual intervention required to close positions."
                        ),
                    )
                    # Don't lock trading; position is potentially still open
                    return

                # --- POST-FLATTEN VERIFICATION ---
                await self._post_flatten_verification()

            # --- LOCK TRADING FOR THE DAY ---
            self.trading_locked_today = True
            self.logger.info("Trading locked for the day after flatten")

            # --- COMPLIANCE LOGGING ---
            await self._log_compliance_event()

            # --- NOTIFICATION ---
            await self.alert_handler.alert(
                level="INFO",
                title="Daily Flatten Complete",
                message=(
                    f"All positions closed. "
                    f"P&L: ${self.flatten_event.pnl_at_flatten:.2f}. "
                    f"Trading locked."
                ),
            )

        except Exception as e:
            self.logger.exception(f"Unhandled exception in flatten routine: {e}")
            await self.alert_handler.alert(
                level="CRITICAL",
                title="Flatten Routine Crashed",
                message=str(e),
            )

    async def _pre_flatten_check(self) -> None:
        """
        Verify broker connectivity and check for open positions.

        Records a FlattenEvent with PRE_CHECK_PASSED or PRE_CHECK_FAILED status.
        """
        try:
            # Get current market snapshot
            unrealized_pnl = await self.broker.get_unrealized_pnl()
            has_open = await self.broker.has_open_position()

            positions_before = 1 if has_open else 0

            self.flatten_event = FlattenEvent(
                timestamp=datetime.now(tz=CENTRAL_TZ),
                status=FlattenStatus.PRE_CHECK_PASSED,
                positions_before_count=positions_before,
                positions_after_count=None,
                pnl_at_flatten=unrealized_pnl,
                error_message=None,
                retry_count=0,
                manual_override_applied=False,
            )

            self.logger.info(
                f"Pre-flatten check passed: "
                f"positions_before={positions_before}, "
                f"unrealized_pnl=${unrealized_pnl:.2f}"
            )

        except Exception as e:
            self.flatten_event = FlattenEvent(
                timestamp=datetime.now(tz=CENTRAL_TZ),
                status=FlattenStatus.PRE_CHECK_FAILED,
                positions_before_count=None,
                positions_after_count=None,
                pnl_at_flatten=None,
                error_message=f"Pre-check failed: {str(e)}",
                retry_count=0,
                manual_override_applied=False,
            )

    async def _flatten_with_retry(
        self, max_retries: int = 3, backoff_seconds: int = 5
    ) -> None:
        """
        Market-order close all positions with exponential backoff retry.

        If all retries fail, status → FLATTEN_FAILED.

        Args:
            max_retries: number of attempts
            backoff_seconds: base backoff (multiplied by attempt number)
        """
        assert self.flatten_event is not None

        self.flatten_event.status = FlattenStatus.FLATTEN_IN_PROGRESS

        for attempt in range(1, max_retries + 1):
            try:
                self.logger.info(f"Flatten attempt {attempt}/{max_retries}")

                flatten_response = await self.broker.flatten_all()

                # Check success
                success = flatten_response.get("success", True) if isinstance(
                    flatten_response, dict
                ) else True

                if success:
                    self.flatten_event.status = FlattenStatus.FLATTEN_SUCCESS
                    self.flatten_event.retry_count = attempt

                    self.logger.info(f"Flatten succeeded on attempt {attempt}")
                    return
                else:
                    error = flatten_response.get("error", "Unknown error") if isinstance(
                        flatten_response, dict
                    ) else str(flatten_response)
                    self.logger.warning(f"Flatten attempt {attempt} failed: {error}")

                    if attempt < max_retries:
                        wait_seconds = backoff_seconds * attempt  # exponential backoff
                        self.logger.info(f"Retrying in {wait_seconds}s...")
                        await asyncio.sleep(wait_seconds)

            except Exception as e:
                self.logger.error(f"Exception on flatten attempt {attempt}: {e}")

                if attempt < max_retries:
                    wait_seconds = backoff_seconds * attempt
                    self.logger.info(f"Retrying in {wait_seconds}s...")
                    await asyncio.sleep(wait_seconds)

        # All retries exhausted
        self.flatten_event.status = FlattenStatus.FLATTEN_FAILED
        self.flatten_event.retry_count = max_retries
        self.flatten_event.error_message = (
            "Flatten failed after all retries exhausted"
        )

    async def _post_flatten_verification(self) -> None:
        """
        Verify that all positions are now closed.

        Raises RuntimeError if any position remains open.
        """
        assert self.flatten_event is not None

        try:
            has_open = await self.broker.has_open_position()

            if has_open:
                raise RuntimeError(
                    "POST-FLATTEN CHECK FAILED: positions still open after flatten executed. "
                    "Manual intervention required."
                )

            self.flatten_event.positions_after_count = 0
            self.logger.info("Post-flatten verification passed: all positions closed")

        except Exception as e:
            self.flatten_event.status = FlattenStatus.FLATTEN_FAILED
            self.flatten_event.error_message = str(e)
            raise

    async def _log_compliance_event(self) -> None:
        """
        Record this flatten routine execution to the compliance ledger.
        """
        assert self.flatten_event is not None

        event_details = {
            "routine": "daily_3pm_flatten",
            "status": self.flatten_event.status.value,
            "positions_before": self.flatten_event.positions_before_count,
            "positions_after": self.flatten_event.positions_after_count,
            "pnl_at_flatten": self.flatten_event.pnl_at_flatten,
            "retry_count": self.flatten_event.retry_count,
        }

        from live_bot.pnl_tracker import EventType

        self.pnl_tracker.log_compliance_event(
            event_type=EventType.FLATTEN_EXECUTED,
            details=event_details,
        )

    def can_open_new_position(self) -> bool:
        """
        Called by the main trading loop to check if new entries are allowed.

        Returns False if:
        - Trading is locked (after flatten)
        - It's within 10 minutes of 3:10 PM (prevent late-day entries)

        Returns:
            bool: True if a new position can be opened
        """
        now = datetime.now(tz=CENTRAL_TZ)

        # Trading locked today after flatten
        if self.trading_locked_today:
            return False

        # Prevent entries within 10 minutes of flatten time
        time_until_flatten = self._minutes_until_flatten(now)

        if time_until_flatten < 10:
            self.logger.warning(
                f"Preventing new entries: {time_until_flatten:.1f} min until flatten"
            )
            return False

        return True

    @staticmethod
    def _minutes_until_flatten(now: datetime) -> float:
        """
        Minutes from `now` (must be tz-aware, in CENTRAL_TZ) to the next
        occurrence of the 3:10 PM CT flatten time -- today's if still ahead,
        otherwise tomorrow's.

        Returns:
            float: minutes until the next flatten (always >= 0)
        """
        flatten_dt = now.replace(hour=15, minute=10, second=0, microsecond=0)

        if flatten_dt < now:
            flatten_dt += timedelta(days=1)

        return (flatten_dt - now).total_seconds() / 60

    async def apply_manual_override(self, reason: str) -> None:
        """
        Manual override: force unlock trading / acknowledge flatten failure.

        Used only in emergencies after human review.
        Logged to compliance ledger.

        Args:
            reason: explanation for the override (e.g., "broker API recovered")
        """
        self.trading_locked_today = False

        if self.flatten_event:
            self.flatten_event.manual_override_applied = True

        self.logger.warning(f"Manual override applied: {reason}")

        from live_bot.pnl_tracker import EventType

        self.pnl_tracker.log_compliance_event(
            event_type=EventType.MANUAL_OVERRIDE,
            details={"reason": reason},
        )

    def reset_daily_lock(self) -> None:
        """
        Reset flatten state for next trading day.

        Called at start of new session (e.g., 08:00 AM CT).
        """
        self.trading_locked_today = False
        self.flatten_event = None
        self.logger.info("Daily lock reset for new session")
