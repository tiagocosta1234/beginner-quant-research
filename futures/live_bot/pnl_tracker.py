"""
Realized P&L Tracker: SQLite persistence layer for position lifecycle.

Tracks positions through their state machine (OPEN → PARTIALLY_CLOSED → FULLY_CLOSED)
and records every fill as an immutable event. All P&L calculations are logged
to the compliance ledger for audit.

Schema: positions, fills, position_snapshots, compliance_ledger tables.
"""

from __future__ import annotations

import json
import sqlite3
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from pathlib import Path
from enum import Enum
from typing import Optional, Callable
from zoneinfo import ZoneInfo

CENTRAL_TZ = ZoneInfo("America/Chicago")


class PositionStatus(Enum):
    OPEN = "OPEN"
    PARTIALLY_CLOSED = "PARTIALLY_CLOSED"
    FULLY_CLOSED = "FULLY_CLOSED"


class FillType(Enum):
    ENTRY = "ENTRY"
    PARTIAL_EXIT = "PARTIAL_EXIT"
    FULL_EXIT = "FULL_EXIT"


class EventType(Enum):
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_PARTIALLY_CLOSED = "POSITION_PARTIALLY_CLOSED"
    POSITION_FULLY_CLOSED = "POSITION_FULLY_CLOSED"
    FLATTEN_EXECUTED = "FLATTEN_EXECUTED"
    RISK_BREACH = "RISK_BREACH"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


@dataclass
class Position:
    """Immutable snapshot of a position at query time."""
    id: int
    instrument: str
    entry_time: datetime
    entry_price: float
    entry_quantity: int
    entry_side: str  # 'LONG' or 'SHORT'
    status: PositionStatus
    total_quantity_exited: int
    realized_pnl: float
    average_entry_price: float
    first_exit_time: Optional[datetime] = None
    fully_closed_time: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=CENTRAL_TZ))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=CENTRAL_TZ))

    @property
    def quantity_remaining(self) -> int:
        return self.entry_quantity - self.total_quantity_exited

    @property
    def is_open(self) -> bool:
        return self.status in (PositionStatus.OPEN, PositionStatus.PARTIALLY_CLOSED)


@dataclass
class Fill:
    """Immutable record of a single fill (entry or exit)."""
    id: int
    position_id: int
    fill_type: FillType
    order_id: str
    timestamp: datetime
    quantity: int
    price: float
    side: str  # 'LONG' or 'SHORT'
    pnl_realized: Optional[float] = None  # NULL for ENTRY fills
    pnl_per_contract: Optional[float] = None
    commission: float = 0.0
    broker_response_json: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=CENTRAL_TZ))


@dataclass
class ComplianceEvent:
    """Record of a compliance-relevant event (trade, flatten, risk breach)."""
    id: int
    event_type: EventType
    event_time: datetime
    instrument: Optional[str] = None
    details_json: str = ""
    account_balance_at_event: Optional[float] = None
    unrealized_pnl_at_event: Optional[float] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=CENTRAL_TZ))


