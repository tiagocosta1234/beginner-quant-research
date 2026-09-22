"""the trader: the combined TOD-filter + VWAP-Z edge (Rounds 57-59), wired up as one
live Strategy under a single name/process, since both trade MNQ and can't run
as independent bot processes without risking a double position on the same
instrument.

Source of truth: `futures/docs/TRADING_JOURNAL.md`'s 2026-09-21
entries (Rounds 57-63) for how this exact configuration was derived and
checked -- read those before trusting this file with anything beyond a
Practice-mode rehearsal.

SIZING UPDATED 2026-09-22 (Round 69): $2,400/$600 (Round 63's numbers) is
SUPERSEDED -- not because the dollar amounts were wrong, but because the
SIZING FORMULA under it was: every resolver in this campaign (and main.py's
own handle_entry_signal, fixed in the same round) sized contracts against
the signal's tight initial_stop_distance_points, not the wider
trail_distance_points the stop is actually placed at (trail_distance =
TRAIL_ATR_MULT(1.5) x initial distance). That meant "$2,400 risk" could
realize up to ~$3,600 on a trade with zero favorable excursion -- confirmed
against real TOD losses up to -$3,635.67. Once contracts are sized against
the TRUE stop distance (main.py's fix, same commit) and a same-day halt is
enforced BEFORE a new entry whose own worst-case loss could breach a chosen
ceiling (risk_governor.py's new self_imposed_daily_stop, rule 8), a real,
verified daily-loss ceiling becomes possible. Swept four ceiling levels
against the account's current state (balance $247,937.86, buffer $7,059.98,
target gap $17,062.14, 19 real eval days to 2026-10-30) -- $3,000 had the
best success-minus-ruin edge of the four (+2.6pp; the $5,000-ceiling point,
closest to the old sizing's real behavior, actually has ruin EXCEEDING
success, -1.8pp). Chosen: **TOD_RISK=$2,100, VWAPZ_RISK=$1,500,
self_imposed_daily_stop=$3,000 -> P(success)=32.0%, P(ruin)=29.4%**. Verified
empirically, not just asserted: worst real historical day under this exact
sizing + halt rule was -$2,972.88, full history total P&L $488,167, EV/day
$517.13 (mean) / -$551.60 (median -- the edge depends on catching enough
large-winner days to outweigh a majority of small losing ones, same shape
VWAP-Z has shown throughout). See TRADING_JOURNAL.md Round 69/69b before
changing this again -- the sizing is a function of the CURRENT buffer,
target gap, AND the chosen daily-ceiling tradeoff, not a fixed constant.

Composition, not reimplementation: wraps one `RandomEntryAtrTrailStrategy`
(`tod_filter=True`, the Round 39 last-third-of-session variant) and one
`VwapZScoreStrategy` internally, calling both every bar and returning
whichever fires -- reusing the two already-tested strategy classes rather
than re-deriving their signal logic a third time. Per-source sizing is set
explicitly here (`TOD_RISK=$2,400`, `VWAPZ_RISK=$600`, Round 63's corrected
numbers), since `Signal.risk_dollars` is the one field neither wrapped class
sets on its own -- both deliberately leave it at `None` ("use the account
default"), since neither was ever meant to dictate its own dollar size in
isolation.

Gating: no custom "one position at a time" logic needed here --
`main.py`'s `handle_entry_signal()` already refuses any new entry while
`broker.has_open_position()` is True, for every strategy, which is exactly
the rule Round 57's backtest enforced explicitly via
`resolve_trailing_sequential_per_signal_risk`. The two edges gate each other
through that existing mechanism; this file doesn't need to know about it.

Daily loss limit: also already real, existing infrastructure, not something
this file implements. `risk_governor.AccountConfig.daily_loss_limit`
(default $5,000, matching `DAILY_LOSS_LIMIT` throughout this campaign's
Monte Carlo work) is enforced every poll cycle by `main.py`'s own
`governor.evaluate()` call, for every strategy -- the exact hard per-day cap
Round 59 simulated offline is what this account's real risk governor already
does live, with zero extra code required.

Tie-break for the (extremely rare) case both edges fire on the identical
1-minute bar: TOD is checked first. Round 57's backtest sorted the two raw
signal streams by exact timestamp before gating, which has no well-defined
tie-break for a genuine tie either (pandas' default sort is not stable) --
this is a reasonable, documented choice, not a claimed reproduction of a
specific backtest artifact.
"""

from __future__ import annotations

from typing import Any

from live_bot.random_entry_atr_trail_strategy import RandomEntryAtrTrailStrategy
from live_bot.strategy_interface import Signal, SignalAction, Strategy
from live_bot.vwap_zscore_strategy import VwapZScoreStrategy

TOD_RISK = 2100.0
VWAPZ_RISK = 1500.0


class ManualStrategy(Strategy):
    """TOD filter ($2,100/trade) + VWAP-Z ($1,500/trade), combined -- Round 69's
    corrected sizing under the TRUE stop-distance sizing fix, paired with a
    $3,000 self-imposed daily stop (see module docstring). Requires
    SELF_IMPOSED_DAILY_STOP=3000 set in the environment to actually enforce the
    daily ceiling this sizing was chosen for -- the strategy alone only sets
    per-trade risk_dollars, not the daily governor rule. Was $2,400/$600 (Round
    63) until 2026-09-22."""

    def __init__(self, tod: Strategy | None = None, vwapz: Strategy | None = None) -> None:
        # Injectable for testing the priority/tie-break logic in isolation
        # (see tests/test_manual_strategy.py); real use always takes the defaults.
        self._tod = tod if tod is not None else RandomEntryAtrTrailStrategy(tod_filter=True)
        self._vwapz = vwapz if vwapz is not None else VwapZScoreStrategy()

    def on_bar(self, bars: Any) -> Signal:
        # Both are called every bar regardless of which one's result is used --
        # RandomEntryAtrTrailStrategy's per-session state (_entered_today) is
        # meant to advance this way: its random pick for the day is drawn once
        # and consumed whether or not the trader ultimately takes it, matching Round
        # 57's backtest (sig_tod's one candidate per session is generated
        # independently of gating and only discarded afterward if it overlaps
        # an already-open position). VwapZScoreStrategy is fully stateless, so
        # calling it every bar has no side effect to worry about either way.
        tod_signal = self._tod.on_bar(bars)
        vwapz_signal = self._vwapz.on_bar(bars)

        if tod_signal.action in (SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT):
            return Signal(
                action=tod_signal.action,
                initial_stop_distance_points=tod_signal.initial_stop_distance_points,
                trail_distance_points=tod_signal.trail_distance_points,
                risk_dollars=TOD_RISK,
                reason=f"[the trader/TOD ${TOD_RISK:.0f}] {tod_signal.reason}",
            )
        if vwapz_signal.action in (SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT):
            return Signal(
                action=vwapz_signal.action,
                initial_stop_distance_points=vwapz_signal.initial_stop_distance_points,
                trail_distance_points=vwapz_signal.trail_distance_points,
                risk_dollars=VWAPZ_RISK,
                reason=f"[the trader/VWAP-Z ${VWAPZ_RISK:.0f}] {vwapz_signal.reason}",
            )
        return Signal(action=SignalAction.HOLD, reason="the trader: neither TOD nor VWAP-Z fired this bar")
