"""Strategy-agnostic risk limits for the live bot.

The governor enforces self-imposed risk limits independently of the strategy plugged in via
strategy_interface.py and of the broker connection in broker_client.py. It has no network
dependency, so it is fully unit tested with synthetic P&L sequences (tests/test_risk_governor.py).

Limits (all amounts are settings in AccountConfig, not facts about any account):
  1. Daily loss limit: hard lockout once today's realized loss reaches the limit.
  2. Trailing maximum drawdown: stop trading if equity falls to the highest end-of-day balance
     minus trailing_dd_amount. Optionally the floor stops trailing once the high-water mark
     passes static_lock_hwm (None = it trails forever, the conservative choice).
  3. Best-day share: once today's profit would exceed consistency_cap_pct of total net profit,
     no further profit is booked today. The governor only limits new profit; it never forces a
     loss to "fix" a day that is already over the share.
  4. Session flatten: every position is closed before session_flatten_time.
  5. Per-trade risk cap: check_position_size() rejects a trade whose risk exceeds
     max_single_trade_risk or the drawdown buffer actually left, whichever is smaller.
     Oversized trades, not bad signals, did most of the damage in the author's manual trading.
  6. Consecutive-loss lockout: no new entries after consecutive_loss_limit losing fills in a row
     within one day (a breakeven fill neither extends nor resets the streak).
  8. Daily stop, pre-emptive (opt-in): a trade is refused if today's P&L minus that trade's own
     risk would already be past -self_imposed_daily_stop. A circuit breaker can only act between
     trades, so a real guarantee must refuse the trade that could cross the line.
  9. Equity-scaled sizing (opt-in): compute_dynamic_risk() sizes each trade as a fraction of the
     buffer left right now, smaller while underwater and larger once above the start.
 10. Balance reconciliation: reconcile_balance() compares the tracked balance with the broker's
     settled balance each poll. A mismatch means money moved that record_fill() never saw (for
     example a manual trade on the same account); the flag is sticky and main.py stops the bot
     so a human re-checks the state.
 11. Consecutive losing days: no new entries after consecutive_losing_days_limit days in a row
     that each ended negative. Rule 6 resets daily, so it cannot see a run of separate bad days;
     a walk-forward test found five small losing days summing past the drawdown limit.
 12. Daily profit cap (opt-in, max_daily_profit): the mirror of rule 8, refusing a fixed-target
     trade whose own best case would push the day past the cap.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
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
    """Default risk-limit settings. Examples only: set your own before any live use."""

    starting_balance: float = 250_000.0
    profit_target_balance: float = 265_000.0  # starting_balance + $15,000
    daily_loss_limit: float = 5_000.0  # example: 2% of the starting balance
    trailing_dd_amount: float = 10_000.0  # distance from HWM to failure floor
    static_lock_hwm: float | None = None  # None = the floor trails forever; see rule 2
    consistency_cap_pct: float = 0.55  # best day at most 55% of total profit; see rule 3
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
    # consecutive_loss_limit resets every day, so it cannot see a run of separate bad days;
    # rule 11 caps consecutive losing days (a walk-forward test found five small losing days
    # summing past the drawdown limit). Default 5.
    consecutive_losing_days_limit: int = 5
    self_imposed_daily_stop: float | None = None  # opt-in, tighter-than-DLL same-day cap; see rule 8
    # Opt-in daily profit cap (rule 12): blocks new entries once today's profit is at or past
    # it. It cannot stop one fixed-target fill from landing above the cap, so size the
    # strategy's own target under it.
    max_daily_profit: float | None = None
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
    CONSECUTIVE_LOSING_DAYS = auto()  # soft: see rule 11; blocks new entries across day boundaries


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

    Persistence (opt-in via state_file, added 2026-09-24): every field above that
    has no live-broker equivalent (prior_days_pnl, consecutive_losing_days,
    high_water_mark, current_trading_date, and today's own daily_realized_pnl/
    consecutive_losses) previously lived ONLY in this instance's memory. A real
    gap, found by inspection the same day live_bot's process had already been
    restarted several times during a single shadow-test session: every restart
    silently reset consecutive_losing_days to 0 and wiped prior_days_pnl, quietly
    defeating rule 11 (the 5-losing-day circuit breaker) and rule 3's consistency
    check across a restart -- and start_new_trading_day() being unconditionally
    called once at every process startup (main.py) meant even a same-day restart
    wiped today's own daily_realized_pnl/consecutive_losses, undermining rules 1/6/12
    for the rest of that day too. current_balance is deliberately NOT persisted --
    it always comes from the constructor's starting_balance (which callers seed
    from broker.get_account_balance() each restart), the same live-source-of-truth
    principle rule 10 already enforces; a persisted balance could silently mask a
    real reconciliation mismatch instead of surfacing it.
    """

    def __init__(
        self,
        config: AccountConfig,
        starting_balance: float | None = None,
        starting_high_water_mark: float | None = None,
        state_file: str | Path | None = None,
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

        # Completed trading DAYS in a row that ended net negative (0 after any day
        # that ended net >= 0). Updated once per day, in start_new_trading_day(), not
        # per-fill -- see rule 11. Distinct from consecutive_losses above, which
        # resets every day and so cannot see a streak spanning multiple days.
        self.consecutive_losing_days: int = 0

        # Set by reconcile_balance() once a live-vs-tracked balance mismatch beyond
        # tolerance is seen; sticky for this instance's lifetime -- see rule 10.
        self.balance_reconciliation_mismatch: bool = False
        self.last_reconciliation_diff: float | None = None

        # Opt-in disk persistence for the state above that has no live-broker
        # equivalent -- see the class docstring. None (default) preserves this
        # class's original fully-in-memory, no-I/O behavior exactly, so every
        # existing test that never passes state_file is unaffected.
        self._state_file = Path(state_file) if state_file else None
        self._load_state()

    # -- persistence -----------------------------------------------------------

    def _load_state(self) -> None:
        """Restore state from a prior instance's _save_state(), if state_file is
        set and the file exists. Missing/corrupt/unreadable state fails SAFE by
        leaving this instance's fresh-start defaults in place (equivalent to no
        persistence configured) rather than crashing the bot on a bad file."""
        if self._state_file is None or not self._state_file.exists():
            return
        try:
            data = json.loads(self._state_file.read_text())
        except (OSError, ValueError):
            return
        if data.get("current_trading_date"):
            self.current_trading_date = dt.date.fromisoformat(data["current_trading_date"])
        self.daily_realized_pnl = data.get("daily_realized_pnl", self.daily_realized_pnl)
        self.consecutive_losses = data.get("consecutive_losses", self.consecutive_losses)
        self.consecutive_losing_days = data.get("consecutive_losing_days", self.consecutive_losing_days)
        self.prior_days_pnl = {
            dt.date.fromisoformat(k): v for k, v in data.get("prior_days_pnl", {}).items()
        }
        self.high_water_mark = data.get("high_water_mark", self.high_water_mark)
        self.balance_reconciliation_mismatch = data.get(
            "balance_reconciliation_mismatch", self.balance_reconciliation_mismatch
        )
        self.last_reconciliation_diff = data.get("last_reconciliation_diff", self.last_reconciliation_diff)

    def _save_state(self) -> None:
        """Persist the fields _load_state() restores. Called after every mutation
        of that state (start_new_trading_day, record_fill, reconcile_balance) so a
        process kill at any point loses at most the in-flight call, not the whole
        session. No-op unless state_file was configured."""
        if self._state_file is None:
            return
        data = {
            "current_trading_date": self.current_trading_date.isoformat() if self.current_trading_date else None,
            "daily_realized_pnl": self.daily_realized_pnl,
            "consecutive_losses": self.consecutive_losses,
            "consecutive_losing_days": self.consecutive_losing_days,
            "prior_days_pnl": {d.isoformat(): v for d, v in self.prior_days_pnl.items()},
            "high_water_mark": self.high_water_mark,
            "balance_reconciliation_mismatch": self.balance_reconciliation_mismatch,
            "last_reconciliation_diff": self.last_reconciliation_diff,
        }
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._state_file.with_suffix(self._state_file.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(self._state_file)  # atomic swap -- never leaves a half-written state file

    # -- session lifecycle -------------------------------------------------

    def start_new_trading_day(self, session_date: dt.date, opening_balance: float | None = None) -> None:
        """Roll daily counters and update the high-water mark from the prior EOD settle.

        Must be called once at the start of each new trading session, with the
        account's actual settled opening balance (falls back to the governor's
        own tracked balance if not supplied, e.g. in tests).

        main.py actually calls this unconditionally on every process startup, not
        just once per real calendar day -- so this must also be safe to call again
        on a same-day restart (session_date == self.current_trading_date already,
        e.g. from a reloaded state_file) WITHOUT wiping today's already-accumulated
        daily_realized_pnl/consecutive_losses. Only refresh the live balance and
        return; the roll-into-prior-days logic below only fires on an actual day
        change.
        """
        if self.current_trading_date == session_date:
            if opening_balance is not None:
                self.current_balance = opening_balance
            self._save_state()
            return

        if self.current_trading_date is not None:
            self.prior_days_pnl[self.current_trading_date] = self.daily_realized_pnl
            self.high_water_mark = max(self.high_water_mark, self.current_balance)
            if self.daily_realized_pnl < 0:
                self.consecutive_losing_days += 1
            else:
                self.consecutive_losing_days = 0

        self.current_trading_date = session_date
        self.current_balance = opening_balance if opening_balance is not None else self.current_balance
        self.daily_start_balance = self.current_balance
        self.daily_realized_pnl = 0.0
        # Every position must already be flat before session close (session-flatten
        # rule), so a new day should never start with floating P&L — reset
        # defensively in case that invariant is ever violated upstream.
        self.unrealized_pnl = 0.0
        self.consecutive_losses = 0
        self._save_state()

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
        self._save_state()

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
        self._save_state()
        return not self.balance_reconciliation_mismatch

    # -- rule checks ---------------------------------------------------------

    def check_position_size(
        self, proposed_risk_dollars: float, proposed_reward_dollars: float | None = None,
    ) -> tuple[bool, str | None]:
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

        proposed_reward_dollars (optional, mirrors proposed_risk_dollars):
        added 2026-09-24 so a full-target win can be checked PREEMPTIVELY
        against max_daily_profit (rule 12), not just reactively after the fact
        -- a reactive-only check was proven insufficient in the backtest
        engine (round76's resolve_outcomes_gated) once two individually-
        compliant wins the same real day still summed past the $1,650 cap.
        Only strategies with a fixed target (Signal.expected_reward_dollars)
        can supply this before a fill; when omitted, max_daily_profit still
        gets checked reactively below, same as before this fix.
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
        profit_cap = self.config.max_daily_profit
        if profit_cap is not None and self.daily_total_pnl() >= profit_cap:
            return False, (
                f"today's total P&L (${self.daily_total_pnl():,.2f}) is already at or past "
                f"the max_daily_profit cap of ${profit_cap:,.2f} — no new entries until "
                f"tomorrow, see rule 12."
            )
        if (
            profit_cap is not None
            and proposed_reward_dollars is not None
            and self.daily_total_pnl() + proposed_reward_dollars > profit_cap
        ):
            return False, (
                f"proposed reward ${proposed_reward_dollars:,.2f} could push today's total "
                f"P&L (${self.daily_total_pnl():,.2f}) past the max_daily_profit cap of "
                f"${profit_cap:,.2f} if it fully wins — refused BEFORE the fact, see rule 12"
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

    def best_single_day_profit_prior_to_today(self) -> float:
        """Largest COMPLETED day's profit, across every day strictly before
        today. -inf if there is no completed day yet (mathematically inert in
        every comparison this feeds -- max(-inf, x) == x)."""
        return max(self.prior_days_pnl.values(), default=float("-inf"))

    def consistency_room_left(self) -> float | None:
        """How much more profit today can book before breaching the consistency cap
        -- negative if ALREADY breached (by today's own day, or by a past day still
        too large a share of a total that hasn't caught up yet).

        FIXED 2026-09-24, TWICE, both real bugs confirmed empirically:

        Fix 1: the original formula compared today's profit only against PRIOR
        days summed, and returned None ("no cap") whenever prior profit was <= 0
        -- meaning a single day banking the ENTIRE profit target (100%
        concentration, the exact case this rule exists to catch) was never
        flagged. Confirmed with a real $3,500-in-one-day test:
        consistency_breached() returned False. Fixed by gating on the actual
        profit_target_balance (already on AccountConfig, never referenced here
        before) rather than "any prior profit at all" -- matches the usual worked example (a $1,600 best day out
        of $3,000 total profit is 53%, under 55%) and every backtest's Monte Carlo (`cum >= target and
        best_day <= cap*cum`), which already modeled it this way.

        Fix 2 (this pass): fix 1 still only checked TODAY's own contribution --
        it had no way to see that a PAST day remains the disqualifying one
        against a total that hasn't grown enough yet to dilute it. Confirmed
        against Round 85's own real walk-forward data: a $11,731.20 day (Aug
        27) kept the account genuinely non-compliant for the following week
        even though every subsequent day was individually small and positive
        -- the old, once-fixed check still returned consistency_breached()=False
        the entire time. Fixed by tracking the actual best single day EVER
        (best_single_day_profit_prior_to_today), not just "today vs. the sum of
        everything before it", and checking that against the running total --
        the same general form the Monte Carlo has always used.

        Returns None when total accumulated profit (prior + today) hasn't
        reached the target yet -- callers should treat None as "the rule does
        not bind yet", not as "unlimited forever".
        """
        target_profit = self.config.profit_target_balance - self.config.starting_balance
        prior_profit = self.total_net_profit_prior_to_today()
        total_profit_today = prior_profit + self.daily_realized_pnl
        if total_profit_today < target_profit:
            return None
        cap = self.config.consistency_cap_pct
        prior_best_day = self.best_single_day_profit_prior_to_today()
        if prior_best_day > cap * total_profit_today:
            # Already breached by a day that isn't today -- no amount of
            # room "today" can retroactively fix that day; report how far
            # over the cap that past day currently sits, as a negative number.
            return cap * total_profit_today - prior_best_day
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

    def consecutive_losing_days_breached(self) -> bool:
        return self.consecutive_losing_days >= self.config.consecutive_losing_days_limit

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
        if self.consecutive_losing_days_breached():
            reasons.append(LockoutReason.CONSECUTIVE_LOSING_DAYS)
            # soft, same as above -- this triggers at the start of a new day (see
            # start_new_trading_day()), so there is never an open position to
            # flatten when it fires.

        return RiskDecision(
            can_open_new_position=len(reasons) == 0,
            must_flatten_now=must_flatten,
            reasons=reasons,
            remaining_drawdown_buffer=self.remaining_drawdown_buffer(),
            daily_pnl=self.daily_total_pnl(),
            consistency_room_left=self.consistency_room_left(),
        )
