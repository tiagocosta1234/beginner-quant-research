"""
INTEGRATION GUIDE: Wiring the three components into the main bot loop.

This module shows how to integrate:
1. PnlTracker (position lifecycle + compliance logging)
2. FlattenRoutine (3:10 PM daily flatten + trading lockout)
3. Deployment framework (credentials, health checks, logging)

Into the existing main.py event loop.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from live_bot.broker_client import BrokerClient, BrokerConfig
from live_bot.pnl_tracker import PnlTracker, EventType
from live_bot.flatten_routine import FlattenRoutine
from live_bot.deployment import (
    CredentialManager,
    ComplianceLogger,
    HealthChecker,
    BrokerCredentials,
)
from live_bot.risk_governor import AccountConfig, RiskGovernor
from live_bot.strategy_interface import Strategy, SignalAction, NoOpStrategy
from zoneinfo import ZoneInfo

CENTRAL_TZ = ZoneInfo("America/Chicago")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("integrated_bot")


class IntegratedTradingBot:
    """
    Main bot orchestrator: integrates all three components.

    Components:
    1. PnlTracker: SQLite position lifecycle + compliance ledger
    2. FlattenRoutine: daily 3:10 PM flatten + trading lock
    3. Deployment: credentials, health checks, logging

    Usage:
        bot = IntegratedTradingBot()
        await bot.initialize()
        await bot.run()
    """

    def __init__(self, db_path: str = "./trading_bot.db", log_dir: str = "./logs"):
        self.db_path = db_path
        self.log_dir = log_dir

        # Core components (initialized in initialize())
        self.broker: BrokerClient | None = None
        self.pnl_tracker: PnlTracker | None = None
        self.flatten_routine: FlattenRoutine | None = None
        self.compliance_logger: ComplianceLogger | None = None
        self.health_checker: HealthChecker | None = None
        self.risk_governor: RiskGovernor | None = None
        self.strategy: Strategy | None = None
        self.scheduler: AsyncIOScheduler | None = None

    async def initialize(self) -> None:
        """
        One-time setup: load credentials, connect broker, start scheduler.

        Call this once at bot startup, before run().
        """
        logger.info("=== Initializing Integrated Trading Bot ===")

        # 1. Load credentials
        logger.info("Loading broker credentials...")
        cred_manager = CredentialManager(vault_db_path="./.vault.db")
        try:
            creds = cred_manager.load_credentials(use_vault=True)
        except Exception as e:
            logger.warning(f"Vault load failed, falling back to env: {e}")
            creds = cred_manager.load_credentials(use_vault=False)

        # Set environment for broker
        for key, value in creds.to_env_dict().items():
            import os

            os.environ[key] = value

        # 2. Initialize components
        logger.info("Initializing components...")

        # Broker
        broker_config = BrokerConfig.from_env()
        self.broker = BrokerClient(broker_config)
        await self.broker.connect()

        # PnL Tracker
        self.pnl_tracker = PnlTracker(db_path=self.db_path, logger=logger)

        # Compliance logging
        self.compliance_logger = ComplianceLogger(log_dir=self.log_dir, logger=logger)

        # Health checker
        self.health_checker = HealthChecker(broker=self.broker, logger=logger)

        # Risk governor
        account_config = AccountConfig()
        self.risk_governor = RiskGovernor(
            account_config,
            starting_balance=self.broker.get_account_balance() or 250_000.0,
            starting_high_water_mark=250_877.88,
        )
        self.risk_governor.start_new_trading_day(datetime.now(tz=CENTRAL_TZ).date())

        # Strategy (default: NoOp)
        import os

        strategy_name = os.getenv("BOT_STRATEGY", "noop").lower()
        if strategy_name == "noop":
            self.strategy = NoOpStrategy()
        else:
            # Load real strategy (implement as needed)
            self.strategy = NoOpStrategy()

        # Flatten routine + scheduler
        self.scheduler = AsyncIOScheduler()
        self.flatten_routine = FlattenRoutine(
            broker=self.broker,
            account_config=account_config,
            pnl_tracker=self.pnl_tracker,
            logger=logger,
        )
        await self.flatten_routine.schedule(self.scheduler)

        logger.info("✓ All components initialized")

    async def run(self) -> None:
        """
        Main event loop: strategy polling, risk governance, flatten scheduling.

        This is the core trading loop. Runs indefinitely until stopped.
        """
        if not all(
            [
                self.broker,
                self.pnl_tracker,
                self.flatten_routine,
                self.compliance_logger,
                self.risk_governor,
                self.strategy,
                self.scheduler,
            ]
        ):
            raise RuntimeError("Components not initialized; call initialize() first")

        # Start scheduler
        self.scheduler.start()

        logger.info("=== Trading loop started ===")

        poll_interval_seconds = 30
        health_check_interval_seconds = 60
        last_health_check = datetime.now(tz=CENTRAL_TZ)

        try:
            while True:
                now = datetime.now(tz=CENTRAL_TZ)

                # --- Health check (every 60 seconds) ---
                if (now - last_health_check).total_seconds() > health_check_interval_seconds:
                    health_status = await self.health_checker.check_health()
                    self.compliance_logger.log_health(health_status)
                    last_health_check = now

                # --- Poll strategy ---
                try:
                    # Get unrealized P&L first
                    unrealized_pnl = await self.broker.get_unrealized_pnl()
                    self.risk_governor.update_unrealized_pnl(unrealized_pnl)

                    # Evaluate risk constraints
                    decision = self.risk_governor.evaluate(now)

                    # Handle risk breaches
                    if decision.must_flatten_now:
                        logger.warning(f"Risk breach: {decision.reasons}")
                        self.compliance_logger.log_risk_decision(
                            decision="FLATTEN_IMMEDIATE",
                            reason=", ".join(r.name for r in decision.reasons),
                            details={
                                "unrealized_pnl": unrealized_pnl,
                                "buffer_remaining": decision.remaining_drawdown_buffer,
                            },
                        )
                        await self.broker.flatten_all()
                        self.pnl_tracker.log_compliance_event(
                            event_type=EventType.RISK_BREACH,
                            details={
                                "reasons": [r.name for r in decision.reasons],
                                "unrealized_pnl": unrealized_pnl,
                            },
                        )

                        # Hard breach: stop bot
                        if any(
                            r.name in ["TRAILING_DRAWDOWN", "DAILY_LOSS_LIMIT"]
                            for r in decision.reasons
                        ):
                            logger.error(
                                "Hard risk breach encountered. Stopping bot for the session."
                            )
                            break

                    # Check if new entries are allowed (blocked before 3:10 PM flatten)
                    elif (
                        decision.can_open_new_position
                        and self.flatten_routine.can_open_new_position()
                    ):
                        # Get bars and generate signal
                        bars_needed = (
                            3000
                            if hasattr(self.strategy, "__class__")
                            and "SupportResistance" in self.strategy.__class__.__name__
                            else 500
                        )
                        bars = await self.broker.get_bars(
                            bars=bars_needed, timeframe="1min"
                        )

                        signal = self.strategy.on_bar(bars)

                        if signal.action in (SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT):
                            await self._handle_entry_signal(signal, now)

                except Exception as e:
                    logger.error(f"Error in trading loop: {e}", exc_info=True)

                # Poll interval
                await asyncio.sleep(poll_interval_seconds)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt; shutting down")
        finally:
            await self.shutdown()

    async def _handle_entry_signal(self, signal, now: datetime) -> None:
        """
        Process an entry signal: risk check, order placement, P&L tracking.

        Args:
            signal: Signal object from strategy
            now: current timestamp
        """
        logger.info(f"Entry signal received: {signal.action} ({signal.reason})")

        # Check position size
        risk_dollars = signal.risk_dollars or 700.0
        size_allowed, rejection_reason = self.risk_governor.check_position_size(
            risk_dollars
        )

        if not size_allowed:
            logger.warning(f"Position size rejected: {rejection_reason}")
            self.compliance_logger.log_risk_decision(
                decision="ENTRY_REJECTED",
                reason=rejection_reason,
                details={"proposed_risk": risk_dollars},
            )
            return

        # Place order
        try:
            contract_id = self.broker.get_contract_id()
            side = 0 if signal.action == SignalAction.ENTER_LONG else 1

            logger.info(
                f"Placing order: {signal.action} {signal.size} @ contract {contract_id}"
            )

            entry_response, trail_response = await self.broker.place_market_entry_with_trailing_stop(
                contract_id=contract_id,
                side=side,
                size=signal.size,
                trail_price=signal.trail_distance_points or 20.0,
            )

            # Record in P&L tracker
            order_id = entry_response.get("order_id", "unknown")
            entry_price = entry_response.get("fill_price", 0.0)

            position = self.pnl_tracker.record_entry_fill(
                instrument="MNQ",  # TODO: get from config
                entry_price=entry_price,
                entry_quantity=signal.size,
                side="LONG" if signal.action == SignalAction.ENTER_LONG else "SHORT",
                order_id=order_id,
                broker_response=entry_response,
            )

            self.compliance_logger.log_entry(
                signal=signal.action.name,
                size=signal.size,
                entry_price=entry_price,
                reason=signal.reason,
            )

            logger.info(f"✓ Entry recorded: pos_id={position.id}, P&L tracking active")

        except Exception as e:
            logger.error(f"Error placing entry order: {e}", exc_info=True)

    async def shutdown(self) -> None:
        """Clean shutdown: disconnect broker, flush logs, save state."""
        logger.info("=== Shutting down ===")

        if self.scheduler:
            self.scheduler.shutdown()

        if self.broker:
            await self.broker.disconnect()

        # Generate end-of-day summary
        if self.pnl_tracker:
            today = datetime.now(tz=CENTRAL_TZ).date()
            summary = self.pnl_tracker.daily_summary_report(today)
            self.compliance_logger.log_daily_summary(summary)

        logger.info("✓ Shutdown complete")


# --- CLI ENTRY POINTS ---


async def main():
    """Main entry point: initialize and run the bot."""
    bot = IntegratedTradingBot(
        db_path="./trading_bot.db",
        log_dir="./logs",
    )

    await bot.initialize()
    await bot.run()


def setup_vault():
    """CLI: one-time vault setup."""
    import sys

    if len(sys.argv) < 4:
        print("Usage: python -m deployment vault <api_key> <username> <account_name>")
        sys.exit(1)

    api_key = sys.argv[2]
    username = sys.argv[3]
    account_name = sys.argv[4]

    creds = BrokerCredentials(
        api_key=api_key,
        username=username,
        account_name=account_name,
    )

    encryption_key = CredentialManager.setup_vault("./.vault.db", creds)
    print(f"\n✓ Vault created. Export this key:")
    print(f"  export VAULT_ENCRYPTION_KEY={encryption_key}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "vault":
        setup_vault()
    else:
        asyncio.run(main())
