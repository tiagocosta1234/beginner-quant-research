"""Broker interface the live bot talks to.

The private version of this file wrapped one broker's Python SDK (REST orders plus a
SignalR real-time feed). That adapter is not part of the public repo. To run the bot
against a real broker, subclass `BrokerClient`, implement every abstract method with the
contract described in its docstring, and return your class from `create_broker()`.

Design goals kept from the original:
  - "dry_run" (the default) never makes a network call, so importing or instantiating
    anything here cannot touch a real account.
  - "practice" is meant for a simulated/demo account with the same API surface.
  - "live" refuses to start unless BOT_CONFIRM_LIVE is set explicitly, so a config typo
    can never enable real trading.

Lessons from the original adapter, kept as contracts below because they cost real bugs:
  - The account balance must come from the broker's real-time account events, not a
    snapshot taken at login (the snapshot never refreshed).
  - Position queries must be filtered to this bot's own contract: the SDK returned every
    open position on the account, so the bot once flattened a manual trade on another
    instrument and tripped its own loss limits.
  - Subscriptions that are coroutines must be awaited, or they silently never happen.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

VALID_MODES = {"dry_run", "practice", "live"}


@dataclass
class BrokerConfig:
    mode: str = "dry_run"
    instrument: str = "MNQ"
    timeframes: list[str] = field(default_factory=lambda: ["5min"])
    # Days of history to load at connect time. Strategies that need longer lookback
    # (e.g. disciplined_bracket_strategy.py's 20-session range) raise it via BOT_INITIAL_DAYS.
    initial_days: int = 5

    @classmethod
    def from_env(cls) -> "BrokerConfig":
        return cls(
            mode=os.getenv("BOT_MODE", "dry_run").lower(),
            instrument=os.getenv("BOT_INSTRUMENT", "MNQ"),
            initial_days=int(os.getenv("BOT_INITIAL_DAYS", "5")),
            # The poll loop asks every strategy for 1min bars, so subscribe to 1min as well
            # as 5min (a 5min-only default once left every strategy with "no bars yet").
            timeframes=[t.strip() for t in os.getenv("BOT_TIMEFRAMES", "1min,5min").split(",") if t.strip()],
        )


class BrokerClient(ABC):
    """One broker connection per instrument. Subclass this for a real broker."""

    def __init__(self, config: BrokerConfig) -> None:
        if config.mode not in VALID_MODES:
            raise ValueError(f"Unknown BrokerClient mode {config.mode!r}, must be one of {VALID_MODES}")
        if config.mode == "live" and os.getenv("BOT_CONFIRM_LIVE") != "I_UNDERSTAND_THIS_IS_REAL_MONEY":
            raise RuntimeError(
                "Refusing to start in live mode: set the environment variable "
                "BOT_CONFIRM_LIVE=I_UNDERSTAND_THIS_IS_REAL_MONEY explicitly. "
                "This exists so a config typo can never silently enable live trading."
            )
        self.config = config
        # Updated from the broker's real-time account events (see _on_account_update).
        self._latest_live_balance: float | None = None

    async def _on_account_update(self, event: Any) -> None:
        """Handler for a real-time account event. Accepts an object with `.data`, a flat
        dict with "balance", or a raw dict with the balance nested under "data" (the shape
        the original broker actually sent). Always logs the raw payload."""
        data = getattr(event, "data", event)
        if isinstance(data, dict) and "balance" not in data and isinstance(data.get("data"), dict):
            data = data["data"]
        balance = data.get("balance") if isinstance(data, dict) else getattr(data, "balance", None)
        if balance is not None:
            self._latest_live_balance = float(balance)
        logging.getLogger(__name__).info(
            "account_update event received: extracted_balance=%s raw_data=%r", balance, data
        )

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """True once connect() has succeeded."""

    @abstractmethod
    async def connect(self) -> None:
        """Log in, load `config.initial_days` of history for `config.timeframes`, and
        subscribe `_on_account_update` to the broker's real-time account events."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the connection; safe to call twice."""

    @abstractmethod
    async def get_bars(self, bars: int = 200, timeframe: str = "5min") -> Any:
        """Recent OHLCV bars as a Polars DataFrame (timestamp, open, high, low, close,
        volume), or None if not available yet."""

    @abstractmethod
    def get_contract_id(self) -> str:
        """The broker's identifier for this instrument's current contract."""

    @abstractmethod
    async def place_bracket_order(
        self,
        *,
        contract_id: str,
        side: int,  # 0 = buy/long, 1 = sell/short
        size: int,
        entry_price: float | None,
        stop_loss_price: float,
        take_profit_price: float,
        entry_type: str = "market",
    ) -> Any:
        """Entry plus OCO stop and target. Returns the broker's response, which must
        expose the stop order's id so the stop can be re-anchored to the real fill."""

    @abstractmethod
    async def place_market_entry_with_trailing_stop(
        self, *, contract_id: str, side: int, size: int, trail_price: float
    ) -> tuple[Any, Any]:
        """Market entry, then a trailing stop on the opposite side (`trail_price` is in
        price points, not dollars). Returns (entry_response, trail_response). If the trail
        fails, the caller must flatten immediately; this method does not roll back."""

    @abstractmethod
    async def flatten_all(self) -> Any:
        """Close THIS instrument's own position at market (never other instruments').
        No-op returning None when flat."""

    @abstractmethod
    def get_account_balance(self) -> float | None:
        """Current balance: prefer `_latest_live_balance`, fall back to the login snapshot
        only before the first account event. None if not logged in."""

    @abstractmethod
    async def get_entry_fill_price(self, order_id: int, since: Any) -> float | None:
        """Size-weighted average fill price of one order since `since`, or None."""

    @abstractmethod
    async def modify_stop_price(self, order_id: int, stop_price: float) -> bool:
        """Move a working stop (keeping its id, so the OCO link to the target stays)."""

    @abstractmethod
    async def get_trades_since(self, since: Any) -> list[dict]:
        """This instrument's fills since `since` as dicts {pnl, fees, size, order_id};
        pnl is None on an opening fill."""

    @abstractmethod
    async def has_open_position(self) -> bool:
        """True if THIS instrument has an open position (filter by contract id)."""

    @abstractmethod
    async def get_unrealized_pnl(self) -> float:
        """Mark-to-market P&L of THIS instrument's own position, 0.0 if flat."""

    @abstractmethod
    async def on(self, event: Any, handler: Callable[..., Awaitable[None]]) -> None:
        """Subscribe `handler` to a broker event (fills, position P&L). Must be awaited."""


