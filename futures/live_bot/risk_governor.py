"""Strategy-agnostic risk governance for the BrokerAPI $250k Freedom Test account.

This module enforces Broker's account-survival rules independently of whatever
strategy is plugged in via strategy_interface.py, and independently of the broker
connection in broker_client.py. It has NO network dependency, so it can be (and is,
see tests/test_risk_governor.py) fully unit tested with synthetic P&L sequences.

Rules enforced:
  1. Daily Loss Limit (DLL) — hard real-time lockout once today's realized loss
     reaches the configured limit.
  2. EOD trailing drawdown floor — the account fails if balance ever falls to or
     below high_water_mark - trailing_dd_amount, where high_water_mark is the
     highest EOD-settled balance ever reached. Broker's real accounts typically
     also have a "static lock" level: once the HWM crosses some threshold, the
     floor stops trailing further. That threshold (static_lock_hwm below) is
     UNCONFIRMED for this specific $250k Freedom Test product — verify on the
     BrokerAPI dashboard before relying on it. Until confirmed, static_lock_hwm
     defaults to None, meaning the floor trails forever (the more conservative
     assumption — it will never overstate the remaining buffer).

     SEPARATE from static_lock_hwm: confirmed 2026-09-20 via Broker's own withdrawal
     policy article (Knowledge_Base/BROKER_LIVE_WITHDRAWAL_RULES.md) that the first
     withdrawal ever requested on this account sets the Maximum Loss Limit to $0
     PERMANENTLY -- it does not re-anchor to (new balance - trailing_dd_amount)
     the way this module's trailing_floor() computes it pre-withdrawal. After that
     first withdrawal, none of this governor's trailing-floor math still describes
     the account's real MLL; the entire remaining balance becomes the loss floor,
     and staying safe becomes a deliberate choice about how much to request, not
     something this code enforces. Not yet wired into AccountConfig/RiskGovernor
     since the exact post-eval numbers (real withdrawal cap for this $250k tier,
     minimum request amount) are still unconfirmed -- see that file before this
     account's first withdrawal.
  3. Consistency limit — caps how much of total accumulated profit any single day
     may represent. Implemented as: for a given day, once that day's own profit
     would exceed consistency_cap_pct of the account's total net profit
     (prior days' profit + today's profit), no further profit-taking should be
     booked today. This governor only flags/limits new profit; it does not (and
     should not) try to force a loss to "fix" an already-booked overage.
  4. Session flatten — every open position must be closed before
     session_flatten_time (default 3:10 PM CT, per Broker's live/eval rules).
  5. Per-trade position-size cap — check_position_size() rejects any proposed
     trade whose risk exceeds max_single_trade_risk, or exceeds whatever
     drawdown buffer is actually left (whichever is smaller). Added after
     reviewing this account's historical discretionary trading record (Notion
     "Live Trading Journal", 93 trades, Jan-Jun 2026): position-size variance,
     not signal quality, was the dominant cause of realized damage there — at
     least 9 separate live/eval accounts were blown, and the trader's own
     in-the-moment notes repeatedly cite oversized or "accidental" risk as the
     proximate cause ("Had to risk like 200$ or else this eval is gonna go to
     shit"; "risked 2%, i thought too much on accident"). A hard, code-enforced
     ceiling on risk-per-trade — not just on cumulative daily/trailing loss —
     directly targets that specific, evidenced failure mode.
  6. Consecutive-loss lockout — new entries are blocked after
     consecutive_loss_limit realized losing fills in a row within a single day
     (a breakeven fill neither extends nor resets the streak). This automates a
     discipline the same discretionary journal shows was sometimes self-imposed
     ("2 BE's, unlucky tho... done for the day" after a losing pair) and
     sometimes not (leading directly into several of the blown-account entries)
     — making it a hard rule rather than a willpower decision in the moment.
  8. Self-imposed daily stop (opt-in, disabled by default) — check_position_size()
     rejects a proposed trade if today's realized+floating P&L, minus that trade's
     own proposed risk, would already be at or past -self_imposed_daily_stop. This
     is DELIBERATELY TIGHTER than the real Broker daily_loss_limit (rule 1) and is
     the account holder's own choice, not a Broker rule — added 2026-09-22 after
     `futures/docs/TRADING_JOURNAL.md` Round 69 found that a same-day
     circuit breaker can only ever act BETWEEN trades: it cannot shrink the trade
     that crosses the threshold, so a real guarantee requires refusing a new entry
     whose own worst-case loss could push the day past the ceiling, not just
     reacting once the ceiling is already breached. Verified empirically (Round 69)
     against 3.8 years of real historical data at the trader's chosen sizing (TOD $2,100 /
     VWAP-Z $1,500, self_imposed_daily_stop=$3,000): worst historical day under this
     exact rule was -$2,972.88, inside the cap with real margin.
  10. Real-balance reconciliation — reconcile_balance() compares this governor's
      own tracked current_balance against the broker's live settled balance
      each poll cycle. A mismatch beyond balance_reconciliation_tolerance means
      money moved on the account that record_fill() never saw — the exact,
      real failure mode from 2026-09-22 (manual trading on the same account
      desynced the governor undetected, which then falsely attributed the
      resulting equity swing to the trader and tripped a DAILY_LOSS_LIMIT +
      TRAILING_DRAWDOWN breach that shut the bot down while it was flat the
      whole session). Unlike that incident's actual failure (a false breach
      from *misattributed* P&L), a real desync with no threshold crossed is a
      *silent* one — nothing else here would notice a manual trade that
      doesn't also blow through a threshold this governor already watches.
      Once tripped, the mismatch flag is sticky for the life of this
      RiskGovernor instance (not cleared by start_new_trading_day) — main.py
      treats it as a hard breach requiring the bot process to stop, the same
      as rules 1/2, so a human re-checks and restarts with corrected state
      rather than the loop silently trading on with unknown real risk.
  9. Dynamic, equity-scaled position sizing (opt-in, disabled by default) —
     compute_dynamic_risk() returns risk-per-trade as a fraction of the buffer
     actually remaining RIGHT NOW, not a fixed dollar amount, with a smaller
     fraction while underwater vs. the account's original starting balance and
     a larger one once above it. `futures/docs/EDGE_VALIDATION_RESULTS.md`
     Round 26 (2026-09-20) found this changes the shape of the risk/reward
     trade-off, not just its magnitude, versus fixed-dollar sizing (Round 25):
     at the asymmetric rule Round 26 found most capital-efficient, simulated
     probability of reaching the account's profit target exceeded probability
     of blowing it for the first time across the whole campaign. This is a
     REAL RISK-TOLERANCE CHOICE, not something this governor should default
     into silently — `AccountConfig.dynamic_sizing` is None (disabled) unless
     explicitly set, and callers must opt in deliberately. check_position_size()
     still enforces the same hard ceiling/buffer checks on whatever risk value
     is actually proposed, whether it came from compute_dynamic_risk() or a
     fixed default — dynamic sizing changes what gets PROPOSED, not the
     governor's willingness to reject an unsafe proposal.

Unrealized (floating) P&L: DLL and trailing-drawdown checks below include the
current open position's mark-to-market P&L, not just realized/settled P&L (see
`update_unrealized_pnl`). This was a known gap flagged in README.md item #10 —
whether Broker computes these thresholds off real-time equity or EOD-settled
balance only was unconfirmed at time of writing, so this governor takes the
more conservative assumption (real-time) rather than risk being blind to a
fast adverse move on an open position. Re-verify against the real account
before assuming either behavior.

All account numbers below are current as of 2026-09-18 and MUST be re-verified
before the bot is pointed at a real account, especially:
  - consistency_cap_pct — CONFIRMED 2026-09-20 via a real BrokerAPI dashboard
    screenshot of this account (futures/screenshots/, "Captura de
    ecrã 2026-09-20 114848.png"): the dashboard's own "Consistency Target" rule
    reads "Best day is below 55% of profit target" — 55%, not the 50% this file
    used as "the stricter of two candidates" before this screenshot existed.
    That was the wrong direction to be wrong in (a stricter default here would
    have blocked otherwise-legal profitable days, not exposed the account to
    extra risk), but it's now a real confirmed number, not a guess. The same
    screenshot also confirms the trailing-floor and HWM figures below
    ($240,877.88 / $250,877.88) exactly, and the account's current balance
    range, both already correct.
  - static_lock_hwm — still not directly confirmed, but the same 2026-09-20
    dashboard screenshot is suggestive evidence it's correctly `None`: the
    dashboard's own rules panel is headed "1 RULE: Maximum Loss Limit" —
    singular, only the trailing drawdown rule listed, no separate static-lock
    rule shown anywhere on the page. Not fully conclusive from a dashboard
    screenshot alone (a static lock could still exist without a dedicated UI
    callout), but a real signal, not just an assumption. Confirm with Broker
    support or the account agreement text for full certainty before relying on
    it, especially once the account's balance moves far enough past a HWM
    where a lock (if one exists) could plausibly engage.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from enum import Enum, auto
from zoneinfo import ZoneInfo

CENTRAL_TZ = ZoneInfo("America/Chicago")


@dataclass(frozen=True)
class DynamicSizingConfig:
    """Equity-scaled position sizing, per rule 7 in the module docstring above.

    Defaults are Round 26's "asym_down0.04_up0.12" rule — the most
    capital-efficient one found there (highest simulated success-vs-ruin ratio
    among the rules tested), NOT the highest-success-probability one (that was
    a plain 20%-of-buffer fraction, at meaningfully higher simulated ruin risk
    — see `EDGE_VALIDATION_RESULTS.md` Round 26's full grid before choosing
    between them). Re-verify both this choice and its magnitude against
    up-to-date research before relying on it; this config existing does not
    itself endorse any specific risk level as "correct" for this account.
    """

    frac_below_start: float = 0.04  # fraction of current buffer while underwater vs. starting balance
    frac_above_start: float = 0.12  # fraction of current buffer once above starting balance
    risk_floor: float = 25.0  # never propose less than this, however small the buffer
    risk_ceil: float = 2_500.0  # never propose more than this, however large the buffer grows


@dataclass(frozen=True)
class AccountConfig:
    """Constants for the BrokerAPI $250k Freedom Test (verify before live use)."""

    starting_balance: float = 250_000.0
    profit_target_balance: float = 265_000.0  # starting_balance + $15,000
    daily_loss_limit: float = 5_000.0  # Broker's real hard DLL (2% of $250k)
    trailing_dd_amount: float = 10_000.0  # distance from HWM to failure floor
    static_lock_hwm: float | None = None  # UNCONFIRMED — see module docstring
    consistency_cap_pct: float = 0.55  # CONFIRMED via real dashboard screenshot, 2026-09-20 — see module docstring
    session_flatten_time: dt.time = dt.time(15, 10)  # 3:10 PM CT
    timezone: ZoneInfo = CENTRAL_TZ
    # Hard $ cap on any one trade's risk; see rule 5 above. Was $600 (a coincidental
    # match to an earlier, since-superseded MGC sizing figure) -- raised 2026-09-20
    # to $700 after Round 34's refined combined-portfolio sizing recommendation
    # (MNQ $245 / MGC $650 per trade, futures/docs/EDGE_VALIDATION_RESULTS.md
    # Round 34) would otherwise have been silently rejected by check_position_size()
    # the first time an MGC signal proposed $650 -- caught by cross-checking this
    # default against the actual recommended sizing before relying on either.
    max_single_trade_risk: float = 700.0
    consecutive_loss_limit: int = 2  # lock out new entries after this many losses in a row; see rule 6
    self_imposed_daily_stop: float | None = None  # opt-in, tighter-than-DLL same-day cap; see rule 8
    dynamic_sizing: DynamicSizingConfig | None = None  # opt-in equity-scaled sizing; see rule 9
    # Dollar slack allowed between this governor's tracked balance and the broker's
    # live settled balance before reconcile_balance() flags a mismatch (rule 10).
    # Not a loophole for real untracked activity -- real desyncs seen so far have
    # been in the hundreds/thousands of dollars (a manual trade), while this only
    # needs to absorb float/commission-rounding noise between the two sources.
    balance_reconciliation_tolerance: float = 25.0


class LockoutReason(Enum):
    DAILY_LOSS_LIMIT = auto()
    TRAILING_DRAWDOWN = auto()
    SESSION_FLATTEN = auto()
    CONSISTENCY_CAP = auto()  # soft: blocks new profit-taking, not entries/exits generally
    CONSECUTIVE_LOSSES = auto()  # soft: blocks new entries only, no existing position to flatten
    BALANCE_RECONCILIATION_MISMATCH = auto()  # hard: see rule 10


@dataclass
class RiskDecision:
    can_open_new_position: bool
    must_flatten_now: bool
    reasons: list[LockoutReason] = field(default_factory=list)
    remaining_drawdown_buffer: float = 0.0
    daily_pnl: float = 0.0
    consistency_room_left: float | None = None  # None = uncomputable yet (no prior profit)


class RiskGovernor:
    """Tracks account state across sessions and decides whether trading may continue.

    Usage: call `start_new_trading_day(date, opening_balance)` once per session,
    call `record_fill(realized_pnl_delta)` on every closed trade/partial, and call
    `evaluate(now)` before allowing a new entry and periodically to check for a
    forced flatten. This class does not place or cancel orders itself — main.py
    wires its decisions into broker_client.py.
    """

    def __init__(
        self,
        config: AccountConfig,
        starting_balance: float | None = None,
        starting_high_water_mark: float | None = None,
    ) -> None:
        self.config = config
        self.current_balance = starting_balance if starting_balance is not None else config.starting_balance
        self.high_water_mark = starting_high_water_mark if starting_high_water_mark is not None else self.current_balance

        self.daily_start_balance = self.current_balance
        self.daily_realized_pnl = 0.0
        self.current_trading_date: dt.date | None = None

        # Mark-to-market P&L of whatever position is currently open, if any.
        # Zero when flat. Set via update_unrealized_pnl(); cleared automatically
        # by record_fill() on the assumption of one position at a time (this repo's
        # cluster-mutex convention elsewhere) — a full close realizes it, so the
        # floating amount must not also keep counting afterward.
        self.unrealized_pnl: float = 0.0

        # Net realized profit for every trading day strictly before the current one.
        # Keyed by date; used for the consistency-rule calculation.
        self.prior_days_pnl: dict[dt.date, float] = {}

        # Realized losing fills in a row today (0 while flat/on a win/on a scratch).
        # See rule 6 in the module docstring.
        self.consecutive_losses: int = 0

        # Set by reconcile_balance() once a live-vs-tracked balance mismatch beyond
        # tolerance is seen; sticky for this instance's lifetime -- see rule 10.
        self.balance_reconciliation_mismatch: bool = False
        self.last_reconciliation_diff: float | None = None

    # -- session lifecycle -------------------------------------------------

    def start_new_trading_day(self, session_date: dt.date, opening_balance: float | None = None) -> None:
        """Roll daily counters and update the high-water mark from the prior EOD settle.

        Must be called once at the start of each new trading session, with the
        account's actual settled opening balance (falls back to the governor's
        own tracked balance if not supplied, e.g. in tests).
        """
        if self.current_trading_date is not None and self.current_trading_date != session_date:
            self.prior_days_pnl[self.current_trading_date] = self.daily_realized_pnl
            self.high_water_mark = max(self.high_water_mark, self.current_balance)

        self.current_trading_date = session_date
        self.current_balance = opening_balance if opening_balance is not None else self.current_balance
        self.daily_start_balance = self.current_balance
        self.daily_realized_pnl = 0.0
        # Every position must already be flat before session close (session-flatten
        # rule), so a new day should never start with floating P&L — reset
        # defensively in case that invariant is ever violated upstream.
        self.unrealized_pnl = 0.0
        self.consecutive_losses = 0

    def update_unrealized_pnl(self, mark_to_market_pnl: float) -> None:
        """Set the current open position's floating P&L (0.0 when flat).

        Call this on every price/position update from broker_client.py (e.g. a
        POSITION_PNL_UPDATE event) so evaluate() can catch a fast adverse move
        before it's realized, not just after the position closes.
        """
        self.unrealized_pnl = mark_to_market_pnl

    def record_fill(self, realized_pnl_delta: float) -> None:
        """Update balances after a trade (or partial) closes with realized P&L."""
        self.daily_realized_pnl += realized_pnl_delta
        self.current_balance += realized_pnl_delta
        # The P&L that was floating for this position is now realized (folded into
        # daily_realized_pnl/current_balance above) — clear it so evaluate() doesn't
        # double-count it as still-open exposure. Callers with a genuinely different
        # position still open after a partial close should call
        # update_unrealized_pnl() again right after record_fill() to reflect that.
        self.unrealized_pnl = 0.0
        # A loss extends the streak, a win resets it, a breakeven fill does neither
        # (treated as neutral, matching how this account's own trading history
        # journals a scratch: "it's better to have 2 BE than 2 losses").
        if realized_pnl_delta < 0:
            self.consecutive_losses += 1
        elif realized_pnl_delta > 0:
            self.consecutive_losses = 0

    def reconcile_balance(self, live_settled_balance: float) -> bool:
        """Compare this governor's tracked current_balance against the broker's
        live settled balance; call once per poll cycle with
        broker.get_account_balance(). Returns True if they still agree within
        config.balance_reconciliation_tolerance.

        A mismatch means the account moved in a way record_fill() never saw --
        untracked activity (e.g. a manual trade on the same account, the real
        2026-09-22 incident) or a bug in this bot's own fill-handling. Either
        way, every other check in this class is now operating on a current_balance
        it can no longer trust, so the flag this sets is sticky (see rule 10) and
        main.py treats it as a hard breach requiring the process to stop, not
        just a flatten-and-continue.
        """
        diff = live_settled_balance - self.current_balance
        self.last_reconciliation_diff = diff
        if abs(diff) > self.config.balance_reconciliation_tolerance:
            self.balance_reconciliation_mismatch = True
        return not self.balance_reconciliation_mismatch

    # -- rule checks ---------------------------------------------------------

    def check_position_size(self, proposed_risk_dollars: float) -> tuple[bool, str | None]:
        """Whether a proposed new trade's risk is acceptable to open right now.

        Rejects if the proposed risk exceeds the configured hard per-trade cap
        (max_single_trade_risk), or exceeds the drawdown buffer actually
        remaining right now — whichever is smaller. The buffer check matters
        independently of the fixed cap because the buffer itself shrinks over
        time: a trade sized within max_single_trade_risk can still be large
        enough, late in a drawdown, to breach the trailing floor outright in a
        single loss. This is a per-trade gate, separate from evaluate()'s
        account-wide lockout state, because it needs the proposed trade's size
        as an input; call it before placing every new order, in addition to
        (not instead of) evaluate().can_open_new_position.
        """
        if proposed_risk_dollars <= 0:
            return False, "proposed risk must be positive"
        if proposed_risk_dollars > self.config.max_single_trade_risk:
            return False, (
                f"proposed risk ${proposed_risk_dollars:,.2f} exceeds the configured "
                f"per-trade cap of ${self.config.max_single_trade_risk:,.2f}"
            )
        buffer = self.remaining_drawdown_buffer()
        if proposed_risk_dollars > buffer:
            return False, (
                f"proposed risk ${proposed_risk_dollars:,.2f} exceeds the remaining "
                f"drawdown buffer of ${buffer:,.2f} — a single loss at this size "
                f"could breach the trailing floor outright"
            )
        cap = self.config.self_imposed_daily_stop
        if cap is not None and (self.daily_total_pnl() - proposed_risk_dollars) <= -cap:
            return False, (
                f"proposed risk ${proposed_risk_dollars:,.2f} could push today's total "
                f"P&L (${self.daily_total_pnl():,.2f}) past the self-imposed daily stop "
                f"of -${cap:,.2f} on a full loss — see rule 8"
            )
        return True, None

    def compute_dynamic_risk(self) -> float | None:
        """Suggested risk-per-trade under the configured dynamic sizing rule, or
        None if dynamic sizing isn't enabled (config.dynamic_sizing is None) --
        callers should fall back to a fixed size (e.g. a strategy's own default,
        or max_single_trade_risk) in that case. This is a SUGGESTION only:
        check_position_size() still enforces the hard ceiling/buffer check on
        whatever risk value a caller actually proposes to open, whether it came
        from here or from a fixed default -- calling this does not bypass that
        check, and callers must still call check_position_size() before placing
        an order regardless of where the proposed size came from.
        """
        ds = self.config.dynamic_sizing
        if ds is None:
            return None
        frac = ds.frac_above_start if self.current_equity() >= self.config.starting_balance else ds.frac_below_start
        buffer_now = self.remaining_drawdown_buffer()
        return float(min(max(frac * buffer_now, ds.risk_floor), ds.risk_ceil))

    def trailing_floor(self) -> float:
        floor = self.high_water_mark - self.config.trailing_dd_amount
        if self.config.static_lock_hwm is not None and self.high_water_mark >= self.config.static_lock_hwm:
            floor = max(floor, self.config.static_lock_hwm - self.config.trailing_dd_amount)
        return floor

    def current_equity(self) -> float:
        """Settled balance plus whatever the open position is currently worth."""
        return self.current_balance + self.unrealized_pnl

    def daily_total_pnl(self) -> float:
        """Today's realized P&L plus the open position's current floating P&L."""
        return self.daily_realized_pnl + self.unrealized_pnl

    def remaining_drawdown_buffer(self) -> float:
        return self.current_equity() - self.trailing_floor()

    def trailing_dd_breached(self) -> bool:
        return self.current_equity() <= self.trailing_floor()

    def daily_loss_breached(self) -> bool:
        return self.daily_total_pnl() <= -self.config.daily_loss_limit

    def total_net_profit_prior_to_today(self) -> float:
        return sum(self.prior_days_pnl.values())

    def consistency_room_left(self) -> float | None:
        """How much more profit today can book before breaching the consistency cap.

        Returns None when there isn't yet a meaningful cap to compute (no positive
        prior-days profit to be a share of) — callers should treat None as "not
        applicable yet", not as "unlimited".
        """
        prior_profit = self.total_net_profit_prior_to_today()
        if prior_profit <= 0:
            return None
        cap = self.config.consistency_cap_pct
        max_today = (cap / (1 - cap)) * prior_profit
        return max_today - self.daily_realized_pnl

    def consistency_breached(self) -> bool:
        room = self.consistency_room_left()
        return room is not None and room < 0

    def session_flatten_due(self, now: dt.datetime) -> bool:
        local = now.astimezone(self.config.timezone)
        return local.time() >= self.config.session_flatten_time

    def consecutive_loss_breached(self) -> bool:
        return self.consecutive_losses >= self.config.consecutive_loss_limit

    # -- aggregate decision ---------------------------------------------------

    def evaluate(self, now: dt.datetime) -> RiskDecision:
        reasons: list[LockoutReason] = []
        must_flatten = False

        if self.balance_reconciliation_mismatch:
            reasons.append(LockoutReason.BALANCE_RECONCILIATION_MISMATCH)
            must_flatten = True
        if self.daily_loss_breached():
            reasons.append(LockoutReason.DAILY_LOSS_LIMIT)
            must_flatten = True
        if self.trailing_dd_breached():
            reasons.append(LockoutReason.TRAILING_DRAWDOWN)
            must_flatten = True
        if self.session_flatten_due(now):
            reasons.append(LockoutReason.SESSION_FLATTEN)
            must_flatten = True
        if self.consistency_breached():
            reasons.append(LockoutReason.CONSISTENCY_CAP)
            # consistency breach blocks new entries, but does not force flattening
            # an existing position — it is a profit-taking cap, not a loss event.
        if self.consecutive_loss_breached():
            reasons.append(LockoutReason.CONSECUTIVE_LOSSES)
            # same shape as the consistency cap: blocks new entries, not a reason
            # to flatten a position that's already open and otherwise fine.

        return RiskDecision(
            can_open_new_position=len(reasons) == 0,
            must_flatten_now=must_flatten,
            reasons=reasons,
            remaining_drawdown_buffer=self.remaining_drawdown_buffer(),
            daily_pnl=self.daily_total_pnl(),
            consistency_room_left=self.consistency_room_left(),
        )
