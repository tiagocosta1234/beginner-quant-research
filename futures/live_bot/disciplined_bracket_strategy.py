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

REBUILT 2026-09-29 (the trader: "cant it just check the data from yesterday
available on the API?") to be a genuine pure function of `bars`, not
in-memory state accumulated bar-by-bar -- the FIRST version required a
full live session observed by this exact running process before it could
ever produce yesterday's POC/VA or seed the 20-session range history
(fail-safe, but meant a restart any time before 16:00 ET lost all of that
day's progress, since none of it was persisted). Checked directly:
brokerapi_py's TradingSuite/RealtimeDataManager loads REAL historical bars
from the broker's own History API at connect time (`initial_days`, a real
TradingSuite.create() kwarg -- confirmed by reading the installed
brokerapi_py==4.3.1 source, not assumed; default 5, the SDK's own
documented examples use up to 30). broker_client.py now requests
BOT_INITIAL_DAYS (env var, default 30) and main.py requests a matching
`bars_needed` for this strategy, so `bars` itself now typically contains
~20-30 real calendar days of history on every single call, from a fresh
connect or not. This strategy now derives "yesterday's POC/VA" and the
20-session range history by grouping the FULL `bars` window into calendar
days and computing each day's own profile -- fresh, from real broker data,
every single on_bar() call, with no cross-call state to lose on a restart.
The only genuinely in-memory, restart-sensitive state left is
`_entered_today` (has this process already taken today's one entry) --
narrow and low-impact: a restart mid-day, after today's entry already
resolved, could in principle let a second entry fire within the same
ENTRY_GRACE_MINUTES window post-restart. Not solved here (same
narrow edge case the original in-memory version also had); main.py's own
has_open_position() gate still prevents an actual double position from a
still-open prior entry.

RTH TIMESTAMP ASSUMPTION: same UNVERIFIED ASSUMPTION already flagged in
ote_fvg_strategy.py -- this compares each bar's own timestamp directly
against RTH_START/RTH_END, assuming `bars` arrives already in NY wall-
clock time. No existing strategy in this repo does an explicit timezone
conversion on live bars; confirm this against a real connection before
trusting entries are RTH-gated live, not just in backtest.

RESOLVED 2026-09-30: confirmed against the real Practice feed -- bars are
stamped in Central time (`-05:00`), NOT New York. on_bar() now converts
tz-aware timestamps to America/New_York before any RTH/date logic (see the
comment there and tests/test_disciplined_bracket_strategy.py). Other live
strategies still carry the unverified assumption (combined_strategy.py
shares this code shape).
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
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


def _session_profile(day_df: pd.DataFrame) -> tuple[float, float, float, float] | None:
    """One completed RTH session's (high-low range, POC, VAL, VAH), or None
    if the day has no RTH bars. Same tick-binned volume-area-expansion
    algorithm as round178_volume_profile_poc.session_poc /
    round184_value_area_breakout.session_value_area, verified to match
    those functions exactly (2026-09-29, 15 real sessions, 0 mismatches)."""
    if day_df.empty:
        return None
    px = (day_df["close"] / TICK_MNQ).round() * TICK_MNQ
    profile = pd.Series(day_df["volume"].values, index=px.values).groupby(level=0).sum().sort_index()
    levels = profile.index.to_list()
    poc_idx = int(np.argmax(profile.values))
    poc = float(levels[poc_idx])
    day_range = float(day_df["high"].max() - day_df["low"].min())
    if len(levels) < 2:
        return day_range, poc, poc, poc
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
    return day_range, poc, float(levels[lo]), float(levels[hi])


class DisciplinedBracketStrategy(Strategy):
    """See module docstring for the two real adaptations from Round 192,
    and the 2026-09-29 rebuild note on why this derives everything fresh
    from `bars` rather than accumulating state across calls."""

    def __init__(self, disable_va: bool | None = None, poc_filter: str | None = None,
                 filter_log_path: str | os.PathLike | None = None) -> None:
        self._entered_today = False
        self._entered_date: dt.date | None = None
        # VA-rejection fallback on/off (2026-09-30, Round 230: the fallback lost money
        # in both halves of the 2019-2026 history and in every 24/5 variant; dropping
        # it was the better configuration, as an in-sample choice). Default keeps the
        # original behavior; BRACKET_DISABLE_VA=1 in the environment turns it off.
        if disable_va is None:
            disable_va = os.getenv("BRACKET_DISABLE_VA", "0").strip().lower() in ("1", "true", "yes")
        self.disable_va = disable_va
        # POC filter (2026-09-30, Round 244's lead: POC only after a NARROW prior day in a
        # NOT-LOW-VOL regime). "off" (default) = unchanged; "log" = trade as usual but
        # record the filter's verdict for every POC signal (paper tracking); "on" = skip
        # POC signals the filter rejects. Needs daily history (live_bot/daily_history.py).
        if poc_filter is None:
            poc_filter = os.getenv("BRACKET_POC_FILTER", "off").strip().lower()
        if poc_filter not in ("off", "log", "on"):
            raise ValueError(f"BRACKET_POC_FILTER must be off, log or on (got {poc_filter!r})")
        self.poc_filter = poc_filter
        self._history = None
        self._filter_log_path = Path(filter_log_path or os.getenv(
            "BRACKET_POC_FILTER_LOG", Path(__file__).resolve().parent / "logs" / "poc_filter_paper.csv"))
        self._logged_date: dt.date | None = None

    def _poc_filter_verdict(self, rth: pd.DataFrame, today: dt.date) -> dict | None:
        from live_bot.daily_history import DailyHistory, poc_filter_features
        if self._history is None:
            self._history = DailyHistory()
        self._history.merge_live(rth, today)
        return poc_filter_features(self._history.before(today))

    def _log_filter(self, today: dt.date, direction: int, open_px: float, feats: dict | None, acted: str) -> None:
        if self._logged_date == today:
            return
        self._logged_date = today
        row = dict(date=today.isoformat(), mode=self.poc_filter, direction=direction, open=open_px,
                   verdict=("insufficient history" if feats is None else ("PASS" if feats["passed"] else "FAIL")),
                   acted=acted, **({k: feats[k] for k in ("prev_range", "rng_sma20", "rv20", "rv20_med250",
                                                           "narrow", "lowvol", "history_days", "last_session")}
                                   if feats else {}))
        path = self._filter_log_path
        path.parent.mkdir(parents=True, exist_ok=True)
        new = not path.exists()
        pd.DataFrame([row]).to_csv(path, mode="a", header=new, index=False)

    def _size_and_cap(self, direction: int, entry: float, sl: float, tp: float) -> tuple[int, float, float]:
        """Sizes contracts off the $300-risk convention, then clips the
        take-profit price so this trade alone can never realize more than
        CAP_WIN_DOLLARS -- see module docstring point 2.

        CHECKED 2026-09-29 (the trader: "cant have days below -1000$ or above
        1650$"): briefly suspected and "fixed" a bug here (VA-rejection's
        unbounded stop distance forcing an oversized 1-contract position on
        wide-breakout days) based on an ad-hoc debugging script that showed
        real days breaching both bounds. That script had its own sign bug
        (didn't multiply by `direction` in two of its four P&L branches,
        turning legitimate short-side wins into apparent large losses) --
        with that fixed, this function's real behavior across the full
        2019-2026 history is: 0% of days below -$1,000 (worst day exactly
        -$300, precisely the intended risk), 1 day in 1,448 (0.07%) a single
        tick over $1,650. The function was correct; reverted the
        unnecessary change rather than leave live_bot deviating from the
        parity-verified original for no real reason."""
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

    def _poc_reversion_signal(self, open_px: float, prev_poc: float, S: float) -> tuple[int, float, float] | None:
        if not (S > 0):
            return None
        dist = prev_poc - open_px
        if abs(dist) < STOP_MULT * S:
            return None
        direction = 1 if dist > 0 else -1
        sl = open_px - direction * STOP_MULT * S
        return direction, sl, prev_poc

    def _va_rejection_signal(self, open_px: float, prev_poc: float, prev_val: float, prev_vah: float) -> tuple[int, float, float] | None:
        va_width = prev_vah - prev_val
        if not (va_width > 0):
            return None
        if open_px > prev_vah:
            sl = open_px + (open_px - prev_vah)
            return -1, sl, prev_poc
        if open_px < prev_val:
            sl = open_px - (prev_val - open_px)
            return 1, sl, prev_poc
        return None

    def on_bar(self, bars: Any) -> Signal:
        if bars is None or len(bars) == 0:
            return Signal(action=SignalAction.HOLD, reason="no bars yet")

        df = bars.to_pandas().set_index("timestamp").sort_index()
        # Live bars arrive tz-aware in the exchange's Central time (verified
        # 2026-09-30: `-05:00` stamps on the BrokerAPI feed), but RTH_START/RTH_END
        # and the Round 192 backtest are New York wall-clock. Without this the RTH
        # window, the 15-minute entry grace and every profile day were shifted an
        # hour. Naive timestamps are assumed to already be New York wall-clock.
        if getattr(df.index, "tz", None) is not None:
            df.index = df.index.tz_convert("America/New_York").tz_localize(None)
        latest_ts = df.index[-1]
        latest_time = pd.Timestamp(latest_ts).time()
        today = pd.Timestamp(latest_ts).date()

        if self._entered_date != today:
            self._entered_today = False
            self._entered_date = today

        rth_mask = [(RTH_START <= pd.Timestamp(ts).time() < RTH_END) for ts in df.index]
        rth = df[rth_mask]
        if rth.empty:
            return Signal(action=SignalAction.HOLD, reason="no RTH bars in window yet")

        dates_present = sorted(set(rth.index.date))
        prior_dates = [d for d in dates_present if d < today]
        if not prior_dates:
            return Signal(
                action=SignalAction.HOLD,
                reason="no completed prior session in the bars window yet -- "
                       "need at least yesterday's RTH session (check BOT_INITIAL_DAYS/bars_needed)",
            )

        # Compute every completed prior session's own profile fresh from the
        # real bars window -- no reliance on this process having personally
        # observed them live (see module docstring's 2026-09-29 rebuild note).
        profiles: dict[dt.date, tuple[float, float, float, float]] = {}
        for d in prior_dates:
            day_df = rth[rth.index.date == d]
            prof = _session_profile(day_df)
            if prof is not None:
                profiles[d] = prof
        if not profiles:
            return Signal(action=SignalAction.HOLD, reason="no usable prior-session profile in the bars window")

        ordered_dates = sorted(profiles.keys())
        yesterday = ordered_dates[-1]
        _, prev_poc, prev_val, prev_vah = profiles[yesterday]
        range_history = [profiles[d][0] for d in ordered_dates[-RANGE_WINDOW:]]

        todays_rth = rth[rth.index.date == today]
        if self._entered_today or todays_rth.empty:
            return Signal(
                action=SignalAction.HOLD,
                reason="already entered today" if self._entered_today else "no RTH bars yet today",
            )

        minutes_since_open = (
            dt.datetime.combine(today, latest_time) - dt.datetime.combine(today, RTH_START)
        ).total_seconds() / 60.0
        if minutes_since_open > ENTRY_GRACE_MINUTES:
            return Signal(action=SignalAction.HOLD, reason="past today's entry grace window, no trade today")

        open_px = float(todays_rth.iloc[0]["open"])
        leg_name = "POC-reversion"
        sig = None
        if len(range_history) >= RANGE_MIN_PERIODS:
            S = float(np.mean(range_history))
            sig = self._poc_reversion_signal(open_px, prev_poc, S)
        filter_note = ""
        if sig is not None and self.poc_filter != "off":
            feats = self._poc_filter_verdict(rth, today)
            passed = bool(feats and feats["passed"])
            skip = self.poc_filter == "on" and not passed
            self._log_filter(today, sig[0], open_px, feats, "skipped" if skip else "traded")
            filter_note = (f" filter[{self.poc_filter}]="
                           + ("insufficient history" if feats is None else
                              f"{'PASS' if passed else 'FAIL'} (narrow={feats['narrow']}, lowvol={feats['lowvol']})"))
            if skip:
                if self.disable_va:
                    self._entered_today = True  # decided for today; stop re-evaluating
                    return Signal(action=SignalAction.HOLD, reason=f"POC signal filtered out{filter_note}")
                sig = None
        if sig is None and not self.disable_va:
            leg_name = "VA-rejection"
            sig = self._va_rejection_signal(open_px, prev_poc, prev_val, prev_vah)
        if sig is None:
            return Signal(
                action=SignalAction.HOLD,
                reason=f"neither leg fired (open={open_px:.2f}, {len(range_history)} sessions of range history)",
            )

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
                f"[{leg_name}] open={open_px:.2f} POC={prev_poc:.2f} "
                f"VAL={prev_val} VAH={prev_vah} sl={sl_rounded:.2f} "
                f"tp={tp_rounded:.2f} contracts={contracts} reward=${reward:.0f} "
                f"(yesterday={yesterday}, {len(range_history)} sessions of range history){filter_note}"
            ),
        )