class DryRunBroker(BrokerClient):
    """The default: no network, no account. Data and order calls raise, history calls
    return empty results, so the bot's wiring can be exercised offline."""

    @property
    def is_connected(self) -> bool:
        return False

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    def _not_connected(self) -> RuntimeError:
        return RuntimeError("BrokerClient is not connected (dry_run mode)")

    async def get_bars(self, bars: int = 200, timeframe: str = "5min") -> Any:
        raise self._not_connected()

    def get_contract_id(self) -> str:
        raise self._not_connected()

    async def place_bracket_order(self, **kwargs: Any) -> Any:
        raise self._not_connected()

    async def place_market_entry_with_trailing_stop(self, **kwargs: Any) -> tuple[Any, Any]:
        raise self._not_connected()

    async def flatten_all(self) -> Any:
        raise self._not_connected()

    def get_account_balance(self) -> float | None:
        raise self._not_connected()

    async def get_entry_fill_price(self, order_id: int, since: Any) -> float | None:
        return None

    async def modify_stop_price(self, order_id: int, stop_price: float) -> bool:
        return False

    async def get_trades_since(self, since: Any) -> list[dict]:
        return []

    async def has_open_position(self) -> bool:
        raise self._not_connected()

    async def get_unrealized_pnl(self) -> float:
        raise self._not_connected()

    async def on(self, event: Any, handler: Callable[..., Awaitable[None]]) -> None:
        raise self._not_connected()


def create_broker(config: BrokerConfig) -> BrokerClient:
    """Return the broker implementation for `config.mode`."""
    if config.mode == "dry_run":
        return DryRunBroker(config)
    raise NotImplementedError(
        f"Mode {config.mode!r} needs a broker adapter: subclass BrokerClient for your broker "
        "and return it from create_broker()."
    )