class PnlTracker:
    """
    SQLite-backed P&L tracking for position lifecycle.

    One instance per trading bot process. Wraps all database operations.
    Thread-safe: uses sqlite3's connection-per-call model (sqlite3 serializes
    internally). For high-frequency access, consider connection pooling.
    """

    def __init__(self, db_path: str = "./trading_bot.db", logger: Optional[logging.Logger] = None):
        self.db_path = Path(db_path)
        self.logger = logger or logging.getLogger("PnlTracker")
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a fresh SQLite connection (auto-closes on context exit)."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Dict-like row access
        return conn

    def _init_schema(self) -> None:
        """Create tables if they don't exist."""
        conn = self._get_conn()
        cursor = conn.cursor()

        # Positions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrument TEXT NOT NULL,
                entry_time TIMESTAMP NOT NULL,
                entry_price REAL NOT NULL,
                entry_quantity INTEGER NOT NULL,
                entry_side TEXT NOT NULL,
                status TEXT NOT NULL,
                total_quantity_exited INTEGER DEFAULT 0,
                realized_pnl REAL DEFAULT 0.0,
                average_entry_price REAL NOT NULL,
                first_exit_time TIMESTAMP,
                fully_closed_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Fills table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id INTEGER NOT NULL REFERENCES positions(id),
                fill_type TEXT NOT NULL,
                order_id TEXT NOT NULL UNIQUE,
                timestamp TIMESTAMP NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                side TEXT NOT NULL,
                pnl_realized REAL,
                pnl_per_contract REAL,
                commission REAL DEFAULT 0.0,
                broker_response_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Position snapshots (mark-to-market history)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS position_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id INTEGER NOT NULL REFERENCES positions(id),
                timestamp TIMESTAMP NOT NULL,
                current_price REAL NOT NULL,
                unrealized_pnl REAL NOT NULL,
                quantity_remaining INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Compliance ledger
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS compliance_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_time TIMESTAMP NOT NULL,
                instrument TEXT,
                details_json TEXT,
                account_balance_at_event REAL,
                unrealized_pnl_at_event REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.commit()
        conn.close()

    # --- ENTRY OPERATIONS ---

    def record_entry_fill(
        self,
        instrument: str,
        entry_price: float,
        entry_quantity: int,
        side: str,
        order_id: str,
        broker_response: dict,
    ) -> Position:
        """
        Create new Position and record entry Fill.

        Args:
            instrument: e.g. 'MNQ', 'MGC'
            entry_price: market entry price
            entry_quantity: contract count
            side: 'LONG' or 'SHORT'
            order_id: broker's order ID (for audit)
            broker_response: full API response from broker

        Returns:
            Position object (id will be set)

        Raises:
            sqlite3.Error if database error
        """
        now = datetime.now(tz=CENTRAL_TZ)
        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            # Create position
            cursor.execute(
                """
                INSERT INTO positions (
                    instrument, entry_time, entry_price, entry_quantity,
                    entry_side, status, average_entry_price
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    instrument,
                    now,
                    entry_price,
                    entry_quantity,
                    side,
                    PositionStatus.OPEN.value,
                    entry_price,
                ),
            )
            position_id = cursor.lastrowid

            # Record fill
            cursor.execute(
                """
                INSERT INTO fills (
                    position_id, fill_type, order_id, timestamp,
                    quantity, price, side, broker_response_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    position_id,
                    FillType.ENTRY.value,
                    order_id,
                    now,
                    entry_quantity,
                    entry_price,
                    side,
                    json.dumps(broker_response),
                ),
            )

            # Log compliance event
            cursor.execute(
                """
                INSERT INTO compliance_ledger (
                    event_type, event_time, instrument, details_json
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    EventType.POSITION_OPENED.value,
                    now,
                    instrument,
                    json.dumps(
                        {
                            "position_id": position_id,
                            "entry_price": entry_price,
                            "entry_quantity": entry_quantity,
                            "side": side,
                            "order_id": order_id,
                        }
                    ),
                ),
            )

            conn.commit()

            self.logger.info(
                f"Entry recorded: {instrument} {side} {entry_quantity} @ ${entry_price} (pos_id={position_id})"
            )

            # Fetch and return position
            return self.get_position(position_id)

        finally:
            conn.close()

    # --- EXIT OPERATIONS ---

    def record_partial_exit(
        self,
        position_id: int,
        exit_price: float,
        exit_quantity: int,
        order_id: str,
        broker_response: dict,
        point_value: float = 1.0,
    ) -> Fill:
        """
        Record a partial or full exit of an open position.

        Args:
            position_id: ID of position to close
            exit_price: market exit price
            exit_quantity: how many contracts to close
            order_id: broker's order ID
            broker_response: full API response
            point_value: contract multiplier (e.g. 2.0 for MNQ, 10.0 for MGC)

        Returns:
            Fill object representing this exit

        Raises:
            ValueError: if position already fully closed, or quantity exceeds remaining
            sqlite3.Error: if database error
        """
        now = datetime.now(tz=CENTRAL_TZ)
        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            # Get current position
            pos = self.get_position(position_id)

            if pos.status == PositionStatus.FULLY_CLOSED:
                raise ValueError(f"Position {position_id} already fully closed")

            remaining = pos.quantity_remaining
            if exit_quantity > remaining or exit_quantity <= 0:
                raise ValueError(
                    f"Invalid exit: trying to close {exit_quantity} but {remaining} remain"
                )

            # Calculate realized P&L
            if pos.entry_side == "LONG":
                pnl_per_contract = exit_price - pos.average_entry_price
            else:  # SHORT
                pnl_per_contract = pos.average_entry_price - exit_price

            pnl_realized = exit_quantity * pnl_per_contract * point_value

            # Record fill
            cursor.execute(
                """
                INSERT INTO fills (
                    position_id, fill_type, order_id, timestamp,
                    quantity, price, side, pnl_realized, pnl_per_contract,
                    broker_response_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    position_id,
                    FillType.FULL_EXIT.value
                    if exit_quantity == remaining
                    else FillType.PARTIAL_EXIT.value,
                    order_id,
                    now,
                    exit_quantity,
                    exit_price,
                    pos.entry_side,
                    pnl_realized,
                    pnl_per_contract,
                    json.dumps(broker_response),
                ),
            )
            fill_id = cursor.lastrowid

            # Update position
            new_total_exited = pos.total_quantity_exited + exit_quantity
            new_status = (
                PositionStatus.FULLY_CLOSED
                if new_total_exited == pos.entry_quantity
                else PositionStatus.PARTIALLY_CLOSED
            )

            cursor.execute(
                """
                UPDATE positions
                SET total_quantity_exited = ?,
                    realized_pnl = realized_pnl + ?,
                    status = ?,
                    first_exit_time = COALESCE(first_exit_time, ?),
                    fully_closed_time = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    new_total_exited,
                    pnl_realized,
                    new_status.value,
                    now if pos.first_exit_time is None else None,
                    now if new_status == PositionStatus.FULLY_CLOSED else None,
                    now,
                    position_id,
                ),
            )

            # Log compliance event
            event_type = (
                EventType.POSITION_FULLY_CLOSED
                if new_status == PositionStatus.FULLY_CLOSED
                else EventType.POSITION_PARTIALLY_CLOSED
            )

            cursor.execute(
                """
                INSERT INTO compliance_ledger (
                    event_type, event_time, instrument, details_json
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    event_type.value,
                    now,
                    pos.instrument,
                    json.dumps(
                        {
                            "position_id": position_id,
                            "exit_price": exit_price,
                            "exit_quantity": exit_quantity,
                            "pnl_realized": pnl_realized,
                            "order_id": order_id,
                        }
                    ),
                ),
            )

            conn.commit()

            self.logger.info(
                f"Exit recorded: pos_id={position_id} {exit_quantity} @ ${exit_price} = ${pnl_realized:.2f} P&L"
            )

            # Fetch and return fill
            cursor.execute("SELECT * FROM fills WHERE id = ?", (fill_id,))
            row = cursor.fetchone()
            return self._fill_from_row(row)

        finally:
            conn.close()

    # --- QUERIES ---

    def get_position(self, position_id: int) -> Optional[Position]:
        """Fetch a position by ID."""
        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM positions WHERE id = ?", (position_id,))
            row = cursor.fetchone()
            return self._position_from_row(row) if row else None
        finally:
            conn.close()

    def get_open_positions(self, instrument: Optional[str] = None) -> list[Position]:
        """Get all currently open positions (OPEN or PARTIALLY_CLOSED)."""
        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            if instrument:
                cursor.execute(
                    """
                    SELECT * FROM positions
                    WHERE status IN (?, ?)
                      AND instrument = ?
                    ORDER BY entry_time DESC
                    """,
                    (PositionStatus.OPEN.value, PositionStatus.PARTIALLY_CLOSED.value, instrument),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM positions
                    WHERE status IN (?, ?)
                    ORDER BY entry_time DESC
                    """,
                    (PositionStatus.OPEN.value, PositionStatus.PARTIALLY_CLOSED.value),
                )

            return [self._position_from_row(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def daily_summary_report(self, report_date: date) -> dict:
        """
        Generate compliance report for trades closed on a given date.

        Returns:
            {
                'date': date,
                'total_trades_closed': int,
                'total_pnl': float,
                'winning_trades': int,
                'losing_trades': int,
                'breakeven_trades': int,
                'avg_win': float,
                'avg_loss': float,
            }
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            # Trades closed on this date
            cursor.execute(
                """
                SELECT
                    COUNT(*) as count,
                    SUM(realized_pnl) as total_pnl,
                    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winners,
                    SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) as losers,
                    SUM(CASE WHEN realized_pnl = 0 THEN 1 ELSE 0 END) as breakeven,
                    AVG(CASE WHEN realized_pnl > 0 THEN realized_pnl ELSE NULL END) as avg_win,
                    AVG(CASE WHEN realized_pnl < 0 THEN realized_pnl ELSE NULL END) as avg_loss
                FROM positions
                WHERE status = ?
                  AND DATE(fully_closed_time) = ?
                """,
                (PositionStatus.FULLY_CLOSED.value, report_date.isoformat()),
            )

            row = cursor.fetchone()

            return {
                "date": report_date.isoformat(),
                "total_trades_closed": row["count"] or 0,
                "total_pnl": row["total_pnl"] or 0.0,
                "winning_trades": row["winners"] or 0,
                "losing_trades": row["losers"] or 0,
                "breakeven_trades": row["breakeven"] or 0,
                "avg_win": row["avg_win"] or 0.0,
                "avg_loss": row["avg_loss"] or 0.0,
            }
        finally:
            conn.close()

    def record_position_snapshot(
        self,
        position_id: int,
        current_price: float,
        unrealized_pnl: float,
    ) -> None:
        """Record mark-to-market snapshot of a position (for audit trail)."""
        pos = self.get_position(position_id)
        if not pos:
            return

        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO position_snapshots (
                    position_id, timestamp, current_price, unrealized_pnl,
                    quantity_remaining, status
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    position_id,
                    datetime.now(tz=CENTRAL_TZ),
                    current_price,
                    unrealized_pnl,
                    pos.quantity_remaining,
                    pos.status.value,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def log_compliance_event(
        self,
        event_type: EventType,
        details: dict,
        instrument: Optional[str] = None,
        account_balance: Optional[float] = None,
        unrealized_pnl: Optional[float] = None,
    ) -> None:
        """Log an event to the compliance ledger."""
        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO compliance_ledger (
                    event_type, event_time, instrument, details_json,
                    account_balance_at_event, unrealized_pnl_at_event
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event_type.value,
                    datetime.now(tz=CENTRAL_TZ),
                    instrument,
                    json.dumps(details),
                    account_balance,
                    unrealized_pnl,
                ),
            )
            conn.commit()

            self.logger.info(f"Compliance event logged: {event_type.value}")
        finally:
            conn.close()

    # --- HELPERS ---

    def _position_from_row(self, row: sqlite3.Row) -> Position:
        """Convert a DB row to Position object."""
        return Position(
            id=row["id"],
            instrument=row["instrument"],
            entry_time=datetime.fromisoformat(row["entry_time"]).replace(
                tzinfo=CENTRAL_TZ
            ),
            entry_price=row["entry_price"],
            entry_quantity=row["entry_quantity"],
            entry_side=row["entry_side"],
            status=PositionStatus(row["status"]),
            total_quantity_exited=row["total_quantity_exited"],
            realized_pnl=row["realized_pnl"],
            average_entry_price=row["average_entry_price"],
            first_exit_time=datetime.fromisoformat(row["first_exit_time"]).replace(
                tzinfo=CENTRAL_TZ
            )
            if row["first_exit_time"]
            else None,
            fully_closed_time=datetime.fromisoformat(row["fully_closed_time"]).replace(
                tzinfo=CENTRAL_TZ
            )
            if row["fully_closed_time"]
            else None,
            created_at=datetime.fromisoformat(row["created_at"]).replace(
                tzinfo=CENTRAL_TZ
            ),
            updated_at=datetime.fromisoformat(row["updated_at"]).replace(
                tzinfo=CENTRAL_TZ
            ),
        )

    def _fill_from_row(self, row: sqlite3.Row) -> Fill:
        """Convert a DB row to Fill object."""
        return Fill(
            id=row["id"],
            position_id=row["position_id"],
            fill_type=FillType(row["fill_type"]),
            order_id=row["order_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]).replace(
                tzinfo=CENTRAL_TZ
            ),
            quantity=row["quantity"],
            price=row["price"],
            side=row["side"],
            pnl_realized=row["pnl_realized"],
            pnl_per_contract=row["pnl_per_contract"],
            commission=row["commission"],
            broker_response_json=row["broker_response_json"],
            created_at=datetime.fromisoformat(row["created_at"]).replace(
                tzinfo=CENTRAL_TZ
            ),
        )
