"""Entry point wiring risk_governor + broker_client + strategy_interface together.

Modes (set via BOT_MODE env var, default "dry_run"):
  dry_run  — no network calls at all. Just proves the pieces import and wire up
             correctly. This is the default so nothing runs live by accident.
  practice — connects to the BrokerAPI Practice account (same API surface as
             live, zero real-money risk). Requires BROKERAPI_API_KEY,
             BROKERAPI_USERNAME, BROKERAPI_ACCOUNT_NAME (practice account name)
             in the environment — see .env.example.
  live     — connects to whatever account BROKERAPI_ACCOUNT_NAME resolves to.
             Requires BOT_CONFIRM_LIVE=I_UNDERSTAND_THIS_IS_REAL_MONEY in
             addition to the credentials above. DO NOT use until: (1) a
             strategy has passed walk-forward validation, (2) this whole
             pipeline has been run against the Practice account successfully,
             (3) risk_governor's numbers (consistency %, static lock HWM) are
             confirmed against the real account. See README.md checklist.

Strategy (set via BOT_STRATEGY env var, default "noop" — deliberately, NOT
any of the three below; switching strategies is a real decision, this file
will not make it for you by defaulting into it):
  noop                        — always holds. Zero trading risk. The default.
  random_entry_atr_trail      — the MNQ edge validated in Rounds 19-26. One
             instrument, one bot process (BOT_INSTRUMENT=MNQ). Read
             `random_entry_atr_trail_strategy.py`'s module docstring first.
  support_resistance_bounce   — the MGC edge validated in Rounds 30/30b. One
             instrument, one bot process (BOT_INSTRUMENT=MGC). Read
             `support_resistance_bounce_strategy.py`'s module docstring first.
  vwap_zscore                 — the MNQ edge from Round 49 (2026-09-20/21). One
             instrument, one bot process (BOT_INSTRUMENT=MNQ). Read
             `vwap_zscore_strategy.py`'s module docstring first -- in
             particular, a real Monte Carlo search (2026-09-21) found that
             70% probability of reaching this account's profit target before
             the real Oct 30 withdrawal deadline is NOT reachable by sizing this
             edge alone at ANY risk/trade (asymptotes ~50-52%, see
             `futures/docs/TRADING_JOURNAL.md`'s 2026-09-21 entry).
  manual                         — TOD filter + VWAP-Z, combined in ONE process
             (BOT_INSTRUMENT=MNQ; not two separate processes the way the MNQ+MGC
             note below describes, since both trade MNQ and would risk a double
             position). Per-signal sizing ($2,100 TOD / $1,500 VWAP-Z, Round 69,
             2026-09-22, corrected from Round 63's $2,400/$600 after a real sizing-
             formula bug fix, not just a re-tune) is set inside `manual_strategy.py`
             itself via `Signal.risk_dollars` -- but MAX_SINGLE_TRADE_RISK MUST be
             raised to >= $2,100 (`.env`: `MAX_SINGLE_TRADE_RISK=2100`) or
             check_position_size() silently rejects every TOD signal. This sizing
             is paired with `SELF_IMPOSED_DAILY_STOP=3000` (risk_governor.py rule
             8) -- set both together, not independently. BOT_DYNAMIC_SIZING still
             should not be enabled for this strategy (would override its explicit
             per-edge risk_dollars). Read `manual_strategy.py`'s module docstring and
             `TRADING_JOURNAL.md`'s Round 69/69b entries first.
  disciplined_bracket         — POC-reversion + VA-rejection, EVAL-STAGE (Round 192,
             single leg at a time, take-profit capped at $1,650 to dodge Broker's
             consistency-rule ratchet). Read `disciplined_bracket_strategy.py`'s
             module docstring first.
  combined              — the same two legs, LIVE-STAGE counterpart
             (uncapped take-profit -- the cap above only exists for the eval-stage
             ratchet). Switching between this and disciplined_bracket above IS the
             eval-vs-live stage switch for this account; always set explicitly
             per the real dashboard, never auto-detected. Read
             `combined_strategy.py`'s module docstring first.

Running BOTH edges together (Round 31's actual finding — see below) means
running TWO separate bot processes against the same account, one per
instrument/strategy pair above; this file does not orchestrate multi-instrument
trading within a single process. As of Round 31 (2026-09-20), the deadline that
matters is the real withdrawal-request deadline (2026-10-30, not the Test's own
2026-12-10 expiration — see `futures/docs/EDGE_VALIDATION_RESULTS.md`
Round 28), and the risk-per-trade that actually gives good odds against that
short window is NOT either edge's individually-buffer-safe size: Round 31 found
MNQ $75 / MGC $200 (each edge's own safe size) gives only 0.4% probability of
reaching the profit target in the real ~20-day window, while sizing up gives
dramatically better odds. Round 34's refined sweep (finer steps than Round 31b's,
confirmed non-fluke across 10 MC seeds in Round 33): **MNQ $245 / MGC $650 —
87.8% success against 3.8% ruin**, the actual recommended sizing for this
deadline, set via `AccountConfig.max_single_trade_risk` per process (or
`RiskGovernor.check_position_size`'s ceiling — default raised to $700 on
2026-09-20 so it doesn't silently reject the $650 MGC signal). This is Monte
Carlo evidence over resampled real historical trades, not a guarantee — read
Rounds 31, 33, and 34 in full before trusting it.

Sizing (set via BOT_DYNAMIC_SIZING=1 to enable, default disabled — fixed
`AccountConfig.max_single_trade_risk` per trade): equity-scaled sizing per
`risk_governor.DynamicSizingConfig`, found in Round 26 to change the shape of
the risk/reward trade-off, not just its magnitude — also not defaulted on. Round
31's 83.4%/3.8% finding above used FIXED risk per trade, not this dynamic
sizing; combining the two hasn't been tested.

This file HAS been run end-to-end against a real API key, on the Practice
account (2026-09-21/22) — the auth/order/event round-trip is confirmed, not
just the code path up to `broker_client.connect()`. The real (non-Practice)
account has not been separately exercised; treat that as its own go-live step.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
import os
import sys
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from live_bot.broker_client import BrokerClient, BrokerConfig
from live_bot.combined_strategy import CombinedStrategy
from live_bot.disciplined_bracket_strategy import DisciplinedBracketStrategy
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

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:  # pragma: no cover - dotenv is a convenience, not a hard requirement
    pass

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

# Fallback seed values if ACCOUNT_STARTING_BALANCE/ACCOUNT_STARTING_HWM aren't set in
# the environment -- these are the real account's last known state as of 2026-09-19
# (see live_bot/tests/test_risk_governor.py), NOT the account_config fresh-start
# defaults. In practice/live mode, the live-fetched balance (via
# broker.get_account_balance()) always overrides this balance fallback once
# connected; the high-water-mark fallback is still used either way, since BrokerAPI's
# API has no field for historical HWM -- re-verify both numbers on the BrokerAPI
# dashboard before trusting them for a real run.
FALLBACK_STARTING_BALANCE = 245_815.38
FALLBACK_STARTING_HWM = 250_877.88


def _select_strategy() -> Strategy:
    name = os.getenv("BOT_STRATEGY", "noop").lower()
    if name == "noop":
        return NoOpStrategy()
    if name == "random_entry_atr_trail":
        log.warning(
            "BOT_STRATEGY=random_entry_atr_trail: this is the one validated edge in "
            "this repo's research, deployable but NOT likely to succeed on its own -- "
            "Round 26's best sizing found ~21%% probability of reaching the profit "
            "target vs. a real probability of blowing the account first. See "
            "random_entry_atr_trail_strategy.py's module docstring before proceeding."
        )
        tod_filter = os.getenv("BOT_TOD_FILTER", "0") == "1"
        if tod_filter:
            log.warning(
                "BOT_TOD_FILTER=1: entries restricted to the last third of the RTH "
                "session (Round 39). Confirmed 2026-09-20 (Round 40) this alone still "
                "gives ~0%% probability of reaching the profit target before the real "
                "deadline -- see random_entry_atr_trail_strategy.py's module docstring."
            )
        return RandomEntryAtrTrailStrategy(tod_filter=tod_filter)
    if name == "support_resistance_bounce":
        log.warning(
            "BOT_STRATEGY=support_resistance_bounce: the MGC edge validated in Rounds "
            "30/30b. See support_resistance_bounce_strategy.py's module docstring "
            "before proceeding, including the live-vs-backtest gap it documents on "
            "level detection while a position is open."
        )
        return SupportResistanceBounceStrategy()
    if name == "vwap_zscore":
        log.warning(
            "BOT_STRATEGY=vwap_zscore: the MNQ edge from Round 49. A real Monte Carlo "
            "sizing search (2026-09-21) found 70%% probability of reaching this "
            "account's profit target before the real Oct 30 deadline is NOT reachable "
            "at any risk/trade for this edge alone -- P(success) asymptotes ~50-52%%. "
            "See vwap_zscore_strategy.py's module docstring before proceeding."
        )
        return VwapZScoreStrategy()
    if name == "manual":
        log.warning(
            "BOT_STRATEGY=manual: TOD filter ($1,680/trade) + VWAP-Z ($1,200/trade) combined "
            "in one MNQ process (Round 75, 2026-09-23 -- resized down from Round 69's "
            "$2,100/$1,500 after a real DLL breach from manual trading shrank the account's "
            "buffer to $1,719.94; the old sizing's larger leg alone would now exceed the "
            "entire buffer and get rejected outright). Per-signal risk_dollars is set inside "
            "manual_strategy.py itself; MAX_SINGLE_TRADE_RISK's fixed ceiling ($2,100 in .env) "
            "is no longer the binding constraint -- the real remaining drawdown buffer is, and "
            "it is now TIGHTER than SELF_IMPOSED_DAILY_STOP=3000, so that rule won't fire "
            "before the buffer check does. This is the most aggressive sizing the real buffer "
            "can support, not a conservative choice: TOD at $1,680 is 97.7%% of the entire "
            "buffer, so a single losing TOD trade leaves ~$40 of margin. Chosen deliberately, "
            "after being shown the real trade-off (Round 75, futures/engine/"
            "round75_250k_post_breach_resweep.py): P(success)=19.1%%, P(ruin)=62.8%% against "
            "the real $22,402.18 target gap and 27 trading days to the 2026-10-30 deadline -- "
            "success RISES with sizing here because conservative sizing can't close that gap "
            "in time at all (P(success)=0.0%% at 1x baseline). "
            "See manual_strategy.py's module docstring and TRADING_JOURNAL.md Round 75 "
            "before proceeding."
        )
        return ManualStrategy()
    if name == "ote_fvg":
        log.warning(
            "BOT_STRATEGY=ote_fvg: OTE (61.8-79%% retracement) + 15m FVG sweep-reclaim, "
            "NY RTH-only entries (Round 76, resized in Round 87 -- stop=10pts/RR=1:4, was "
            "1:2 -- specifically so a single trade's own win stays under the real $1,650/day "
            "consistency-derived cap). Best real eval-stage candidate found this campaign, "
            "TRUE walk-forward validated (parameters chosen using only data prior to each "
            "test fold, not hindsight): $50K Test P(success)=77.2%%, P(ruin)=22.8%%, "
            "median=4.0 days, real BrokerAPI/BrokerAPI MNQ data, real one-position-at-a-time + "
            "$1,000 day-cap + $1,650 preemptive daily-profit-cap gating, real 55%% "
            "consistency check. Verified exhaustively: zero of 31 real walk-forward days "
            "exceed $1,650 (see round87's docstring). Wired in 2026-09-24 as the shadow-test "
            "step of the deployment roadmap -- confirm BOT_MODE=practice before running; "
            "this has NOT been validated for a live/real-money account. See "
            "ote_fvg_strategy.py's module docstring for the full prerequisite checklist."
        )
        return OteFvgStrategy()
    if name == "disciplined_bracket":
        log.warning(
            "BOT_STRATEGY=disciplined_bracket: Round 192's POC-reversion + VA-rejection "
            "disciplined bracket (the trader's chosen strategy for evaluations, 2026-09-29 "
            "split-strategy Monte Carlo -- real eval-stage pass rate 27.9%% vs the "
            "live-stage combined signal's 2.5%%, 15-day window, 50K tier). WIRED UP AS "
            "A SCOPED-DOWN ADAPTATION, not a 1:1 port of Round 192: single leg at a time "
            "(has_open_position()'s one-position gate was not weakened to allow Round "
            "192's two CONCURRENT legs) and the $1,650 win cap is enforced by clipping "
            "the take-profit price at entry, not mark-to-market monitoring (main.py has "
            "no EXIT-signal handling to flatten an open position mid-day). Both "
            "adaptations make this WEAKER than Round 192's real 27.9%% backtested "
            "number -- read disciplined_bracket_strategy.py's module docstring in full "
            "before trusting a forward-test run to reproduce it. Entry/exit price-level "
            "logic verified 2026-09-29 against the original backtest functions "
            "(round178_volume_profile_poc.py, round184_value_area_breakout.py) across "
            "60 real historical NQ sessions, 0 mismatches -- but the FIRST live session "
            "produces no entry by design (no seeded 'yesterday' profile, only a seeded "
            "20-session range). Confirm BOT_MODE=practice before running; this has NOT "
            "been validated for a live/real-money account."
        )
        return DisciplinedBracketStrategy()
    if name == "combined":
        log.warning(
            "BOT_STRATEGY=combined: live-stage counterpart to disciplined_bracket -- "
            "same two legs (meta-labeled POC-reversion + unfiltered VA-rejection), single leg "
            "at a time, but UNCAPPED take-profit (the $1,650 win cap exists only to dodge "
            "Broker's eval-stage consistency-rule ratchet; once live there's no ratchet to "
            "dodge, so this strategy is deliberately stronger, not just a copy). Switching "
            "BOT_STRATEGY between disciplined_bracket and combined IS the eval-vs-live "
            "stage switch for this account -- always set explicitly, never auto-detected off "
            "the dashboard; a mismatch (live stage still running the capped strategy, or "
            "vice versa) is a real, silent cost, not a crash, so check the dashboard's stage "
            "yourself before switching. The meta-labeling model (poc_meta_model.json) is "
            "pre-trained and serialized, not trained live, with its confidence threshold fit "
            "on the training set's own distribution (not the OOS test set's, which would be a "
            "real look-ahead problem for live use). Parity-verified 2026-09-29 against "
            "round198_meta_labeling_poc.py's own reference feature values and predictions "
            "across 8 real dates spanning six months, after catching and fixing two real bugs "
            "in this file's own reconstruction: a P&L sign bug in _resolve_day_outcome (short "
            "trades' stop/target branches weren't multiplied by direction, inverting every "
            "short outcome) and a range_chg formula bug (was comparing two 20-day rolling "
            "averages; the trained model expects a single day's range vs. the range exactly "
            "20 sessions earlier, ranges.pct_change(20).shift(1)). See combined_strategy.py's "
            "module docstring and TRADING_JOURNAL.md's 2026-09-29 entry for the full account. "
            "Confirm BOT_MODE=practice before running; this has NOT been validated for a "
            "live/real-money account."
        )
        return CombinedStrategy()
    raise ValueError(
        f"Unknown BOT_STRATEGY={name!r}, must be one of: noop, random_entry_atr_trail, "
        "support_resistance_bounce, vwap_zscore, manual, ote_fvg, disciplined_bracket, "
        "combined"
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
        await broker.place_bracket_order(
            contract_id=contract_id,
            side=side,
            size=signal.size,
            entry_price=None,  # market entry
            stop_loss_price=signal.stop_loss_price,
            take_profit_price=signal.take_profit_price,
        )
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
            "account's real $4,937.50 buffer.",
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
            "before any order is placed -- see TRADING_JOURNAL.md Round 69.",
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
    # AccountConfig's own defaults (trailing_dd_amount=$10,000, daily_loss_limit=$5,000)
    # are the $250K account's real numbers -- REAL GAP FOUND 2026-09-29 while connecting
    # a different (150K-tier) Practice account for the first time: neither had an env
    # override, so running against any other tier would silently use the WRONG failure
    # floor. Confirmed dangerous, not theoretical: this exact $150K account's real MLL
    # is $4,500 (reinvestment_snowball.FIRMS["broker_150k"]), giving a real floor of
    # HWM-$4,500 -- $5,500 TIGHTER than the $250K default's HWM-$10,000 floor would have
    # silently allowed. Added the same deliberate-opt-in env override pattern as every
    # other AccountConfig field above; get this right for whatever account is actually
    # connected before trusting the risk governor's numbers, same warning as every other
    # override here.
    _trailing_dd_env = os.getenv("TRAILING_DD_AMOUNT")
    if _trailing_dd_env:
        account_config_kwargs["trailing_dd_amount"] = float(_trailing_dd_env)
        log.warning(
            "TRAILING_DD_AMOUNT=$%.0f active (default $10,000, the $250K account's "
            "real number) -- confirm this matches whatever account is actually "
            "connected before trusting remaining_drawdown_buffer().",
            float(_trailing_dd_env),
        )
    _daily_loss_limit_env = os.getenv("DAILY_LOSS_LIMIT")
    if _daily_loss_limit_env:
        account_config_kwargs["daily_loss_limit"] = float(_daily_loss_limit_env)
        log.warning(
            "DAILY_LOSS_LIMIT=$%.0f active (default $5,000, the $250K account's "
            "real number) -- confirm this matches whatever account is actually "
            "connected before trusting daily_loss_breached().",
            float(_daily_loss_limit_env),
        )
    account_config = AccountConfig(**account_config_kwargs)  # NOTE: consistency_cap_pct
    # and static_lock_hwm are UNCONFIRMED defaults — see risk_governor.py docstring.
    # profit_target_balance falls back to the $250K account's own default
    # ($265,000) unless PROFIT_TARGET_BALANCE is set in .env -- get this right
    # for whatever account is actually configured, or the consistency-rule
    # check (rule 3) silently uses the wrong target for it.
    # Do not go live without verifying these against the real account.

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
    broker = BrokerClient(broker_config)
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
    governor.start_new_trading_day(dt.date.today())

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

                # --- 2b. Reconcile tracked balance against the broker's live settled
                # balance (risk_governor.py rule 10). No network call -- reads the
                # same cached account_info get_account_balance() already uses at
                # startup. Catches untracked account activity (e.g. a manual trade)
                # before it can silently invalidate every other check below.
                live_balance = broker.get_account_balance()
                if live_balance is not None and not governor.reconcile_balance(live_balance):
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
                        # hours, on the $250K account). Fixed here rather than left
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
                            bars_needed = 12000
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
