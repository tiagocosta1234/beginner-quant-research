"""Round 192's disciplined bracket (POC reversion, Round 178 + Value Area
rejection, Round 184) -- the trader's chosen strategy for evaluations from the
2026-09-29 split-strategy Monte Carlo (see futures/docs/
TRADING_JOURNAL.md, "split-strategy Monte Carlo" entry: this signal's real
eval-stage pass rate, 27.9% over a 15-day window at the 50K tier, is ~11x
the combined POC+VA live-stage signal's 2.5%, purely because capping
daily P&L avoids triggering Broker's consistency-rule ratchet).

TWO REAL ADAPTATIONS from the backtested Round 192, both documented here
rather than silently applied -- this is not a 1:1 reproduction of the
backtest, and both make this file WEAKER than Round 192's real 27.9%
number. Read these before trusting a forward-test run to reproduce it:

1. SINGLE LEG AT A TIME, NOT TWO CONCURRENT LEGS. Round 192 holds POC-
   reversion and VA-rejection open SIMULTANEOUSLY when both fire the same
   day. live_bot's entire architecture (main.py's handle_entry_signal,
   every existing Strategy in this repo including manual_strategy.py, per
   its own docstring: "no custom one-at-a-time logic needed here --
   main.py's handle_entry_signal() already refuses any new entry while
   broker.has_open_position() is True") enforces ONE open position at a
   time as a deliberate, cross-cutting safety invariant every other
   strategy also depends on. Weakening that gate to allow two concurrent
   legs is a real architecture change with real blast radius, not
   something to rush through unreviewed while nobody's available to check
   it. This strategy instead checks POC-reversion first, then VA-rejection
   only if POC didn't fire -- the same "check first signal, then second"
   composition manual_strategy.py already uses for TOD+VWAP-Z. At most one
   entry per session.

2. THE $1,650 WIN CAP IS ENFORCED BY CLIPPING THE TAKE-PROFIT PRICE, NOT
   BY MARK-TO-MARKET MONITORING. Round 192's day cap flattens BOTH legs
   the instant their COMBINED mark-to-market P&L crosses $1,650 or -$850,
   necessary there because two legs' unrealized P&L can sum past either
   threshold before either leg's own stop/target fires. With a single leg
   here: the $300-risk-per-trade convention already caps worst-case loss
   at ~$300 (well under -$850 -- the loss side of the cap never binds and
   needs no separate enforcement); the WIN side can genuinely exceed
   $1,650 on a strong single-leg move (the target is the POC itself, an
   unbounded distance), so this strategy clips the take-profit PRICE at
   entry time so the position's own resting limit order can never realize
   more than $1,650 -- enforced by the broker's own bracket order, the
   same already-tested mechanism every other bracket-shape strategy in
   this repo uses, not by this bot polling and reacting after the fact
   (which could miss a fast-moving bar the same way any reactive check
   can). Net effect matches Round 192's real purpose for the win cap
   (never let a single day exceed 55% of the $50K Test's $3,000 target
   and force the consistency-rule ratchet) without new EXIT-signal wiring
   in main.py, which currently has none (checked 2026-09-29: run()'s poll
   loop only handles SignalAction.ENTER_LONG/ENTER_SHORT).

A faithful two-leg port (extending main.py's single-position gate
deliberately, with review) is real, larger follow-up engineering --
flagged, not built here. Treat a practice-account forward-test run as
validating THIS file's actual single-leg behavior, not as reproducing
Round 192's exact 27.9% figure.

ENTRY RULES (unchanged from the backtest -- see round178_volume_profile_poc.py
and round184_value_area_breakout.py in futures/engine/ for the
original causal research):
  POC reversion: previous session's Point of Control (POC, the price level
  with the most RTH volume) vs today's open. If |open - POC| >= 0.15 x S
  (S = 20-session average session range), trade TOWARD the POC: direction
  = sign(POC - open). Stop = 0.15xS beyond the open (away from POC).
  Target = the POC itself.
  VA rejection (checked only if POC reversion didn't fire): previous
  session's Value Area (the range containing 70% of RTH volume, VAL/VAH).
  If today opens above VAH, bet on rejection back into value: short, stop
  = open + (open-VAH), target = the POC. Mirror if today opens below VAL.
  No trade if today's open falls inside yesterday's value area, or if
  neither rule fires.
  Flat by 16:00 ET is NOT separately implemented here -- flatten_routine.py
  already does a real, global 3:10pm CT (4:10pm ET) flatten for every
  strategy in this repo; note this is 10 minutes later than round178/184/
  192's own backtested FLAT_TIME (16:00 ET), a pre-existing, repo-wide
  characteristic (not introduced by this file) worth knowing about, not
  worth building a second flatten mechanism to close.

PRICE LEVELS vs POSITION SIZE: POC/VAL/VAH and stop/target price levels
are computed on live MNQ 1-minute bars directly -- MNQ and full-size NQ
(what round178/184/192 were originally backtested on, via Databento) share
the identical underlying index and tick size (0.25), so the price levels
need no adjustment. Position SIZE differs: MNQ's point value is $2.00/
contract (POINT_VALUE_MNQ below, round11_fvg_bias.POINT_VALUE["MNQ"]) vs
full-size NQ's $20.00 the backtest sized against. This matters because
main.py's handle_entry_signal does NOT auto-size a bracket-shape signal
from risk_dollars (only the trailing-stop path does that conversion) --
it uses Signal.size directly, so this strategy computes its own contract
count, same pattern as ote_fvg_strategy.py's _size_contracts.

20-SESSION RANGE HISTORY (S) is seeded once at construction from this
repo's local Databento NQ dataset (same price scale as live MNQ; last
available date 2026-09-25 as of when this file was written) so the
strategy isn't stuck below the 10-session minimum for its first weeks
live -- see SEED_RANGE_HISTORY below. Self-corrects: real, live-observed
session ranges push the seed out (maxlen=RANGE_WINDOW) as the bot
actually trades. In sharp contrast, "yesterday's POC/VA" (the actual
entry LEVEL each day, not just the stop-sizing input) is NEVER seeded
from local data -- it requires a session this bot has genuinely observed
live, so the very first live session produces no entry signal by design
(fail-safe: no trade on unverified data, not a bug). Confirmed directly
(2026-09-29): the local dataset's last day (2026-09-25) does not reach
"yesterday" relative to any realistic bot start date, so seeding entry
levels from it would risk trading on stale data -- deliberately not done.

RTH TIMESTAMP ASSUMPTION: same UNVERIFIED ASSUMPTION already flagged in
ote_fvg_strategy.py -- this compares each bar's own timestamp directly
against RTH_START/RTH_END, assuming `bars` arrives already in NY wall-
clock time. No existing strategy in this repo does an explicit timezone
conversion on live bars; confirm this against a real connection before
trusting entries are RTH-gated live, not just in backtest.
"""

