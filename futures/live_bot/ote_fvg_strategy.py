"""OTE + 15m FVG sweep-reclaim strategy (MNQ) -- live-wireable port of
`futures/engine/round76_ote_pdarray_formalized.py`'s
`detect_ote_signals`, the best real capped candidate found in this
campaign's 2026-09-24 strategy search. Sizing history: FIXED_STOP_POINTS=10
since Round 82 (was 20, the videos' own constant, never fit to MNQ's real
volatility); RR was set to 1:4 in Round 87 (was 1:2, Round 82's in-sample
pick) so a single trade's own win stayed under the trader's real $1,650/day
consistency-derived cap. RESIZED to RR=1:3 the same day (Round 97/98) after
a real data-quality defect was found and fixed in `MNQ_1MIN_BROKERAPI.csv`
(real RTH volume was 1,128-17,425/day for 2026-07-27 through 09-11 --
impossible for real MNQ, a feed defect, not a market condition; fixed via
`round11_fvg_bias.load_1m_mnq_reconciled()`, cross-validated against the
legacy dataset). Re-run on the corrected data, the walk-forward's own
latest (most-current) folds select RR=1:3, not 1:4 -- see
the research log's 2026-09-24 "DATA FIXED" entry for the full derivation.

INVALIDATED 2026-09-25 (Round 104) -- the numbers below are WRONG, kept only
so the correction is visible in-place rather than silently deleted. Rounds
82/96-103 all re-scored one frozen `detect_ote_signals()` signal set across a
swept (stop, RR) grid, but that detector bakes each signal's stop-loss PRICE
LEVEL in at detection time using round76's own hardcoded 20.0-point constant
-- verified directly, every signal's |entry-stop| was exactly 20.0 no matter
what stop_points got swept afterward. So every "stop=10 wins" claim below was
actually scoring a 20-point-wide exit corridor while pricing/sizing/reporting
it as a 10-point one. Fixed and re-run end-to-end in
`futures/engine/round104_ote_fixed_stop_validation.py`: the
corrected walk-forward no longer even picks stop=10/RR=3 (it picks
stop=40/RR=4 instead), and even that corrected best configuration fails this
campaign's own significance bar (bootstrap P(edge>0)=53.6%, 90% CI
[-$139.78, $159.02] -- straddles zero, not >=90%). Plain reading: there is
currently NO statistically validated real edge for this strategy on MNQ.
Full derivation and the buggy-vs-fixed comparison table:
the research log's 2026-09-25 "MAJOR CORRECTION" entry. Do not fund or
attempt a real Test purchase off the numbers below -- they do not hold.
The live code's OWN stop/RR constants just below (FIXED_STOP_POINTS=10,
RR=3.0) are UNAFFECTED by this bug (self-consistent at detection time) but
are also NOT the corrected walk-forward's pick -- they are simply unvalidated
now, not proven wrong as specific numbers, just no longer backed by the
(broken) evidence that was cited for them.

~~Current validated numbers (Round 97/98, TRUE walk-forward on the RECONCILED
(data-quality-fixed) dataset -- parameters chosen using only data prior to
each test fold, not hindsight over the whole sample -- NY RTH-only entries,
single-trade-compliant sizing, real $1,650/day cap enforced PREEMPTIVELY,
not reactively): n=56 real trades, bootstrap P(true edge>0)=100.0%,
baseline P(success)=100.0%, P(ruin)=0.0%, median=5.0 days at a 10-day
window.~~ INVALIDATED -- see above.

STATUS (2026-09-25): WIRED IN for Practice-mode shadow-testing
(`BOT_STRATEGY=ote_fvg` in `main.py`'s `_select_strategy()`), NOT VALIDATED
FOR LIVE, and now additionally NOT VALIDATED AT ALL pending a real edge
being found on the corrected pipeline. Prerequisites #1/#2 below are done;
#3/#4 are the reason this must still not point at a real Test attempt:

  1. DONE -- `main.py`'s `bars_needed` now has an explicit `OteFvgStrategy`
     branch (1500 bars) rather than the 500-bar default, which this
     strategy's own worst-case lookback (K_MIN(60) + up to 2x
     MAX_LOOKAHEAD_BARS(240) + the 15m FVG resample's own lag, ~540 minutes
     minimum) would have silently outrun.
  2. DONE -- main.py's bracket-order path (`stop_loss_price`/`take_profit_price`
     both set) had never been exercised by any real strategy in this repo
     before this one -- every prior strategy (the trader, VWAP-Z, RandomEntryAtrTrail,
     SupportResistanceBounce) uses the trailing-stop shape instead. Real gap
     found while building this: for the trailing shape, `handle_entry_signal()`
     computes `contracts` itself from `risk_dollars / trail_distance_points`;
     for the BRACKET shape, it uses `signal.size` directly with NO such
     derivation (main.py, `place_bracket_order(..., size=signal.size, ...)`).
     That's why this class computes and sets `Signal.size` itself (see
     `_size_contracts`) rather than relying on `risk_dollars` alone.
  3. IN PROGRESS -- shadow-testing in Practice mode (ACCOUNT-ID,
     the account this campaign already uses for rehearsals). STILL ZERO REAL
     FILLS as of 2026-09-24 -- the RTH-only filter means this strategy only
     gets a real chance to fire during NY market hours, and none had
     qualified yet as of this entry. Needed before any real Test attempt:
     at least one real live fill, confirmed against a parallel offline run
     of round76/round97 on the same real bars, to verify live execution
     (stop/target placement, the unverified NY-timezone assumption below)
     actually matches what the backtest assumes.
  4. STILL OPEN -- even the corrected n=56 sample is ~43 real trading days
     (capped by the active MNQ contract's own lifetime, not assumed) -- grow
     that sample and re-validate periodically, not just once.

Ported pieces, self-contained (this repo's convention: `live_bot/` does not
import from `futures/`, matching `vwap_zscore_strategy.py`'s own
`_session_vwap_z`/`_causal_atr15` reimplementations rather than importing
round49's) -- `_resample_causal` and `_detect_fvgs` are round11_fvg_bias.py's
functions verbatim; `_detect_ote_signals` is round76's `detect_ote_signals`
verbatim. Any future change to the source-of-truth round files must be
mirrored here by hand; nothing enforces the two staying in sync.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import numpy as np
import pandas as pd

from live_bot.strategy_interface import Signal, SignalAction, Strategy

K_MIN = 60                  # lookback window (minutes) for "prior swing low/high"
MIN_LEG_POINTS = 15.0       # ignore legs smaller than this (noise filter)
RETRACE_LOCK_FRAC = 0.30    # leg's far end "locks in" once price gives back this much
MAX_LOOKAHEAD_BARS = 240    # abandon a candidate sweep if no valid entry within 4h
OTE_LO, OTE_HI = 0.618, 0.79
FIXED_STOP_POINTS = 10.0    # round82 finding, 2026-09-24: the videos' own 20pt constant was
                             # never fit to MNQ's real volatility; sweeping stop x RR found this
                             # dominates (P(success)=95.3% vs 20pt's 63.7% in the baseline simulation),
                             # and unlike prior "great numbers" this campaign has found, it holds
                             # up under OOS-split/tail-concentration scrutiny -- see round82's
                             # own docstring for the full verification, not just the headline.
RR = 3.0                    # round97/98 finding, 2026-09-24 (was 4.0, round87's pick under the
                             # since-fixed, partly-broken MNQ data -- see module docstring). On
                             # the corrected (load_1m_mnq_reconciled) data, the walk-forward's own
                             # latest (most-current, most-data) folds pick RR=1:3, not 1:4. Single
                             # trade win at this RR is $1,155.20 (20 contracts, 10pt stop) --
                             # comfortably under the trader's real $1,650/day cap, same margin logic as
                             # round87's own derivation, just re-run on trustworthy data.
RISK_DOLLAR = 400.0         # matches the validated baseline backtest's sizing
POINT_VALUE_MNQ = 2.0       # $ per 1.0 price point, one MNQ contract (round11's POINT_VALUE["MNQ"])
COMMISSION_RT = 1.24        # $ per contract round trip (round11's COMMISSION_RT)
TICK_SIZE_MNQ = 0.25        # round11's TICK_SIZE["MNQ"]
RTH_START = dt.time(9, 30)  # round85/87's NY RTH-only filter -- see on_bar's own caveat
RTH_END = dt.time(16, 0)


class OteFvgStrategy(Strategy):
    """OTE (61.8-79% retracement) + unmitigated 15m FVG confluence, off a
    liquidity-sweep-and-reclaim impulse leg. See module docstring for
    validated numbers, provenance, and what is NOT yet done before this can
    run in Practice or live mode.
    """

    def _resample_causal(self, df1m: pd.DataFrame, rule: str) -> pd.DataFrame:
        """Bar labeled/timestamped at its CLOSE time (right-closed,
        right-labeled) -- identical to round11_fvg_bias.resample_causal."""
        o = df1m["open"].resample(rule, label="right", closed="right").first()
        h = df1m["high"].resample(rule, label="right", closed="right").max()
        l = df1m["low"].resample(rule, label="right", closed="right").min()
        c = df1m["close"].resample(rule, label="right", closed="right").last()
        return pd.DataFrame({"open": o, "high": h, "low": l, "close": c}).dropna()

    def _detect_fvgs(self, htf: pd.DataFrame) -> pd.DataFrame:
        """3-candle causal FVG, identical to round11_fvg_bias.detect_fvgs."""
        h = htf["high"].values
        l = htf["low"].values
        idx = htf.index
        n = len(htf)
        recs = []
        for i in range(2, n):
            if l[i] > h[i - 2]:
                recs.append((idx[i], 1, h[i - 2], l[i]))
            elif h[i] < l[i - 2]:
                recs.append((idx[i], -1, h[i], l[i - 2]))
        return pd.DataFrame(recs, columns=["confirm_ts", "direction", "zone_lo", "zone_hi"])

    def _detect_ote_signals(self, df1m: pd.DataFrame, fvg_zones: pd.DataFrame) -> pd.DataFrame:
        """Identical to round76_ote_pdarray_formalized.detect_ote_signals --
        see that file for the full rule-by-rule derivation. Ported verbatim."""
        lo = df1m["low"].values
        hi = df1m["high"].values
        cl = df1m["close"].values
        ts = df1m.index.values
        n = len(df1m)

        fvg_confirm = fvg_zones["confirm_ts"].values
        fvg_dir = fvg_zones["direction"].values
        fvg_lo = fvg_zones["zone_lo"].values
        fvg_hi = fvg_zones["zone_hi"].values

        def fvg_overlaps(entry_lo, entry_hi, want_dir, as_of_ts):
            mask = (fvg_confirm <= as_of_ts) & (fvg_dir == want_dir) & \
                   (fvg_lo <= entry_hi) & (fvg_hi >= entry_lo)
            return mask.any()

        signals = []
        i = K_MIN
        while i < n:
            prior_low = lo[i - K_MIN:i].min()
            prior_high = hi[i - K_MIN:i].max()
            direction = 0
            if lo[i] < prior_low and cl[i] > prior_low:
                direction = 1
                sweep_price = lo[i]
            elif hi[i] > prior_high and cl[i] < prior_high:
                direction = -1
                sweep_price = hi[i]

            if direction == 0:
                i += 1
                continue

            running_extreme = sweep_price
            locked_leg_far = None
            j = i
            invalidated = False
            while j < min(i + MAX_LOOKAHEAD_BARS, n):
                if direction == 1:
                    running_extreme = max(running_extreme, hi[j])
                    if lo[j] < sweep_price:
                        invalidated = True
                        break
                    giveback = running_extreme - cl[j]
                    if giveback >= RETRACE_LOCK_FRAC * (running_extreme - sweep_price) and \
                       (running_extreme - sweep_price) >= MIN_LEG_POINTS:
                        locked_leg_far = running_extreme
                        lock_pos = j
                        break
                else:
                    running_extreme = min(running_extreme, lo[j])
                    if hi[j] > sweep_price:
                        invalidated = True
                        break
                    giveback = cl[j] - running_extreme
                    if giveback >= RETRACE_LOCK_FRAC * (sweep_price - running_extreme) and \
                       (sweep_price - running_extreme) >= MIN_LEG_POINTS:
                        locked_leg_far = running_extreme
                        lock_pos = j
                        break
                j += 1

            if locked_leg_far is None or invalidated:
                i += 1
                continue

            leg_span = abs(locked_leg_far - sweep_price)
            if direction == 1:
                entry_lo = locked_leg_far - OTE_HI * leg_span
                entry_hi = locked_leg_far - OTE_LO * leg_span
            else:
                entry_lo = locked_leg_far + OTE_LO * leg_span
                entry_hi = locked_leg_far + OTE_HI * leg_span

            found = False
            k = lock_pos + 1
            while k < min(i + MAX_LOOKAHEAD_BARS, n - 1):
                if direction == 1 and lo[k] < sweep_price:
                    break
                if direction == -1 and hi[k] > sweep_price:
                    break
                tapped = (lo[k] <= entry_hi) and (hi[k] >= entry_lo)
                if tapped:
                    if not fvg_overlaps(entry_lo, entry_hi, direction, ts[k]):
                        k += 1
                        continue
                    if k + 1 < n:
                        reaction_ok = (cl[k + 1] > entry_lo) if direction == 1 else (cl[k + 1] < entry_hi)
                        if reaction_ok:
                            entry_px = cl[k + 1]
                            stop_px = entry_px - FIXED_STOP_POINTS if direction == 1 else entry_px + FIXED_STOP_POINTS
                            signals.append((ts[k + 1], direction, entry_px, stop_px))
                            found = True
                            break
                k += 1

            i = (k if found else j) + 1

        return pd.DataFrame(signals, columns=["ts", "direction", "entry", "stop"])

    def _size_contracts(self, stop_points: float) -> int:
        """Mirrors round76's resolve_outcomes_gated sizing exactly: fixed
        dollar risk / fixed stop distance -> whole contracts, floor of 1. Set
        explicitly on Signal.size because main.py's bracket-order path does
        NOT derive size from risk_dollars itself -- see module docstring
        point 2."""
        return max(1, int(RISK_DOLLAR // (stop_points * POINT_VALUE_MNQ)))

    def on_bar(self, bars: Any) -> Signal:
        if bars is None or len(bars) < K_MIN + 50:
            return Signal(action=SignalAction.HOLD, reason="not enough bars yet for OTE/FVG detection")

        df1m = bars.to_pandas().set_index("timestamp").sort_index()
        htf15 = self._resample_causal(df1m, "15min")
        if len(htf15) < 3:
            return Signal(action=SignalAction.HOLD, reason="not enough 15m bars yet for FVG detection")

        fvg_zones = self._detect_fvgs(htf15)
        sig_df = self._detect_ote_signals(df1m, fvg_zones)
        if sig_df.empty:
            return Signal(action=SignalAction.HOLD, reason="no OTE/FVG signal in the current window")

        latest_ts = df1m.index[-1]
        last_sig = sig_df.iloc[-1]
        if pd.Timestamp(last_sig["ts"]) != pd.Timestamp(latest_ts):
            return Signal(action=SignalAction.HOLD, reason="no fresh OTE/FVG signal on this bar")

        # NY RTH-only, added Round 87 (the trader: "you can only take trades in new
        # york time") -- the validated P(success)=77.2% figure is RTH-filtered;
        # entries outside 09:30-16:00 were never part of what was tested.
        # UNVERIFIED ASSUMPTION, flagged not silently guessed: this compares
        # the bar's own timestamp directly against RTH_START/RTH_END, which
        # assumes `bars` arrives already in NY wall-clock time (matching
        # load_1m_brokerapi's convention in the offline backtest). No existing
        # strategy in this repo does an explicit timezone conversion on live
        # bars -- confirm this assumption against a real connection before
        # trusting entries are actually RTH-gated live, not just in backtest.
        latest_time = pd.Timestamp(latest_ts).time()
        if not (RTH_START <= latest_time < RTH_END):
            return Signal(action=SignalAction.HOLD, reason=f"fresh signal outside NY RTH hours (bar time={latest_time})")

        direction = int(last_sig["direction"])
        entry_px = float(last_sig["entry"])
        stop_px = float(last_sig["stop"])
        target_dist = RR * FIXED_STOP_POINTS
        target_px = entry_px + target_dist if direction == 1 else entry_px - target_dist
        contracts = self._size_contracts(FIXED_STOP_POINTS)
        # Same fee-inclusive formula as round83's single_trade_win_dollars, so the
        # live governor's preemptive max_daily_profit check (rule 12) sees exactly
        # what the backtest was verified against, not an idealized number.
        commission = COMMISSION_RT * contracts
        slip_dollars_rt = 2 * TICK_SIZE_MNQ * POINT_VALUE_MNQ * contracts
        expected_reward = target_dist * POINT_VALUE_MNQ * contracts - commission - slip_dollars_rt

        return Signal(
            action=SignalAction.ENTER_LONG if direction == 1 else SignalAction.ENTER_SHORT,
            stop_loss_price=stop_px,
            take_profit_price=target_px,
            size=contracts,
            risk_dollars=RISK_DOLLAR,
            expected_reward_dollars=expected_reward,
            reason=(
                f"OTE/FVG sweep-reclaim (dir={direction:+d}, entry~{entry_px:.2f}, "
                f"stop={stop_px:.2f}, target={target_px:.2f}, RR=1:{RR:.0f}, "
                f"size={contracts}, expected_reward=${expected_reward:.2f})"
            ),
        )
