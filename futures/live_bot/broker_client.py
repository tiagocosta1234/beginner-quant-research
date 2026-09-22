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

NOT YET VERIFIED against a real API key — see README.md checklist. The method
signatures below were taken directly from the installed brokerapi_py==4.3.1
source via `inspect.signature`, not guessed, but the end-to-end auth/order/event
round-trip against BrokerAPI has not been exercised.
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

    @classmethod
    def from_env(cls) -> "BrokerConfig":
        return cls(
            mode=os.getenv("BOT_MODE", "dry_run").lower(),
            instrument=os.getenv("BOT_INSTRUMENT", "MNQ"),
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

    @property
    def is_connected(self) -> bool:
        return self._suite is not None

    async def connect(self) -> None:
        if self.config.mode == "dry_run":
            return  # intentionally makes no network calls
        assert px is not None
        self._suite = await px.TradingSuite.create(
            instrument=self.config.instrument,
            timeframes=self.config.timeframes,
        )

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

        `client.account_info` is populated during connect()/authenticate() (see
        brokerapi_py/client/auth.py) -- this makes no separate network call.
        Does NOT give the account's historical high-water-mark (BrokerAPI's Account
        model has no such field); that must still come from a verified source
        (see risk_governor's starting_high_water_mark) since it depends on this
        account's trading history, not just its current state.
        """
        suite = self._require_connected()
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