from __future__ import annotations

import datetime as dt
import os
from collections import deque
from typing import Any

import numpy as np
import pandas as pd

from live_bot.strategy_interface import Signal, SignalAction, Strategy

# RISK_PER_TRADE / CAP_WIN_DOLLARS / MAX_CONTRACTS are TIER-DEPENDENT and
# configurable via env vars -- round192's $300/leg and $1,650 win cap (55%
# of the $50K Test's $3,000 target) are specifically 50K-tier numbers;
# the 27.9% eval-stage pass rate this strategy was chosen for was validated
# at that tier. A different account tier needs these RESCALED, not reused
# as-is: reinvestment_snowball.py's own real tier definitions give the
# $150K tier contract_mult=3.0 (target=$9,000, mll=$4,500), so ALL THREE
# figures scale by the same factor for that tier (0.55 x $9,000 = $4,950,
# matching 1650 x 3 exactly -- confirmed 2026-09-29 the two derivations
# agree, not just assumed). BRACKET_RISK_PER_TRADE / BRACKET_CAP_WIN_DOLLARS
# / BRACKET_MAX_CONTRACTS in the environment override the 50K-tier
# defaults below; set them to match whatever account is actually connected
# (checked via a real, read-only broker.get_account_balance() call, not
# assumed from live_bot/.env's ACCOUNT_STARTING_BALANCE alone -- that field
# was flagged in the 2026-09-24 journal entry as an unverified shadow-test
# stand-in, not a live-verified number).
RISK_PER_TRADE = float(os.getenv("BRACKET_RISK_PER_TRADE", "300.0"))
CAP_WIN_DOLLARS = float(os.getenv("BRACKET_CAP_WIN_DOLLARS", "1650.0"))
MAX_CONTRACTS = int(os.getenv("BRACKET_MAX_CONTRACTS", "50"))
POINT_VALUE_MNQ = 2.0        # $ per 1.0 index point, one MNQ contract (round11's POINT_VALUE["MNQ"])
TICK_MNQ = 0.25              # round11's TICK_SIZE["MNQ"] -- same tick as full-size NQ
STOP_MULT = 0.15             # round178's POC-reversion stop multiplier (x S)
RANGE_WINDOW = 20            # round178's 20-session average-range lookback
RANGE_MIN_PERIODS = 10       # round178's rolling(..., min_periods=10)
VA_PCT = 0.70                # round184's value-area volume fraction
ENTRY_GRACE_MINUTES = 15.0   # tolerate poll-cycle lag; skip entry for the day past this into RTH
RTH_START = dt.time(9, 30)
RTH_END = dt.time(16, 0)

