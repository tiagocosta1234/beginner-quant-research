"""Entry point wiring risk_governor + broker_client + strategy_interface together.

Modes (BOT_MODE, default "dry_run"):
  dry_run  - no network calls at all; proves the pieces import and wire up. The default,
             so nothing runs live by accident.
  practice - a simulated/demo account through your own BrokerClient subclass.
  live     - a real account; also requires BOT_CONFIRM_LIVE=I_UNDERSTAND_THIS_IS_REAL_MONEY.
             Do not use before a strategy has passed out-of-sample validation and the whole
             pipeline has run on a practice account.

Strategy (BOT_STRATEGY, default "noop", which always holds; choosing a strategy is a
deliberate decision this file will not make for you):
  random_entry_atr_trail     - random side with an ATR trailing stop (MNQ), Rounds 19-26
  support_resistance_bounce  - support/resistance bounce (MGC), Rounds 30/30b
  vwap_zscore                - VWAP z-score fade (MNQ), Round 49
  manual                     - time-of-day filter plus VWAP-Z in one MNQ process; per-signal
                               sizing lives in manual_strategy.py (MAX_SINGLE_TRADE_RISK must
                               allow it, paired with SELF_IMPOSED_DAILY_STOP)
  ote_fvg                    - OTE retracement plus 15m FVG sweep-reclaim, NY session (Round 76/87)
  disciplined_bracket        - POC reversion plus value-area rejection with a capped daily win
                               (Round 192), one leg at a time
  combined                   - the same two legs, uncapped, with a pre-trained meta-label filter

Each strategy trades one instrument; two instruments mean two bot processes. Read each
strategy file's docstring before using it: none of them kept an edge out of sample.

Sizing: fixed AccountConfig.max_single_trade_risk per trade by default; BOT_DYNAMIC_SIZING=1
switches to equity-scaled sizing (risk_governor.DynamicSizingConfig).
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
import os
import sys
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Load .env BEFORE importing any live_bot module: strategy modules read their sizing from the
# environment at import time, and loading it later once sent the first practice trade out at a
# third of the intended size.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:  # pragma: no cover - dotenv is a convenience, not a hard requirement
    pass

from live_bot.broker_client import BrokerClient, BrokerConfig, create_broker
from live_bot.combined_strategy import CombinedStrategy
from live_bot.disciplined_bracket_strategy import DisciplinedBracketStrategy
from live_bot.fill_recorder import FillRecorder, trading_date
from live_bot.flatten_routine import FlattenRoutine, AlertHandler
from live_bot.health_check import HealthCheck, HealthStatus
from live_bot.manual_strategy import ManualStrategy
from live_bot.ote_fvg_strategy import OteFvgStrategy
from live_bot.pnl_tracker import PnlTracker
from live_bot.random_entry_atr_trail_strategy import RandomEntryAtrTrailStrategy
from live_bot.risk_governor import AccountConfig, RiskGovernor
from live_bot.strategy_interface import NoOpStrategy, SignalAction, Strategy
from live_bot.support_resistance_bounce_strategy import SupportResistanceBounceStrategy
from live_bot.vwap_zscore_strategy import VwapZScoreStrategy

# CME contract point values (dollars per 1.0 index-point move, standard published
# specs, not a research finding -- MNQ: Micro E-mini Nasdaq-100, $2/point; MGC:
# Micro Gold, $10/point). Both instruments now have a validated edge (MNQ:
# Rounds 19-26; MGC: Rounds 30/30b) -- see BOT_STRATEGY in this module's
# docstring for which Strategy class pairs with which instrument.
POINT_VALUE = {"MNQ": 2.0, "MGC": 10.0}

# BUGFIX (2026-09-21): the installed brokerapi_py SDK logs several messages
# containing emoji (e.g. "\U0001F4E1 Real-time client connected"). Windows'
# default console codepage (cp1252) can't encode them, which previously raised
# repeated non-fatal UnicodeEncodeError "Logging error" tracebacks on every
# such line -- noisy enough to bury a real error. Reconfiguring stdout/stderr
# to UTF-8 (falling back silently on interpreters too old to support it) fixes
# this without touching the SDK.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except Exception:  # pragma: no cover - best-effort only
            pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("live_bot")

POLL_INTERVAL_SECONDS = 30

# Example seed values used when ACCOUNT_STARTING_BALANCE / ACCOUNT_STARTING_HWM are not set. In practice
# or live mode the broker's balance overrides the balance once connected; the high-water mark must be
# set by you, since brokers rarely report it.
FALLBACK_STARTING_BALANCE = 250_000.0
FALLBACK_STARTING_HWM = 250_000.0


def _select_strategy() -> Strategy:
    name = os.getenv("BOT_STRATEGY", "noop").lower()
    if name == "noop":
        return NoOpStrategy()
    if name == "random_entry_atr_trail":
        log.warning(
            "BOT_STRATEGY=random_entry_atr_trail: random side with an ATR trailing stop (Rounds 19-26); a control strategy, practice only."
        )
        tod_filter = os.getenv("BOT_TOD_FILTER", "0") == "1"
        if tod_filter:
            log.warning(
                "BOT_TOD_FILTER=1: entries restricted to the last third of the RTH session (Round 39)."
            )
        return RandomEntryAtrTrailStrategy(tod_filter=tod_filter)
    if name == "support_resistance_bounce":
        log.warning(
            "BOT_STRATEGY=support_resistance_bounce: MGC support/resistance bounce (Rounds 30/30b); see the strategy docstring for the level-detection caveat; practice only."
        )
        return SupportResistanceBounceStrategy()
    if name == "vwap_zscore":
        log.warning(
            "BOT_STRATEGY=vwap_zscore: MNQ VWAP z-score fade (Round 49); practice only."
        )
        return VwapZScoreStrategy()
    if name == "manual":
        log.warning(
            "BOT_STRATEGY=manual: time-of-day filter plus VWAP-Z in one MNQ process; per-signal sizing is set in manual_strategy.py; practice only."
        )
        return ManualStrategy()
    if name == "ote_fvg":
        log.warning(
            "BOT_STRATEGY=ote_fvg: OTE retracement plus 15m FVG sweep-reclaim, NY session entries (Rounds 76/87); practice only."
        )
        return OteFvgStrategy()
    if name == "disciplined_bracket":
        log.warning(
            "BOT_STRATEGY=disciplined_bracket: POC reversion plus value-area rejection with a capped daily win (Round 192), one leg at a time; the first session produces no entry by design; practice only."
        )
        return DisciplinedBracketStrategy()
    if name == "combined":
        log.warning(
            "BOT_STRATEGY=combined: the same two legs, uncapped, filtered by the pre-trained meta-label model (poc_meta_model.json); practice only."
        )
        return CombinedStrategy()
    raise ValueError(
        f"Unknown BOT_STRATEGY={name!r}, must be one of: noop, random_entry_atr_trail, "
        "support_resistance_bounce, vwap_zscore, manual, ote_fvg, disciplined_bracket, "
        "combined"
    )


FILL_LOOKUP_ATTEMPTS, FILL_LOOKUP_DELAY_S = 5, 0.3


async def reanchor_stop_to_fill(signal, response, side: int, broker: BrokerClient, *, since) -> None:
    """Move a just-placed bracket's stop so it sits the planned distance from the
    ACTUAL entry fill, not from signal.entry_reference_price. A market entry can fill
    points away from the price the strategy planned from (2026-09-30: short planned
    at 30,701.50, filled 30,690.75); a stop left at the planned price then risks more
    (or less) than the $ the contracts were sized for. The target is left as placed.

    Never raises: if the fill can't be seen or the broker rejects the move (e.g. price
    already went through the new level), the original stop stays in place and this
    logs an error -- the position is never left without a stop."""
    entry_id = getattr(response, "entry_order_id", None)
    stop_id = getattr(response, "stop_order_id", None)
    if not getattr(response, "success", False) or entry_id is None or stop_id is None:
        log.warning(
            "Cannot re-anchor stop to fill: bracket response has no entry/stop order id "
            "(success=%s entry=%s stop=%s); stop stays at planned %s",
            getattr(response, "success", None), entry_id, stop_id, signal.stop_loss_price,
        )
        return
    fill = None
    for _ in range(FILL_LOOKUP_ATTEMPTS):
        try:
            fill = await broker.get_entry_fill_price(entry_id, since)
        except Exception as e:  # noqa: BLE001 -- a lookup failure must not kill the loop
            log.warning("Fill-price lookup for order %s failed: %s", entry_id, e)
        if fill is not None:
            break
        await asyncio.sleep(FILL_LOOKUP_DELAY_S)
    if fill is None:
        log.error(
            "Entry order %s fill price not visible after %d lookups; stop stays at planned %s",
            entry_id, FILL_LOOKUP_ATTEMPTS, signal.stop_loss_price,
        )
        return
    direction = 1 if side == 0 else -1
    distance = abs(signal.entry_reference_price - signal.stop_loss_price)
    new_stop = round(fill - direction * distance, 6)
    adverse = direction * (fill - signal.entry_reference_price)  # > 0: filled worse than planned
    if new_stop == signal.stop_loss_price:
        log.info("Entry filled at the planned %.2f; stop stays at %.2f", fill, new_stop)
        return
    try:
        ok = await broker.modify_stop_price(stop_id, new_stop)
    except Exception as e:  # noqa: BLE001
        log.error("Stop modify for order %s raised: %s", stop_id, e)
        ok = False
    if ok:
        log.info(
            "Stop re-anchored to fill: filled %.2f vs planned %.2f (%+.2f pts against), "
            "stop %.2f -> %.2f (distance %.2f kept)",
            fill, signal.entry_reference_price, adverse, signal.stop_loss_price, new_stop, distance,
        )
    else:
        log.error(
            "Stop re-anchor REJECTED: wanted %.2f (fill %.2f + planned distance %.2f); "
            "original stop %.2f stays in place",
            new_stop, fill, distance, signal.stop_loss_price,
        )


async def handle_entry_signal(
    signal,
    *,
    broker: BrokerClient,
    governor: RiskGovernor,
    account_config: AccountConfig,
    broker_config: BrokerConfig,
) -> None:
    """Everything from 'a signal wants to enter' through 'an order was placed (or
    safely refused)'. Extracted out of run()'s poll loop as its own function
    specifically so it can be exercised by an integration test
    (tests/test_main_integration.py) against fake broker/governor objects,
    without needing a real network connection or a real API key -- this is the
    exact seam where a real bug (the poll-count-vs-bar-count mismatch caught
    while building random_entry_atr_trail_strategy.py) previously hid, because
    the strategy and the governor were each unit-tested in isolation but their
    wiring together here never was, until now.

    Caller contract: only invoke this when `signal.action` is ENTER_LONG or
    ENTER_SHORT (run()'s loop already filters on that) -- this function assumes
    it, it does not re-check.
    """
    if await broker.has_open_position():
        log.info(
            "Signal %s (%s) received but a position is already open on %s; ignoring.",
            signal.action, signal.reason, broker_config.instrument,
        )
        return

    uses_bracket_shape = signal.stop_loss_price is not None and signal.take_profit_price is not None
    uses_trailing_shape = (
        signal.initial_stop_distance_points is not None and signal.trail_distance_points is not None
    )
    if not uses_bracket_shape and not uses_trailing_shape:
        log.error(
            "Signal %s has neither a complete stop_loss_price/take_profit_price "
            "pair nor a complete initial_stop_distance_points/trail_distance_points "
            "pair -- refusing to place an order without risk governance able to see "
            "a defined stop. reason=%s",
            signal.action, signal.reason,
        )
        return

    # Resolve the dollar risk to actually use: dynamic sizing (if enabled)
    # overrides whatever the strategy proposed, since sizing policy is risk
    # governance's call, not the strategy's -- see risk_governor.py rule 7 and
    # Signal's docstring on risk_dollars.
    dynamic_risk = governor.compute_dynamic_risk()
    risk_dollars = dynamic_risk if dynamic_risk is not None else signal.risk_dollars
    if risk_dollars is None:
        risk_dollars = account_config.max_single_trade_risk
        log.info(
            "Signal %s gave no risk_dollars and dynamic sizing is disabled -- "
            "falling back to max_single_trade_risk=$%.2f",
            signal.action, risk_dollars,
        )

    size_allowed, size_rejection_reason = governor.check_position_size(
        risk_dollars, proposed_reward_dollars=signal.expected_reward_dollars,
    )
    if not size_allowed:
        log.warning(
            "Signal %s rejected by check_position_size: %s (proposed risk_dollars=%s)",
            signal.action, size_rejection_reason, risk_dollars,
        )
        return

    contract_id = broker.get_contract_id()
    side = 0 if signal.action == SignalAction.ENTER_LONG else 1  # 0=buy/long, 1=sell/short

    if uses_trailing_shape:
        point_value = POINT_VALUE.get(broker_config.instrument)
        if not point_value:
            log.error(
                "No POINT_VALUE entry for instrument=%s -- cannot convert "
                "risk_dollars into a contract count. Add it to main.py's "
                "POINT_VALUE dict before using this instrument with a "
                "trailing-stop strategy.",
                broker_config.instrument,
            )
            return
        # Sized against trail_distance_points (the stop actually placed via
        # place_market_entry_with_trailing_stop below), NOT initial_stop_distance_points.
        # Bug found 2026-09-21/22 in the backtest engine and confirmed present here too:
        # trail_distance_points = TRAIL_ATR_MULT(1.5) x initial_stop_distance_points, so
        # sizing against the tighter initial distance let a trade that never gets a
        # favorable move realize ~1.5x the intended risk_dollars (matches Round 69's
        # finding: nominal $2,400 -> real worst-case losses up to $3,636). Sizing against
        # trail_distance_points makes risk_dollars mean what it says.
        contracts = max(1, int(risk_dollars // (signal.trail_distance_points * point_value)))
        log.info(
            "Placing market entry + trailing stop: %s size=%s risk=$%.2f "
            "trail_dist=%.2f contract=%s (%s)",
            signal.action, contracts, risk_dollars,
            signal.trail_distance_points, contract_id, signal.reason,
        )
        entry_resp, trail_resp = await broker.place_market_entry_with_trailing_stop(
            contract_id=contract_id,
            side=side,
            size=contracts,
            trail_price=signal.trail_distance_points,
        )
        if not getattr(trail_resp, "success", True):
            log.error(
                "Trailing-stop placement failed after entry filled (entry=%s, "
                "trail=%s) -- position is OPEN WITH NO PROTECTIVE STOP. "
                "Flattening immediately.",
                entry_resp, trail_resp,
            )
            await broker.flatten_all()
    else:
        log.info(
            "Placing bracket order: %s size=%s SL=%s TP=%s contract=%s (%s)",
            signal.action, signal.size, signal.stop_loss_price,
            signal.take_profit_price, contract_id, signal.reason,
        )
        placed_at = dt.datetime.now(dt.timezone.utc)
        response = await broker.place_bracket_order(
            contract_id=contract_id,
            side=side,
            size=signal.size,
            entry_price=None,  # market entry
            stop_loss_price=signal.stop_loss_price,
            take_profit_price=signal.take_profit_price,
        )
        if signal.entry_reference_price is not None:
            await reanchor_stop_to_fill(signal, response, side, broker, since=placed_at - dt.timedelta(minutes=5))
        # NOTE (README item #6): record_fill() is not called here or anywhere in
        # the live loop yet -- ORDER_FILLED events are still not subscribed to,
        # so the governor's daily_realized_pnl/current_balance will NOT update
        # from this order closing. Only the unrealized_pnl polling in run()
        # reflects real-time reality until that's wired up. Applies to the
        # trailing-stop path above too.


async def run() -> None:
    """
    Main BrokerAPI polling loop: integrated with PnLTracker, FlattenRoutine, HealthCheck.

    Initialization:
      1. Load broker config, strategy, account config
      2. Initialize PnLTracker (SQLite compliance ledger)
      3. Initialize FlattenRoutine + APScheduler (3:10 PM CT daily flatten)
      4. Initialize HealthCheck (periodic broker/data freshness monitoring)
      5. Connect broker and seed RiskGovernor with live balance if available

    Each polling cycle (every POLL_INTERVAL_SECONDS):
      1. Run health check; log/alert on degradation
      2. Query fills from broker (unrealized P&L, open positions)
      2b. Reconcile governor's tracked balance against broker.get_account_balance()
          (risk_governor.py rule 10) -- catches untracked account activity
      3. Feed fills to PnLTracker (record entries/exits for compliance)
      4. Evaluate flatten routine checks (can_open_new_position(), time-based locks)
      5. Evaluate risk governor (must_flatten_now?, can_open_new_position?)
      6. If risk or flatten signals → halt trading, execute flatten, lock trading
      7. If can trade → query bars, run strategy, place signal orders
      8. Log all state changes to compliance ledger

    Shutdown:
      - Finalize P&L (daily summary to compliance ledger)
      - Close any open positions safely
      - Shutdown scheduler and broker
    """
    broker_config = BrokerConfig.from_env()
    dynamic_sizing = None
    if os.getenv("BOT_DYNAMIC_SIZING", "0") == "1":
        from live_bot.risk_governor import DynamicSizingConfig

        dynamic_sizing = DynamicSizingConfig()
        log.warning(
            "BOT_DYNAMIC_SIZING=1: risk-per-trade will scale with the account's current "
            "buffer (frac_below_start=%.2f, frac_above_start=%.2f) instead of a fixed "
            "dollar amount. This is a real risk-tolerance choice -- see "
            "risk_governor.DynamicSizingConfig's docstring and EDGE_VALIDATION_RESULTS.md "
            "Round 26 before relying on it.",
            dynamic_sizing.frac_below_start, dynamic_sizing.frac_above_start,
        )
    # Both overrides below keep AccountConfig's own defaults ($700 cap, 2-loss
    # lockout) unless explicitly set -- same deliberate-opt-in pattern as
    # BOT_STRATEGY/BOT_DYNAMIC_SIZING/BOT_TOD_FILTER above, since raising the
    # per-trade risk ceiling or loosening the loss lockout are real
    # risk-tolerance decisions this code should never make silently.
    max_single_trade_risk = float(os.getenv("MAX_SINGLE_TRADE_RISK", "700"))
    consecutive_loss_limit = int(os.getenv("CONSECUTIVE_LOSS_LIMIT", "2"))
    if max_single_trade_risk != 700.0 or consecutive_loss_limit != 2:
        log.warning(
            "Risk-governance defaults overridden: max_single_trade_risk=$%.0f "
            "(default $700), consecutive_loss_limit=%d (default 2). Confirm this "
            "is deliberate -- these are the two rules directly protecting the "
            "remaining buffer.",
            max_single_trade_risk, consecutive_loss_limit,
        )
    # Opt-in, disabled unless set -- see risk_governor.py rule 8. This is the
    # account holder's own tighter-than-DLL choice (Round 69, 2026-09-22), not a
    # Broker rule, so it stays None (no effect) unless explicitly configured.
    _self_imposed_env = os.getenv("SELF_IMPOSED_DAILY_STOP")
    self_imposed_daily_stop = float(_self_imposed_env) if _self_imposed_env else None
    if self_imposed_daily_stop is not None:
        log.warning(
            "SELF_IMPOSED_DAILY_STOP=$%.0f active: new entries will be refused once "
            "today's realized+floating P&L, minus the proposed trade's own risk, "
            "would already be at or past -$%.0f. This is tighter than the real "
            "Broker daily_loss_limit and is enforced in check_position_size(), "
            "before any order is placed (Round 69).",
            self_imposed_daily_stop, self_imposed_daily_stop,
        )
    _max_daily_profit_env = os.getenv("MAX_DAILY_PROFIT")
    max_daily_profit = float(_max_daily_profit_env) if _max_daily_profit_env else None
    if max_daily_profit is not None:
        log.warning(
            "MAX_DAILY_PROFIT=$%.0f active: new entries refused once today's P&L is "
            "at/past this cap, or a full-target win on the proposed trade would push "
            "it past this cap -- see risk_governor.py rule 12.",
            max_daily_profit,
        )
    _profit_target_balance_env = os.getenv("PROFIT_TARGET_BALANCE")
    account_config_kwargs = dict(
        dynamic_sizing=dynamic_sizing,
        max_single_trade_risk=max_single_trade_risk,
        consecutive_loss_limit=consecutive_loss_limit,
        self_imposed_daily_stop=self_imposed_daily_stop,
        max_daily_profit=max_daily_profit,
    )
    if _profit_target_balance_env:
        account_config_kwargs["profit_target_balance"] = float(_profit_target_balance_env)
    # AccountConfig's defaults are examples; set TRAILING_DD_AMOUNT and DAILY_LOSS_LIMIT to your own limits.
    _trailing_dd_env = os.getenv("TRAILING_DD_AMOUNT")
    if _trailing_dd_env:
        account_config_kwargs["trailing_dd_amount"] = float(_trailing_dd_env)
        log.warning(
            "TRAILING_DD_AMOUNT=$%.0f active (default $10,000) -- confirm this matches whatever account is actually "
            "connected before trusting remaining_drawdown_buffer().",
            float(_trailing_dd_env),
        )
    _daily_loss_limit_env = os.getenv("DAILY_LOSS_LIMIT")
    if _daily_loss_limit_env:
        account_config_kwargs["daily_loss_limit"] = float(_daily_loss_limit_env)
        log.warning(
            "DAILY_LOSS_LIMIT=$%.0f active (default $5,000) -- confirm this matches whatever account is actually "
            "connected before trusting daily_loss_breached().",
            float(_daily_loss_limit_env),
        )
    account_config = AccountConfig(**account_config_kwargs)  # every limit here is a setting; set yours before any live use

    log.info("Starting live_bot in mode=%s instrument=%s", broker_config.mode, broker_config.instrument)

    starting_balance = float(os.getenv("ACCOUNT_STARTING_BALANCE", FALLBACK_STARTING_BALANCE))
    starting_hwm = float(os.getenv("ACCOUNT_STARTING_HWM", FALLBACK_STARTING_HWM))

    strategy = _select_strategy()  # defaults to NoOpStrategy -- see module docstring's BOT_STRATEGY section

    # =========================================================================
    # INITIALIZATION: Wire PnLTracker, FlattenRoutine, HealthCheck, Scheduler
    # =========================================================================

    # Initialize PnLTracker (SQLite compliance ledger)
    db_path = os.getenv("BOT_DB_PATH", "./trading_bot.db")
    pnl_tracker = PnlTracker(db_path=db_path, logger=log)
    log.info(f"PnLTracker initialized: db_path={db_path}")

    # Initialize broker and connect
    broker = create_broker(broker_config)
    await broker.connect()

    if broker_config.mode != "dry_run":
        live_balance = broker.get_account_balance()
        if live_balance is not None:
            log.info("Seeding governor from live account balance: $%.2f (env/fallback was $%.2f)",
                      live_balance, starting_balance)
            starting_balance = live_balance
        else:
            log.warning(
                "Could not fetch live account balance; falling back to $%.2f "
                "(env ACCOUNT_STARTING_BALANCE or hardcoded fallback). Verify this is "
                "still accurate before trusting the risk governor's numbers.",
                starting_balance,
            )

    # Initialize RiskGovernor. state_file persists the cross-restart state that
    # has no live-broker equivalent (prior_days_pnl, consecutive_losing_days,
    # high_water_mark, today's own daily_realized_pnl/consecutive_losses) -- see
    # risk_governor.RiskGovernor's class docstring. Defaults to a path scoped to
    # this account (BROKERAPI_ACCOUNT_NAME) so switching accounts (e.g. Practice
    # vs. a real Test) can never load another account's state by accident.
    _account_slug = "".join(
        c if c.isalnum() or c in "-_" else "_" for c in os.getenv("BROKERAPI_ACCOUNT_NAME", "default")
    )
    state_file = os.getenv("RISK_STATE_FILE", f"./live_bot/state/risk_state_{_account_slug}.json")
    governor = RiskGovernor(
        account_config,
        starting_balance=starting_balance,
        starting_high_water_mark=starting_hwm,
        state_file=state_file,
    )
    log.info("RiskGovernor state persistence: %s", state_file)
    # Broker's trading day starts at 5 PM CT (fill_recorder.trading_date); the loop
    # below rolls the day over the same way while running.
    governor.start_new_trading_day(trading_date(dt.datetime.now(tz=account_config.timezone)))
    fill_recorder = FillRecorder(logger=log)

    # Initialize FlattenRoutine + APScheduler
    scheduler = AsyncIOScheduler()
    alert_handler = AlertHandler()
    flatten_routine = FlattenRoutine(
        broker=broker,
        account_config=account_config,
        pnl_tracker=pnl_tracker,
        alert_handler=alert_handler,
        logger=log,
    )
    await flatten_routine.schedule(scheduler)
    scheduler.start()
    log.info("FlattenRoutine scheduled; APScheduler started")

    # Initialize HealthCheck
    health_check = HealthCheck(
        broker=broker,
        account_config=account_config,
        logger=log,
    )
    log.info("HealthCheck initialized")

    if broker_config.mode == "dry_run":
        decision = governor.evaluate(dt.datetime.now(tz=account_config.timezone))
        log.info(
            "Dry run smoke test OK. No network calls made. Risk decision: "
            "can_open=%s reasons=%s buffer=$%.2f",
            decision.can_open_new_position,
            decision.reasons,
            decision.remaining_drawdown_buffer,
        )
        scheduler.shutdown()
        return

    # =========================================================================
    # MAIN POLLING LOOP
    # =========================================================================
    cycle_count = 0
    try:
        while True:
            cycle_count += 1
            now = dt.datetime.now(tz=account_config.timezone)

            try:
                # --- 0. New Broker trading day (5 PM CT): roll the governor's daily
                # counters. Before 2026-09-30 this only happened at process start, so a
                # bot left running past the boundary kept yesterday's realized P&L in
                # today's daily-loss check once fills started being recorded.
                if governor.current_trading_date != trading_date(now):
                    governor.start_new_trading_day(trading_date(now), opening_balance=broker.get_account_balance())
                    log.info("[Cycle %d] New trading day %s: governor daily counters rolled over",
                             cycle_count, governor.current_trading_date)

                # --- 1. Health check ---
                health_report = await health_check.check()
                if health_report.overall_status == HealthStatus.CRITICAL:
                    log.error(
                        "CRITICAL health status. Issues: %s. Stopping bot.",
                        ", ".join(health_report.issues),
                    )
                    break

                # --- 2. Query fills from broker (P&L snapshot) ---
                try:
                    unrealized_pnl = await broker.get_unrealized_pnl()
                    governor.update_unrealized_pnl(unrealized_pnl)
                    log.debug(f"[Cycle {cycle_count}] Unrealized P&L: ${unrealized_pnl:.2f}")
                except Exception as e:
                    log.error(f"Failed to get unrealized P&L: {e}")
                    pnl_tracker.log_compliance_event(
                        event_type=__import__("live_bot.pnl_tracker", fromlist=["EventType"]).EventType.RISK_BREACH,
                        details={"error": f"get_unrealized_pnl failed: {str(e)}"},
                        account_balance=governor.current_balance,
                        unrealized_pnl=0.0,
                    )

                # --- 2a. Record this bot's own closed trades in the governor (record_fill)
                # BEFORE reconciling, so a normal closed trade is not read as untracked
                # activity. See fill_recorder.py.
                try:
                    realized = await fill_recorder.update(broker, governor, now)
                    if realized is not None:
                        pnl_tracker.log_compliance_event(
                            event_type=__import__("live_bot.pnl_tracker", fromlist=["EventType"]).EventType.POSITION_FULLY_CLOSED,
                            details={"realized_pnl": realized, "daily_realized_pnl": governor.daily_realized_pnl},
                            instrument=broker_config.instrument,
                            account_balance=governor.current_balance,
                        )
                except Exception as e:
                    log.error(f"[Cycle {cycle_count}] Fill recording failed: {e}")

                # --- 2b. Reconcile tracked balance against the broker's live settled
                # balance (risk_governor.py rule 10). No network call -- reads the
                # same cached account_info get_account_balance() already uses at
                # startup. Catches untracked account activity (e.g. a manual trade)
                # before it can silently invalidate every other check below. Skipped
                # only while this bot's own just-closed trade is still settling
                # (bounded by FillRecorder.max_wait_cycles).
                live_balance = broker.get_account_balance()
                if live_balance is not None and not fill_recorder.settling and not governor.reconcile_balance(live_balance):
                    log.error(
                        "[Cycle %d] BALANCE RECONCILIATION MISMATCH: tracked=$%.2f "
                        "live=$%.2f diff=$%.2f (tolerance $%.2f) -- account moved in a "
                        "way this bot never recorded. Treating as a hard breach.",
                        cycle_count, governor.current_balance, live_balance,
                        governor.last_reconciliation_diff, account_config.balance_reconciliation_tolerance,
                    )
                    pnl_tracker.log_compliance_event(
                        event_type=__import__("live_bot.pnl_tracker", fromlist=["EventType"]).EventType.RISK_BREACH,
                        details={
                            "error": "balance_reconciliation_mismatch",
                            "tracked_balance": governor.current_balance,
                            "live_balance": live_balance,
                            "diff": governor.last_reconciliation_diff,
                        },
                        account_balance=governor.current_balance,
                    )

                # --- 3. Evaluate risk governor ---
                decision = governor.evaluate(now)
                log.debug(
                    f"[Cycle {cycle_count}] Risk decision: can_open={decision.can_open_new_position} "
                    f"must_flatten={decision.must_flatten_now} buffer=${decision.remaining_drawdown_buffer:.2f}"
                )

                # --- 4. Check flatten routine (time-based + lock checks) ---
                can_open_per_flatten = flatten_routine.can_open_new_position()
                combined_can_open = decision.can_open_new_position and can_open_per_flatten

                # --- 5a. Risk or flatten signal → halt trading, execute flatten ---
                if decision.must_flatten_now:
                    log.warning(f"[Cycle {cycle_count}] Flatten triggered by risk governor: {decision.reasons}")
                    try:
                        await broker.flatten_all()
                        pnl_tracker.log_compliance_event(
                            event_type=__import__("live_bot.pnl_tracker", fromlist=["EventType"]).EventType.FLATTEN_EXECUTED,
                            details={
                                "reason": "risk_governor_breach",
                                "reasons": [r.name for r in decision.reasons],
                            },
                            account_balance=governor.current_balance,
                            unrealized_pnl=await broker.get_unrealized_pnl(),
                        )
                        log.info(f"[Cycle {cycle_count}] Flatten executed successfully")
                    except Exception as e:
                        log.error(f"[Cycle {cycle_count}] Flatten failed: {e}")
                        pnl_tracker.log_compliance_event(
                            event_type=__import__("live_bot.pnl_tracker", fromlist=["EventType"]).EventType.RISK_BREACH,
                            details={"error": f"flatten_all failed: {str(e)}"},
                            account_balance=governor.current_balance,
                        )

                    # Check for hard risk breach requiring bot shutdown
                    if any(
                        r.name in ("TRAILING_DRAWDOWN", "DAILY_LOSS_LIMIT", "BALANCE_RECONCILIATION_MISMATCH")
                        for r in decision.reasons
                    ):
                        log.error(
                            f"[Cycle {cycle_count}] Hard risk breach (%s) — stopping the bot for the session.",
                            decision.reasons,
                        )
                        # REAL GAP FOUND 2026-09-24: this was the one place a real,
                        # unattended breach shutdown happened with zero external
                        # notification -- alert_handler was constructed above but
                        # only ever wired into FlattenRoutine's own internal
                        # failure modes, never into THIS path, the one that matters
                        # most (the exact shutdown that happened, unnoticed for
                        # hours, on the practice account). Fixed here rather than left
                        # alongside AlertHandler's other stub-removal fix, since a
                        # working alert() with nothing calling it on the real
                        # breach path would have been an incomplete fix.
                        await alert_handler.alert(
                            level="CRITICAL",
                            title=f"live_bot hard risk breach: {', '.join(r.name for r in decision.reasons)}",
                            message=(
                                f"Bot stopped at cycle {cycle_count}. Reasons: "
                                f"{[r.name for r in decision.reasons]}. "
                                f"Tracked balance=${governor.current_balance:.2f}. "
                                "The bot process has exited and is NOT trading. "
                                "Check the account and restart manually if appropriate."
                            ),
                        )
                        break

                # --- 5b. Can trade? Query bars and run strategy ---
                elif combined_can_open:
                    try:
                        if isinstance(strategy, SupportResistanceBounceStrategy):
                            bars_needed = 3000
                        elif isinstance(strategy, OteFvgStrategy):
                            # See ote_fvg_strategy.py's module docstring prerequisite #1:
                            # worst case needs K_MIN(60) + up to 2x MAX_LOOKAHEAD_BARS(240)
                            # + the 15m FVG resample's own lag, ~540 minutes minimum. 500
                            # (the old default) silently missed sweeps near the window edge.
                            bars_needed = 1500
                        elif isinstance(strategy, CombinedStrategy):
                            # ADDED 2026-09-30: this strategy fell through to the 500-bar
                            # default, so it could never see the >= 11 completed sessions
                            # it needs and would never trade. Its meta-model feature
                            # range_chg also looks 21 sessions back; the live 1-min feed
                            # returns at most ~27,500 bars (~22 sessions, ~14 of them
                            # full -- checked 2026-09-30), so request all of it.
                            bars_needed = 30000
                        elif isinstance(strategy, DisciplinedBracketStrategy):
                            # Needs ~20-30 real calendar days of RTH history in view every
                            # call (20-session range average + yesterday's own profile) --
                            # pair with BOT_INITIAL_DAYS in .env (broker_client.py loads
                            # that many real days from the broker's History API at connect
                            # time; this must request at least that much back or the extra
                            # loaded history never actually reaches the strategy). ~22
                            # trading days x 390 1m bars/day = ~8,580 RTH bars; requesting
                            # more headroom since the raw window also includes non-RTH bars
                            # this strategy filters out itself.
                            # CORRECTED 2026-09-30 against the real Practice feed: the live
                            # 1-min feed includes overnight bars (~1,380/day, not 390), so
                            # 12,000 bars covered only ~9 RTH sessions -- below the strategy's
                            # RANGE_MIN_PERIODS=10, which silently disabled the POC-reversion
                            # leg (only VA-rejection could ever fire). 20,000 bars covers ~14
                            # full RTH sessions (older sessions in the feed are partial, from
                            # before the contract roll), so the range history reaches >=10.
                            bars_needed = 20000
                        else:
                            bars_needed = 500
                        bars = await broker.get_bars(bars=bars_needed, timeframe="1min")
                        signal = strategy.on_bar(bars)

                        if signal.action in (SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT):
                            log.info(
                                f"[Cycle {cycle_count}] Signal generated: {signal.action} (reason: {signal.reason})"
                            )
                            await handle_entry_signal(
                                signal,
                                broker=broker,
                                governor=governor,
                                account_config=account_config,
                                broker_config=broker_config,
                            )
                            fill_recorder.note_entry(now)
                            # Log entry to compliance ledger
                            pnl_tracker.log_compliance_event(
                                event_type=__import__("live_bot.pnl_tracker", fromlist=["EventType"]).EventType.POSITION_OPENED,
                                details={
                                    "action": signal.action.name,
                                    "reason": signal.reason,
                                    "risk_dollars": signal.risk_dollars,
                                },
                                instrument=broker_config.instrument,
                                account_balance=governor.current_balance,
                            )
                        else:
                            log.debug(f"[Cycle {cycle_count}] No signal: {signal.action}")
                    except Exception as e:
                        log.error(f"[Cycle {cycle_count}] Strategy/bar query error: {e}")
                        pnl_tracker.log_compliance_event(
                            event_type=__import__("live_bot.pnl_tracker", fromlist=["EventType"]).EventType.RISK_BREACH,
                            details={"error": f"strategy/bars failed: {str(e)}"},
                            account_balance=governor.current_balance,
                        )
                else:
                    if not can_open_per_flatten:
                        log.debug(
                            f"[Cycle {cycle_count}] Trading locked by flatten routine "
                            f"(trading_locked={flatten_routine.trading_locked_today})"
                        )
                    if not decision.can_open_new_position:
                        log.debug(f"[Cycle {cycle_count}] Risk governor says cannot open: {decision.reasons}")

            except Exception as e:
                # Catch any unhandled errors in the cycle; log and continue
                log.exception(f"[Cycle {cycle_count}] Unhandled error in polling cycle: {e}")
                pnl_tracker.log_compliance_event(
                    event_type=__import__("live_bot.pnl_tracker", fromlist=["EventType"]).EventType.RISK_BREACH,
                    details={"error": f"polling cycle crashed: {str(e)}"},
                    account_balance=governor.current_balance,
                )

            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    finally:
        # =========================================================================
        # SHUTDOWN: Finalize P&L, close positions, shutdown components
        # =========================================================================
        log.info("Beginning shutdown sequence...")

        try:
            # Stop scheduler first (prevents new flatten jobs from firing)
            scheduler.shutdown(wait=False)
            log.info("APScheduler shut down")
        except Exception as e:
            log.error(f"Error shutting down scheduler: {e}")

        try:
            # Generate daily P&L summary
            today = dt.date.today()
            daily_summary = pnl_tracker.daily_summary_report(today)
            log.info(
                f"Daily P&L Summary ({today.isoformat()}): "
                f"trades={daily_summary['total_trades_closed']} "
                f"pnl=${daily_summary['total_pnl']:.2f} "
                f"wins={daily_summary['winning_trades']} "
                f"losses={daily_summary['losing_trades']}"
            )
            pnl_tracker.log_compliance_event(
                event_type=__import__("live_bot.pnl_tracker", fromlist=["EventType"]).EventType.POSITION_FULLY_CLOSED,
                details={"daily_summary": daily_summary},
                account_balance=governor.current_balance,
            )
        except Exception as e:
            log.error(f"Error generating daily summary: {e}")

        try:
            # Flatten any remaining positions
            if broker.is_connected:
                has_open = await broker.has_open_position()
                if has_open:
                    log.warning("Open positions remain at shutdown; flattening...")
                    await broker.flatten_all()
        except Exception as e:
            log.error(f"Error flattening at shutdown: {e}")

        try:
            # Disconnect broker
            await broker.disconnect()
            log.info("Broker disconnected")
        except Exception as e:
            log.error(f"Error disconnecting broker: {e}")

        log.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(run())
