"""Thin wrapper around the `brokerapi-py` SDK for BrokerAPI order execution and data.

Design goals:
  - Never make a network call in "dry_run" mode (the default) — nothing here can
    accidentally touch a real account just by importing/instantiating it.
  - "practice" mode talks to the Practice account (selected via the
    BROKERAPI_ACCOUNT_NAME env var per brokerapi-py's convention, e.g.
    "PRACTICEJUL2415232717" per its own docstring example) — same API surface as
    the real account, zero real-money risk. Verify with a real API key.
  - "live" mode talks to whatever account BROKERAPI_ACCOUNT_NAME resolves to and
    requires an explicit extra confirmation env var, so a stray default/typo can't
    silently enable live trading.

VERIFIED against a real API key on the Practice account (2026-09-21/22) — see
README.md checklist. The method signatures below were taken directly from the
installed brokerapi_py==4.3.1 source via `inspect.signature`, not guessed, and
the end-to-end auth/order/event round-trip against BrokerAPI has been exercised
on Practice. The real (non-Practice) account has not been separately verified.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

try:
    import brokerapi_py as px
except ImportError:  # pragma: no cover - exercised only if the dependency is missing
    px = None  # type: ignore[assignment]


VALID_MODES = {"dry_run", "practice", "live"}


@dataclass
class BrokerConfig:
    mode: str = "dry_run"
    instrument: str = "MNQ"
    timeframes: list[str] = field(default_factory=lambda: ["5min"])
    # Real days of historical data brokerapi_py loads from the broker's own
    # History API at connect time (TradingSuite.create()'s own `initial_days`
    # kwarg, confirmed 2026-09-29 by reading the installed brokerapi_py==4.3.1
    # source -- NOT guessed; default there is 5, but strategies needing more
    # lookback (e.g. disciplined_bracket_strategy.py's 20-session range) can
    # request more via BOT_INITIAL_DAYS). Kept modest (5) as the default here
    # so existing strategies that never needed multi-week history don't
    # silently start pulling a much bigger data window.
    initial_days: int = 5

    @classmethod
    def from_env(cls) -> "BrokerConfig":
        return cls(
            mode=os.getenv("BOT_MODE", "dry_run").lower(),
            instrument=os.getenv("BOT_INSTRUMENT", "MNQ"),
            initial_days=int(os.getenv("BOT_INITIAL_DAYS", "5")),
        )


class BrokerClient:
    """Wraps `brokerapi_py.TradingSuite`. Construct once per instrument."""

    def __init__(self, config: BrokerConfig) -> None:
        if config.mode not in VALID_MODES:
            raise ValueError(f"Unknown BrokerClient mode {config.mode!r}, must be one of {VALID_MODES}")

        if config.mode != "dry_run" and px is None:
            raise RuntimeError("brokerapi-py is not installed; `pip install brokerapi-py` first")

        if config.mode == "live" and os.getenv("BOT_CONFIRM_LIVE") != "I_UNDERSTAND_THIS_IS_REAL_MONEY":
            raise RuntimeError(
                "Refusing to start in live mode: set the environment variable "
                "BOT_CONFIRM_LIVE=I_UNDERSTAND_THIS_IS_REAL_MONEY explicitly. "
                "This exists so a config typo can never silently enable live trading."
            )

        self.config = config
        self._suite: Any = None  # px.TradingSuite once connected
        # REAL BUG FOUND 2026-09-24, during a Practice-account test of
        # reconcile_balance() (risk_governor.py rule 10): `account_info.balance`
        # (get_account_balance()'s old sole source) is populated ONCE during
        # authenticate() (brokerapi_py/client/auth.py:285, `self.account_info =
        # selected_account`) and never reassigned anywhere else in the SDK --
        # confirmed by reading the installed brokerapi_py==4.3.1 source directly,
        # not assumed. That means every prior call to get_account_balance() for
        # the life of a bot process returned the SAME frozen number from connect
        # time, regardless of any real trading (the bot's own or anyone else's)
        # on the account since. reconcile_balance() compares the governor's
        # tracked balance against this value -- with a frozen "live" side, a
        # mismatch could never be detected, no matter what happened on the real
        # account. This is very likely why manual trading was never caught
        # before tonight, on this account or the $250K one. Real fix: subscribe
        # to the SDK's own real-time "account_update" event (GatewayUserAccount
        # via the already-connected User Hub SignalR feed -- confirmed to exist
        # in realtime/event_handling.py's `_forward_account_update`, delivering
        # balance/margin/buying-power changes) instead of the static snapshot.
        # UNVERIFIED against a live-firing event as of this fix (no manual trade
        # was placed after writing this) -- _on_account_update logs whatever
        # shape it actually receives specifically so the next Practice-mode
        # test can confirm or correct the extraction logic below.
        self._latest_live_balance: float | None = None

    @property
    def is_connected(self) -> bool:
        return self._suite is not None

    async def _on_account_update(self, event: Any) -> None:
        """Handler for the SDK's real-time "account_update" event (see the
        REAL BUG comment in __init__). Defensive extraction: log the raw shape
        received either way, since this has not yet been observed against a
        real firing and the exact payload shape was not empirically confirmed
        (brokerapi_py's AccountUpdateData TypedDict says `data: dict` with a
        `balance: float` key, but the transformation from raw SignalR args to
        this shape happens inside the SDK's private event-forwarding code,
        which was read but not executed/traced live)."""
        data = getattr(event, "data", event)
        balance = None
        if isinstance(data, dict):
            balance = data.get("balance")
        else:
            balance = getattr(data, "balance", None)
        if balance is not None:
            self._latest_live_balance = float(balance)
        # Deliberately always logged (not just on the None-extraction path):
        # this is the only way to confirm, the first time a real account_update
        # fires, whether the extraction above is actually correct.
        import logging
        logging.getLogger(__name__).info(
            "account_update event received: extracted_balance=%s raw_data=%r",
            balance, data,
        )

    async def connect(self) -> None:
        if self.config.mode == "dry_run":
            return  # intentionally makes no network calls
        assert px is not None
        self._suite = await px.TradingSuite.create(
            instrument=self.config.instrument,
            timeframes=self.config.timeframes,
            initial_days=self.config.initial_days,
        )
        # REAL BUG FOUND 2026-09-24, minutes after writing this: TradingSuite.on()
        # (the SDK's own documented "single interface for all event handling")
        # rejects "account_update" outright -- EventBus.on() (trading_suite.py's
        # `on` delegates to it) does `EventType(event)` and RAISES ValueError for
        # any string that isn't a defined EventType member; there is no
        # ACCOUNT_UPDATE member (confirmed by reading the enum's full member
        # list). This crashed connect() and the whole bot on first real
        # Practice-mode start after the fix. "account_update" is a LOWER-LEVEL
        # event, documented and only wired through the realtime client's own
        # `add_callback()` (realtime/event_handling.py), a separate mechanism
        # from TradingSuite's EventBus -- confirmed via that method's own
        # docstring listing "account_update" as a valid, expected value.
        # Callback shape also differs: add_callback hands the raw event dict
        # directly (not wrapped in an Event with a `.data` attribute) --
        # _on_account_update's `getattr(event, "data", event)` already handles
        # both shapes defensively, so no change needed there.
        await self._suite.realtime.add_callback("account_update", self._on_account_update)

    async def disconnect(self) -> None:
        if self._suite is not None:
            await self._suite.disconnect()
            self._suite = None

    def _require_connected(self) -> Any:
        if self._suite is None:
            raise RuntimeError(
                "BrokerClient is not connected (dry_run mode, or connect() was never called)"
            )
        return self._suite

    # -- market data -----------------------------------------------------

    async def get_bars(self, bars: int = 200, timeframe: str = "5min") -> Any:
        """Recent OHLCV bars for this instrument as a Polars DataFrame (columns:
        timestamp, open, high, low, close, volume), or None if not yet available.

        BUGFIX (2026-09-19): the original implementation called
        `instrument_ctx.data.get_bars(days=..., interval=...)`, which does not exist
        on `RealtimeDataManager` (verified via `dir()` against installed
        brokerapi_py==4.3.1 -- it would have raised AttributeError the first time
        this ran in practice/live mode, never having been exercised end-to-end).
        The correct method, confirmed via inspect.getdoc(), is
        `get_data(timeframe, bars)`, returning a **Polars** DataFrame, not pandas --
        any Strategy.on_bar() implementation must use Polars accessors (e.g.
        `bars["close"]`, `.tail(n)`, not pandas-style `.iloc`).
        """
        suite = self._require_connected()
        instrument_ctx = suite[self.config.instrument]
        return await instrument_ctx.data.get_data(timeframe=timeframe, bars=bars)

    # -- instrument metadata --------------------------------------------------

    def get_contract_id(self) -> str:
        """The BrokerAPI contract ID for this instrument (e.g. "CON.F.US.MNQ.Z26").

        Verified via inspect.getsource(TradingSuite) (not guessed): TradingSuite
        already resolves this at connect time (`self.instrument = await
        self.client.get_instrument(self._symbol)`) and stores it as
        `InstrumentContext.instrument_info`, an `Instrument` dataclass whose `.id`
        field is documented as "Unique contract identifier used in API calls" --
        no separate lookup call is needed here, just reading what connect()
        already fetched.
        """
        suite = self._require_connected()
        instrument_ctx = suite[self.config.instrument]
        return instrument_ctx.instrument_info.id

    # -- orders ------------------------------------------------------------

    async def place_bracket_order(
        self,
        *,
        contract_id: str,
        side: int,  # 0 = buy/long, 1 = sell/short, per BrokerAPI Order/place schema
        size: int,
        entry_price: float | None,
        stop_loss_price: float,
        take_profit_price: float,
        entry_type: str = "market",
    ) -> Any:
        suite = self._require_connected()
        instrument_ctx = suite[self.config.instrument]
        return await instrument_ctx.orders.place_bracket_order(
            contract_id=contract_id,
            side=side,
            size=size,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            entry_type=entry_type,
        )

    async def place_market_entry_with_trailing_stop(
        self,
        *,
        contract_id: str,
        side: int,  # 0 = buy/long, 1 = sell/short, same convention as place_bracket_order
        size: int,
        trail_price: float,
    ) -> tuple[Any, Any]:
        """Market entry with a trailing-stop exit and NO fixed target -- the order
        shape `strategy_interface.Signal.trail_distance_points` strategies need
        (e.g. `random_entry_atr_trail_strategy.py`), which `place_bracket_order`
        cannot express (it requires both a stop AND a target).

        Two separate SDK calls, not one atomic bracket: `place_market_order` for
        the entry, then `place_trailing_stop_order` (side flipped, so it closes
        the position the entry just opened) for the exit. If the entry fills but
        the trailing-stop placement then fails, the position is left open with
        NO protective stop -- callers must check the second response and flatten
        immediately (`flatten_all()`) if it didn't succeed; this method does not
        retry or roll back the entry itself.

        RESOLVED (2026-09-20, via SDK source, no live connection needed): `trail_price`
        is PRICE POINTS, not dollars. The docstring example ("15.0, # Trail by
        $15") is ambiguous on its own, but `order_manager/core.py`'s `place_order()`
        passes `trail_price` through `align_price_to_tick_size(trail_price,
        contract_id, self.brokerapi)` -- the identical alignment call used for
        `limit_price`/`stop_price`, which are unambiguously price-denominated. A
        dollar amount would never be tick-size-aligned. This confirms the
        implementation below was already correct; still worth a real fill to be
        certain, but no longer an open assumption.
        """
        suite = self._require_connected()
        instrument_ctx = suite[self.config.instrument]
        entry_response = await instrument_ctx.orders.place_market_order(
            contract_id=contract_id,
            side=side,
            size=size,
        )
        exit_side = 1 - side  # opposite side closes the position the entry just opened
        trail_response = await instrument_ctx.orders.place_trailing_stop_order(
            contract_id=contract_id,
            side=exit_side,
            size=size,
            trail_price=trail_price,
        )
        return entry_response, trail_response

    async def flatten_all(self) -> Any:
        """Close THIS instrument's own open position immediately (market), if any.

        Deliberately does NOT call `instrument_ctx.positions.close_all_positions()`
        -- confirmed 2026-09-22 that it closes every open position on the whole
        account, not just this instrument's (same root cause as
        `_get_own_position`'s docstring). Closing a position this bot never opened
        is a real, already-observed failure mode, not a hypothetical one -- uses
        `close_position_direct` scoped to this instrument's own contract_id
        instead. No-op (returns None) if this instrument is already flat, so it's
        safe to call defensively without checking has_open_position() first.
        """
        suite = self._require_connected()
        instrument_ctx = suite[self.config.instrument]
        position = await self._get_own_position()
        if position is None:
            return None
        return await instrument_ctx.positions.close_position_direct(self.get_contract_id())

    # -- account / P&L -------------------------------------------------------
    # Verified against installed brokerapi_py==4.3.1 source via inspect (not guessed):
    # Position (brokerapi_py.models) has NO unrealizedPnl field -- its own docstring
    # says "For P&L calculations, use PositionManager.calculate_position_pnl()", which
    # needs a current market price and a point_value (tickValue/tickSize) supplied by
    # the caller. This was double-checked after an initial grep hit (an example in
    # client/trading.py's docstring referencing `pos.unrealizedPnl`) turned out to be
    # stale/wrong against the actual Position dataclass -- do not trust that example.

    def get_account_balance(self) -> float | None:
        """Current settled account balance, or None if not yet authenticated.

        FIXED 2026-09-24 (see the REAL BUG comment in __init__): previously
        always read `client.account_info.balance`, a snapshot frozen at
        connect()/authenticate() time and never refreshed by the SDK -- making
        this call return the same stale number for the bot's entire runtime
        regardless of real account activity. Now prefers `_latest_live_balance`,
        updated by the real-time "account_update" event subscription set up in
        connect(); only falls back to the static snapshot before the first such
        event has arrived (e.g. briefly after connecting, or if no real-time
        event has fired yet in whatever venue/mode this runs against).
        UNVERIFIED against a real firing as of this fix -- see _on_account_update.

        Does NOT give the account's historical high-water-mark (BrokerAPI's Account
        model has no such field); that must still come from a verified source
        (see risk_governor's starting_high_water_mark) since it depends on this
        account's trading history, not just its current state.
        """
        suite = self._require_connected()
        if self._latest_live_balance is not None:
            return self._latest_live_balance
        account = suite.client.account_info
        return account.balance if account is not None else None

    async def _get_own_position(self) -> Any | None:
        """This instrument's own open position, or None if flat.

        CONFIRMED BROKEN (2026-09-22, real account event): the earlier assumption
        that `instrument_ctx.positions.get_all_positions()` only returns positions
        for THIS instrument's context was WRONG -- it returns every open position
        on the whole account, across every instrument. Verified directly: the trader is
        BOT_INSTRUMENT=MNQ, took zero trades that day, yet its own flatten routine
        closed a manually-placed MES position, and its unrealized-P&L polling
        picked up a manually-placed ENQ position's mark-to-market swings -- both
        instruments the trader never trades. That false signal tripped a real
        DAILY_LOSS_LIMIT + TRAILING_DRAWDOWN breach and shut the bot down entirely,
        even though it was flat the whole session. Fixed by filtering explicitly on
        contractId == get_contract_id() rather than trusting the SDK's per-instrument
        scoping -- see TRADING_JOURNAL.md's 2026-09-22 entry.
        """
        suite = self._require_connected()
        instrument_ctx = suite[self.config.instrument]
        positions = await instrument_ctx.positions.get_all_positions()
        own_contract_id = self.get_contract_id()
        for p in positions:
            if getattr(p, "contractId", None) == own_contract_id:
                return p
        return None

    async def has_open_position(self) -> bool:
        """True if there's currently an open position on THIS instrument specifically
        (not just any position anywhere on the account -- see _get_own_position)."""
        return (await self._get_own_position()) is not None

    async def get_unrealized_pnl(self) -> float:
        """Mark-to-market P&L of THIS instrument's own open position, or 0.0 if flat
        (or if some other instrument has an open position but this one doesn't --
        see _get_own_position)."""
        suite = self._require_connected()
        instrument_ctx = suite[self.config.instrument]
        position = await self._get_own_position()
        if position is None:
            return 0.0

        current_price = await instrument_ctx.data.get_current_price()
        if current_price is None:
            return 0.0

        tick_size = instrument_ctx.instrument_info.tickSize
        tick_value = instrument_ctx.instrument_info.tickValue
        point_value = (tick_value / tick_size) if tick_size else 0.0

        analysis = await instrument_ctx.positions.calculate_position_pnl(
            position, current_price=current_price, point_value=point_value
        )
        return analysis["unrealized_pnl"]

    # -- events -------------------------------------------------------------

    async def on(self, event: Any, handler: Callable[..., Awaitable[None]]) -> None:
        """Subscribe to a brokerapi_py EventType (ORDER_FILLED, POSITION_PNL_UPDATE, etc.).

        BUGFIX (2026-09-20): `TradingSuite.on()` is a coroutine function (verified
        via `inspect.iscoroutinefunction`, not guessed) -- the previous version of
        this method called `suite.on(event, handler)` without `await` and was
        itself a plain `def`, so the coroutine object was created and immediately
        discarded, never scheduled. The subscription silently never happened; any
        caller relying on this (e.g. an ORDER_FILLED handler) would appear to work
        at startup and then simply never fire. Never exercised end-to-end against a
        real connection, so this bug had no chance to surface until now.
        """
        suite = self._require_connected()
        await suite.on(event, handler)
