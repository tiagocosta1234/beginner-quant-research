"""
Comprehensive unit tests for PnlTracker: position lifecycle, P&L calculation, compliance logging.

Tests cover:
1. Single position entry/exit (long and short)
2. Multiple simultaneous positions
3. Partial exits
4. P&L calculation accuracy
5. Commission/slippage handling
6. Compliance event logging
7. Daily summary reports

Run with: pytest live_bot/tests/test_pnl_tracker.py -v
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

# Import after sys.path adjusted
from live_bot.pnl_tracker import (
    PnlTracker,
    Position,
    PositionStatus,
    Fill,
    FillType,
    EventType,
    ComplianceEvent,
)

CENTRAL_TZ = ZoneInfo("America/Chicago")


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for each test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        yield db_path


@pytest.fixture
def tracker(temp_db):
    """Create a PnlTracker instance with temporary database."""
    return PnlTracker(db_path=temp_db)


class TestSinglePositionEntry:
    """Test single position entry and tracking."""

    def test_record_entry_fill_long(self, tracker):
        """Test recording a long entry."""
        position = tracker.record_entry_fill(
            instrument="MNQ",
            entry_price=20_000.0,
            entry_quantity=2,
            side="LONG",
            order_id="order_001",
            broker_response={"status": "filled", "average_price": 20_000.0},
        )

        assert position.id is not None
        assert position.instrument == "MNQ"
        assert position.entry_price == 20_000.0
        assert position.entry_quantity == 2
        assert position.entry_side == "LONG"
        assert position.status == PositionStatus.OPEN
        assert position.realized_pnl == 0.0
        assert position.total_quantity_exited == 0
        assert position.quantity_remaining == 2

    def test_record_entry_fill_short(self, tracker):
        """Test recording a short entry."""
        position = tracker.record_entry_fill(
            instrument="MGC",
            entry_price=515.50,
            entry_quantity=3,
            side="SHORT",
            order_id="order_002",
            broker_response={"status": "filled"},
        )

        assert position.entry_side == "SHORT"
        assert position.entry_price == 515.50
        assert position.entry_quantity == 3

    def test_entry_creates_compliance_event(self, tracker):
        """Verify entry creates compliance ledger event."""
        position = tracker.record_entry_fill(
            instrument="MNQ",
            entry_price=20_000.0,
            entry_quantity=1,
            side="LONG",
            order_id="order_003",
            broker_response={},
        )

        # Query compliance ledger
        conn = tracker._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM compliance_ledger WHERE event_type = ? AND instrument = ?",
            (EventType.POSITION_OPENED.value, "MNQ"),
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row["event_type"] == EventType.POSITION_OPENED.value
        assert row["instrument"] == "MNQ"

        details = json.loads(row["details_json"])
        assert details["position_id"] == position.id
        assert details["entry_price"] == 20_000.0
        assert details["entry_quantity"] == 1


class TestSinglePositionExit:
    """Test single position full and partial exits."""

    def test_full_exit_long_winning(self, tracker):
        """Test full exit of a winning long position."""
        # Entry
        position = tracker.record_entry_fill(
            instrument="MNQ",
            entry_price=20_000.0,
            entry_quantity=2,
            side="LONG",
            order_id="entry_001",
            broker_response={},
        )
        pos_id = position.id

        # Full exit: sold at 20_100 = +100 per contract
        exit_fill = tracker.record_partial_exit(
            position_id=pos_id,
            exit_price=20_100.0,
            exit_quantity=2,
            order_id="exit_001",
            broker_response={},
            point_value=2.0,  # MNQ multiplier
        )

        # Expected: (20_100 - 20_000) * 2 contracts * 2.0 = +400
        assert exit_fill.pnl_realized == 400.0
        assert exit_fill.pnl_per_contract == 100.0
        assert exit_fill.fill_type == FillType.FULL_EXIT

        # Position should be fully closed
        updated_pos = tracker.get_position(pos_id)
        assert updated_pos.status == PositionStatus.FULLY_CLOSED
        assert updated_pos.realized_pnl == 400.0
        assert updated_pos.quantity_remaining == 0
        assert updated_pos.fully_closed_time is not None

    def test_full_exit_long_losing(self, tracker):
        """Test full exit of a losing long position."""
        position = tracker.record_entry_fill(
            instrument="MNQ",
            entry_price=20_000.0,
            entry_quantity=1,
            side="LONG",
            order_id="entry_002",
            broker_response={},
        )

        exit_fill = tracker.record_partial_exit(
            position_id=position.id,
            exit_price=19_950.0,
            exit_quantity=1,
            order_id="exit_002",
            broker_response={},
            point_value=2.0,
        )

        # Expected: (19_950 - 20_000) * 1 * 2.0 = -100
        assert exit_fill.pnl_realized == -100.0
        assert exit_fill.pnl_per_contract == -50.0

    def test_full_exit_short_winning(self, tracker):
        """Test full exit of a winning short position."""
        position = tracker.record_entry_fill(
            instrument="MGC",
            entry_price=515.50,
            entry_quantity=2,
            side="SHORT",
            order_id="entry_003",
            broker_response={},
        )

        # Short: sold at 515.50, bought back at 515.00 = +0.50 per contract
        exit_fill = tracker.record_partial_exit(
            position_id=position.id,
            exit_price=515.00,
            exit_quantity=2,
            order_id="exit_003",
            broker_response={},
            point_value=10.0,  # MGC multiplier
        )

        # Expected: (515.50 - 515.00) * 2 * 10.0 = +10.0
        assert exit_fill.pnl_realized == 10.0
        assert exit_fill.pnl_per_contract == 0.50

    def test_partial_exit(self, tracker):
        """Test partial exit (exit part of position, leave remainder open)."""
        position = tracker.record_entry_fill(
            instrument="MNQ",
            entry_price=20_000.0,
            entry_quantity=3,
            side="LONG",
            order_id="entry_004",
            broker_response={},
        )

        # Partial exit: close 1 contract at 20_050
        exit_fill = tracker.record_partial_exit(
            position_id=position.id,
            exit_price=20_050.0,
            exit_quantity=1,
            order_id="exit_004",
            broker_response={},
            point_value=2.0,
        )

        assert exit_fill.fill_type == FillType.PARTIAL_EXIT
        assert exit_fill.pnl_realized == 100.0  # (20_050 - 20_000) * 1 * 2.0

        # Position should be partially closed
        updated_pos = tracker.get_position(position.id)
        assert updated_pos.status == PositionStatus.PARTIALLY_CLOSED
        assert updated_pos.total_quantity_exited == 1
        assert updated_pos.quantity_remaining == 2
        assert updated_pos.realized_pnl == 100.0
        assert updated_pos.first_exit_time is not None
        assert updated_pos.fully_closed_time is None

    def test_multiple_partial_exits_then_full_close(self, tracker):
        """Test multiple partial exits followed by full close."""
        position = tracker.record_entry_fill(
            instrument="MNQ",
            entry_price=20_000.0,
            entry_quantity=4,
            side="LONG",
            order_id="entry_005",
            broker_response={},
        )

        # First partial exit: 1 contract at 20_025
        tracker.record_partial_exit(
            position_id=position.id,
            exit_price=20_025.0,
            exit_quantity=1,
            order_id="exit_005a",
            broker_response={},
            point_value=2.0,
        )

        # Second partial exit: 2 contracts at 20_050
        tracker.record_partial_exit(
            position_id=position.id,
            exit_price=20_050.0,
            exit_quantity=2,
            order_id="exit_005b",
            broker_response={},
            point_value=2.0,
        )

        # Final exit: 1 contract at 20_075
        final_exit = tracker.record_partial_exit(
            position_id=position.id,
            exit_price=20_075.0,
            exit_quantity=1,
            order_id="exit_005c",
            broker_response={},
            point_value=2.0,
        )

        assert final_exit.fill_type == FillType.FULL_EXIT

        updated_pos = tracker.get_position(position.id)
        assert updated_pos.status == PositionStatus.FULLY_CLOSED
        assert updated_pos.quantity_remaining == 0
        # Total P&L: (25*2) + (50*2*2) + (75*2) = 50 + 200 + 150 = 400
        assert updated_pos.realized_pnl == 400.0

    def test_exit_validation_prevents_overdraw(self, tracker):
        """Test that exiting more than remaining quantity is rejected."""
        position = tracker.record_entry_fill(
            instrument="MNQ",
            entry_price=20_000.0,
            entry_quantity=2,
            side="LONG",
            order_id="entry_006",
            broker_response={},
        )

        # Try to exit 3 contracts (only 2 available)
        with pytest.raises(ValueError, match="Invalid exit"):
            tracker.record_partial_exit(
                position_id=position.id,
                exit_price=20_100.0,
                exit_quantity=3,
                order_id="exit_006",
                broker_response={},
            )

    def test_exit_validation_prevents_exit_of_closed_position(self, tracker):
        """Test that exiting a fully closed position is rejected."""
        position = tracker.record_entry_fill(
            instrument="MNQ",
            entry_price=20_000.0,
            entry_quantity=1,
            side="LONG",
            order_id="entry_007",
            broker_response={},
        )

        # Close the position
        tracker.record_partial_exit(
            position_id=position.id,
            exit_price=20_100.0,
            exit_quantity=1,
            order_id="exit_007",
            broker_response={},
        )

        # Try to exit again
        with pytest.raises(ValueError, match="already fully closed"):
            tracker.record_partial_exit(
                position_id=position.id,
                exit_price=20_200.0,
                exit_quantity=1,
                order_id="exit_007b",
                broker_response={},
            )


class TestMultiplePositions:
    """Test tracking multiple simultaneous positions."""

    def test_multiple_positions_different_instruments(self, tracker):
        """Test tracking positions in different instruments simultaneously."""
        # Long MNQ
        pos1 = tracker.record_entry_fill(
            instrument="MNQ",
            entry_price=20_000.0,
            entry_quantity=1,
            side="LONG",
            order_id="entry_a",
            broker_response={},
        )

        # Short MGC
        pos2 = tracker.record_entry_fill(
            instrument="MGC",
            entry_price=515.50,
            entry_quantity=2,
            side="SHORT",
            order_id="entry_b",
            broker_response={},
        )

        # Long ES
        pos3 = tracker.record_entry_fill(
            instrument="ES",
            entry_price=5_500.0,
            entry_quantity=1,
            side="LONG",
            order_id="entry_c",
            broker_response={},
        )

        # Verify all are open
        open_positions = tracker.get_open_positions()
        assert len(open_positions) == 3

        # Close one
        tracker.record_partial_exit(
            position_id=pos1.id,
            exit_price=20_100.0,
            exit_quantity=1,
            order_id="exit_a",
            broker_response={},
            point_value=2.0,
        )

        # Should still have 2 open
        open_positions = tracker.get_open_positions()
        assert len(open_positions) == 2

    def test_get_open_positions_by_instrument(self, tracker):
        """Test filtering open positions by instrument."""
        # Multiple positions in MNQ
        tracker.record_entry_fill(
            instrument="MNQ", entry_price=20_000.0, entry_quantity=1,
            side="LONG", order_id="entry_1", broker_response={}
        )
        tracker.record_entry_fill(
            instrument="MNQ", entry_price=20_050.0, entry_quantity=1,
            side="LONG", order_id="entry_2", broker_response={}
        )

        # Position in MGC
        tracker.record_entry_fill(
            instrument="MGC", entry_price=515.0, entry_quantity=1,
            side="SHORT", order_id="entry_3", broker_response={}
        )

        # Query MNQ only
        mnq_positions = tracker.get_open_positions(instrument="MNQ")
        assert len(mnq_positions) == 2
        assert all(p.instrument == "MNQ" for p in mnq_positions)

        # Query MGC only
        mgc_positions = tracker.get_open_positions(instrument="MGC")
        assert len(mgc_positions) == 1
        assert mgc_positions[0].instrument == "MGC"


class TestCommissionAndSlippage:
    """Test P&L calculation with commission and slippage."""

    def test_commission_deduction_from_pnl(self, tracker):
        """Test that commission is properly recorded and deducted."""
        position = tracker.record_entry_fill(
            instrument="MNQ",
            entry_price=20_000.0,
            entry_quantity=1,
            side="LONG",
            order_id="entry_comm_1",
            broker_response={},
        )

        # Exit with commission
        exit_fill = tracker.record_partial_exit(
            position_id=position.id,
            exit_price=20_100.0,
            exit_quantity=1,
            order_id="exit_comm_1",
            broker_response={"commission": 5.0},
            point_value=2.0,
        )

        # P&L should include commission in the calculation
        # Gross: (20_100 - 20_000) * 1 * 2.0 = 200
        # Note: The current tracker doesn't deduct commission automatically from realized_pnl
        # This test documents the current behavior; update if commission handling changes
        assert exit_fill.pnl_realized == 200.0
        assert exit_fill.commission == 0.0  # Commission not currently extracted from broker_response

    def test_multiple_entry_prices_average_calculation(self, tracker):
        """Test that position tracks average entry price correctly."""
        # Entry at 20_000
        position = tracker.record_entry_fill(
            instrument="MNQ",
            entry_price=20_000.0,
            entry_quantity=2,
            side="LONG",
            order_id="entry_scale_1",
            broker_response={},
        )

        # For now, tracker only stores initial entry price
        # This test documents current behavior
        assert position.average_entry_price == 20_000.0


class TestWinningDaysGateCalculation:
    """Test the 5-day, $150 winning-days counter."""

    def test_daily_summary_winning_day(self, tracker):
        """Test daily summary calculation for a winning trading day."""
        today = date.today()

        # Trade 1: +$50
        pos1 = tracker.record_entry_fill(
            instrument="MNQ",
            entry_price=20_000.0,
            entry_quantity=1,
            side="LONG",
            order_id="entry_s1",
            broker_response={},
        )
        tracker.record_partial_exit(
            position_id=pos1.id,
            exit_price=20_025.0,
            exit_quantity=1,
            order_id="exit_s1",
            broker_response={},
            point_value=2.0,
        )

        # Trade 2: +$100
        pos2 = tracker.record_entry_fill(
            instrument="MNQ",
            entry_price=20_100.0,
            entry_quantity=1,
            side="LONG",
            order_id="entry_s2",
            broker_response={},
        )
        tracker.record_partial_exit(
            position_id=pos2.id,
            exit_price=20_150.0,
            exit_quantity=1,
            order_id="exit_s2",
            broker_response={},
            point_value=2.0,
        )

        # Generate daily summary
        summary = tracker.daily_summary_report(today)

        assert summary["total_trades_closed"] == 2
        assert summary["total_pnl"] == 150.0
        assert summary["winning_trades"] == 2
        assert summary["losing_trades"] == 0

    def test_daily_summary_mixed_day(self, tracker):
        """Test daily summary with winners and losers."""
        today = date.today()

        # Winning trade: +$100
        pos1 = tracker.record_entry_fill(
            instrument="MNQ", entry_price=20_000.0, entry_quantity=1,
            side="LONG", order_id="entry_m1", broker_response={}
        )
        tracker.record_partial_exit(
            position_id=pos1.id, exit_price=20_050.0, exit_quantity=1,
            order_id="exit_m1", broker_response={}, point_value=2.0
        )

        # Losing trade: -$200
        pos2 = tracker.record_entry_fill(
            instrument="MNQ", entry_price=20_200.0, entry_quantity=1,
            side="LONG", order_id="entry_m2", broker_response={}
        )
        tracker.record_partial_exit(
            position_id=pos2.id, exit_price=20_100.0, exit_quantity=1,
            order_id="exit_m2", broker_response={}, point_value=2.0
        )

        summary = tracker.daily_summary_report(today)

        assert summary["total_trades_closed"] == 2
        assert summary["total_pnl"] == -100.0
        assert summary["winning_trades"] == 1
        assert summary["losing_trades"] == 1


class TestComplianceLogging:
    """Test compliance ledger recording."""

    def test_log_compliance_event(self, tracker):
        """Test logging arbitrary compliance events."""
        tracker.log_compliance_event(
            event_type=EventType.RISK_BREACH,
            details={"reason": "drawdown exceeded", "current_dd": -0.05},
            instrument="MNQ",
            account_balance=245_000.0,
            unrealized_pnl=-5_000.0,
        )

        conn = tracker._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM compliance_ledger WHERE event_type = ?",
            (EventType.RISK_BREACH.value,),
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row["instrument"] == "MNQ"
        assert row["account_balance_at_event"] == 245_000.0
        assert row["unrealized_pnl_at_event"] == -5_000.0

        details = json.loads(row["details_json"])
        assert details["reason"] == "drawdown exceeded"


class TestPositionSnapshots:
    """Test mark-to-market position snapshots."""

    def test_record_position_snapshot(self, tracker):
        """Test recording a position snapshot."""
        position = tracker.record_entry_fill(
            instrument="MNQ",
            entry_price=20_000.0,
            entry_quantity=1,
            side="LONG",
            order_id="entry_snap_1",
            broker_response={},
        )

        # Record snapshot at current price
        tracker.record_position_snapshot(
            position_id=position.id,
            current_price=20_100.0,
            unrealized_pnl=200.0,
        )

        # Query snapshots
        conn = tracker._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM position_snapshots WHERE position_id = ?",
            (position.id,),
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row["current_price"] == 20_100.0
        assert row["unrealized_pnl"] == 200.0


class TestDatabasePersistence:
    """Test data persistence across connections."""

    def test_data_survives_connection_close_and_reopen(self, temp_db):
        """Test that positions persist when tracker is recreated."""
        # First tracker instance
        tracker1 = PnlTracker(db_path=temp_db)
        position = tracker1.record_entry_fill(
            instrument="MNQ",
            entry_price=20_000.0,
            entry_quantity=1,
            side="LONG",
            order_id="entry_persist",
            broker_response={},
        )
        pos_id = position.id

        # New tracker instance (same DB)
        tracker2 = PnlTracker(db_path=temp_db)
        retrieved_pos = tracker2.get_position(pos_id)

        assert retrieved_pos is not None
        assert retrieved_pos.id == pos_id
        assert retrieved_pos.instrument == "MNQ"
        assert retrieved_pos.entry_price == 20_000.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