# Seeded 2026-09-29 from futures/engine's local NQ Databento dataset (last
# available session 2026-09-25) -- the 20 most recent real session ranges (high-low,
# RTH). See module docstring's "20-SESSION RANGE HISTORY" section.
SEED_RANGE_HISTORY = [
    183.25, 315.75, 196.0, 362.0, 224.0, 81.75, 261.75, 235.75, 196.5, 166.0,
    424.25, 245.75, 467.75, 187.5, 278.5, 646.25, 302.0, 370.5, 334.25, 267.5,
]


class DisciplinedBracketStrategy(Strategy):
    """See module docstring for the two real adaptations from Round 192."""

    def __init__(self) -> None:
        self._range_history: deque[float] = deque(SEED_RANGE_HISTORY, maxlen=RANGE_WINDOW)
        self._session_date: dt.date | None = None
        self._today_high: float | None = None
        self._today_low: float | None = None
        self._today_profile: dict[float, float] = {}
        self._last_accum_ts: pd.Timestamp | None = None
        self._prev_poc: float | None = None
        self._prev_val: float | None = None
        self._prev_vah: float | None = None
        self._have_verified_prev_session = False
        self._entered_today = False

    # -- internal: building today's volume profile, one bar at a time ---------

    def _accumulate_bar(self, close: float, high: float, low: float, vol: float) -> None:
        px = round(close / TICK_MNQ) * TICK_MNQ
        self._today_profile[px] = self._today_profile.get(px, 0.0) + vol
        self._today_high = high if self._today_high is None else max(self._today_high, high)
        self._today_low = low if self._today_low is None else min(self._today_low, low)

    def _finalize_session(self) -> None:
        """Turns today's accumulated profile into "yesterday" for the next
        session. Called right before rolling into a new day; no-ops if
        nothing was accumulated (e.g. the bot was started mid-session and
        never saw this "today" from its own open)."""
        if not self._today_profile or self._today_high is None or self._today_low is None:
            return
        profile = pd.Series(self._today_profile).sort_index()
        levels = profile.index.to_list()
        poc_idx = int(np.argmax(profile.values))
        poc = float(levels[poc_idx])
        if len(levels) < 2:
            self._prev_poc = self._prev_val = self._prev_vah = poc
        else:
            target = VA_PCT * profile.sum()
            lo = hi = poc_idx
            vol_sum = profile.iloc[poc_idx]
            while vol_sum < target and (lo > 0 or hi < len(levels) - 1):
                vol_below = profile.iloc[lo - 1] if lo > 0 else -1
                vol_above = profile.iloc[hi + 1] if hi < len(levels) - 1 else -1
                if vol_below >= vol_above:
                    lo -= 1
                    vol_sum += profile.iloc[lo]
                else:
                    hi += 1
                    vol_sum += profile.iloc[hi]
            self._prev_poc = poc
            self._prev_val = float(levels[lo])
            self._prev_vah = float(levels[hi])
        self._range_history.append(self._today_high - self._today_low)
        self._have_verified_prev_session = True

    def _reset_today(self) -> None:
        self._today_high = None
        self._today_low = None
        self._today_profile = {}
        self._last_accum_ts = None
        self._entered_today = False

    # -- internal: the two entry rules, unchanged from the backtest -----------

    def _poc_reversion_signal(self, open_px: float) -> tuple[int, float, float] | None:
        if len(self._range_history) < RANGE_MIN_PERIODS or self._prev_poc is None:
            return None
        S = float(np.mean(self._range_history))
        if not (S > 0):
            return None
        dist = self._prev_poc - open_px
        if abs(dist) < STOP_MULT * S:
            return None
        direction = 1 if dist > 0 else -1
        sl = open_px - direction * STOP_MULT * S
        tp = self._prev_poc
        return direction, sl, tp

    def _va_rejection_signal(self, open_px: float) -> tuple[int, float, float] | None:
        if self._prev_val is None or self._prev_vah is None or self._prev_poc is None:
            return None
        va_width = self._prev_vah - self._prev_val
        if not (va_width > 0):
            return None
        if open_px > self._prev_vah:
            sl = open_px + (open_px - self._prev_vah)
            return -1, sl, self._prev_poc
        if open_px < self._prev_val:
            sl = open_px - (self._prev_val - open_px)
            return 1, sl, self._prev_poc
        return None

    def _size_and_cap(self, direction: int, entry: float, sl: float, tp: float) -> tuple[int, float, float]:
        """Sizes contracts off the $300-risk convention, then clips the
        take-profit price so this trade alone can never realize more than
        CAP_WIN_DOLLARS -- see module docstring point 2."""
        dist_stop = abs(entry - sl)
        contracts = max(1, min(int(RISK_PER_TRADE // (dist_stop * POINT_VALUE_MNQ)), MAX_CONTRACTS))
        natural_reward = abs(tp - entry) * POINT_VALUE_MNQ * contracts
        if natural_reward > CAP_WIN_DOLLARS:
            capped_dist = CAP_WIN_DOLLARS / (POINT_VALUE_MNQ * contracts)
            capped_dist = round(capped_dist / TICK_MNQ) * TICK_MNQ
            tp = entry + direction * capped_dist
            reward = CAP_WIN_DOLLARS
        else:
            reward = natural_reward
        return contracts, tp, reward

    # -- the interface ----------------------------------------------------------

    def on_bar(self, bars: Any) -> Signal:
        if bars is None or len(bars) == 0:
            return Signal(action=SignalAction.HOLD, reason="no bars yet")

        df = bars.to_pandas().set_index("timestamp").sort_index()
        latest_ts = df.index[-1]
        latest_time = pd.Timestamp(latest_ts).time()
        today = pd.Timestamp(latest_ts).date()

        if self._session_date != today:
            self._finalize_session()
            self._session_date = today
            self._reset_today()

        todays = df[df.index.date == today]
        rth_mask = [(RTH_START <= pd.Timestamp(ts).time() < RTH_END) for ts in todays.index]
        rth_today = todays[rth_mask]

        new_bars = (
            rth_today[rth_today.index > self._last_accum_ts]
            if self._last_accum_ts is not None
            else rth_today
        )
        for ts, row in new_bars.iterrows():
            self._accumulate_bar(float(row["close"]), float(row["high"]), float(row["low"]), float(row["volume"]))
            self._last_accum_ts = ts

        if self._entered_today or rth_today.empty or not self._have_verified_prev_session:
            return Signal(
                action=SignalAction.HOLD,
                reason=(
                    "already entered today" if self._entered_today
                    else "no RTH bars yet today" if rth_today.empty
                    else "no verified prior-session profile yet (bot hasn't observed a full session live)"
                ),
            )

        minutes_since_open = (
            dt.datetime.combine(today, latest_time) - dt.datetime.combine(today, RTH_START)
        ).total_seconds() / 60.0
        if minutes_since_open > ENTRY_GRACE_MINUTES:
            return Signal(action=SignalAction.HOLD, reason="past today's entry grace window, no trade today")

        open_px = float(rth_today.iloc[0]["open"])
        leg_name = "POC-reversion"
        sig = self._poc_reversion_signal(open_px)
        if sig is None:
            leg_name = "VA-rejection"
            sig = self._va_rejection_signal(open_px)
        if sig is None:
            return Signal(action=SignalAction.HOLD, reason=f"neither leg fired (open={open_px:.2f})")

        direction, sl, tp = sig
        contracts, tp_capped, reward = self._size_and_cap(direction, open_px, sl, tp)
        sl_rounded = round(sl / TICK_MNQ) * TICK_MNQ
        tp_rounded = round(tp_capped / TICK_MNQ) * TICK_MNQ

        self._entered_today = True
        action = SignalAction.ENTER_LONG if direction == 1 else SignalAction.ENTER_SHORT
        return Signal(
            action=action,
            stop_loss_price=sl_rounded,
            take_profit_price=tp_rounded,
            size=contracts,
            risk_dollars=RISK_PER_TRADE,
            expected_reward_dollars=reward,
            reason=(
                f"[{leg_name}] open={open_px:.2f} POC={self._prev_poc:.2f} "
                f"VAL={self._prev_val} VAH={self._prev_vah} sl={sl_rounded:.2f} "
                f"tp={tp_rounded:.2f} contracts={contracts} reward=${reward:.0f}"
            ),
        )
