"""Combined filtered-POC + unfiltered-VA (Rounds 198-199), the uncapped variant.

`disciplined_bracket_strategy.py` caps each day's win; this file runs the same two legs
with no win cap. The choice is made with `BOT_STRATEGY` (`disciplined_bracket` or
`combined`), an explicit setting, never auto-detected; see main.py's `_select_strategy()`
for the dispatch.

Two legs, checked in order (same single-leg-at-a-time adaptation as
`disciplined_bracket_strategy.py`, for the same reason: `live_bot`'s
one-position-at-a-time safety gate wasn't weakened to hold two concurrent
legs without review -- Round 199's own real backtest nets both legs on the
same day, which this file does NOT reproduce; a real, disclosed deviation,
matching the capped strategy's own):
  - Meta-labeled POC reversion (Round 198): the same POC-reversion entry as
    the capped strategy, but filtered by a logistic-regression model
    that predicts whether THIS SPECIFIC trade wins, from 6 causal features
    (signal strength, 20-day range, day-of-week, month, recent range
    change, trailing 20-trade win rate of this same signal). Only taken if
    the model's predicted win probability clears a fixed threshold.
  - Unfiltered VA rejection (Round 184, `continuation=False`): meta-
    labeling was found NOT to help this leg (Round 199: OOS AUC ~0.510,
    filtering makes it worse) -- taken unfiltered whenever it fires and
    POC-reversion didn't.

THE MODEL IS PRE-TRAINED AND SERIALIZED, not trained live. `poc_meta_model.json`
(shipped alongside this file) holds a StandardScaler's mean/scale and a
LogisticRegression's coefficients/intercept/threshold, retrained 2026-09-29
from the exact same real data and method as `round198_meta_labeling_poc.py`
-- with one real, deliberate fix: that script's own top-33%-confidence
threshold was computed from the OOS TEST SET'S OWN prediction distribution,
which is not knowable live, in real time, before those future trades
happen (look-ahead). This model's threshold is instead the IS (training)
set's own top-33% quantile -- fully known before any live trade, and
verified to preserve nearly the same real filter effect on the actual OOS
data (43.3% win rate / $287.63 mean vs the original's 43.3%/$287... -- see
the 2026-09-29 journal entry for the full reproduction). `live_bot/` does
not import from `futures/` (this repo's own stated convention,
see `ote_fvg_strategy.py`'s docstring) -- the linear model (scaler + logit,
both simple enough to hand-implement with no sklearn dependency at
inference time) is applied directly from the serialized JSON, no runtime
training or scikit-learn import needed here.

TRAIL_WINRATE IS RECONSTRUCTED FRESH FROM BARS EACH CALL, same "pure
function of bars" design as the capped strategy's 2026-09-29 rebuild
(no cross-call state to lose on a restart) -- walks every prior completed
session in the bars window, replays which ones would have fired a
POC-reversion signal and whether that trade would have won or lost
(causal, bar-by-bar, same stop/target-first-touch resolution as
`idea_harness.resolve_bracket`), and takes the most recent WIN_TRAIL
outcomes' win rate. Needs a genuinely large bars window (POC-reversion
fires most days, so ~20 trade outcomes span roughly a month of real
sessions, similar order of magnitude to the capped strategy's own
BOT_INITIAL_DAYS=30) -- if the window doesn't contain enough reconstructed
trade history, this strategy holds rather than guess (same fail-safe
philosophy as the capped strategy's "no verified prior session, no
trade" rule).

STATUS 2026-09-29: built and wired into main.py (`BOT_STRATEGY=combined`),
not yet forward-tested against a real live connection. This account has not
been switched to the uncapped variant yet -- see the disciplined bracket notes.
Do not switch `BOT_STRATEGY` from `disciplined_bracket` to `combined`
until you decide to switch to the uncapped variant.

TWO REAL BUGS CAUGHT AND FIXED before this file was trusted, both the same
class of mistake that already bit `disciplined_bracket_strategy.py` once
this same session (the trader: "cant have days below -1000$ or above 1650$" --
the investigation that led to this file's own creation):
1. `_resolve_day_outcome`'s stop-hit/target-hit branches returned `sl - entry`
   / `tp - entry` directly, correct only for long trades -- short trades got
   every outcome inverted. Caught by diffing this file's reconstructed
   trail_winrate against `round198_meta_labeling_poc.py`'s own real reference
   sequence for trades before 2025-07-18 (this file said win rate 0.60,
   the reference says 0.25) -- traced day-by-day to 11 of 20 flipped
   outcomes, all shorts. Fixed by multiplying every branch by `direction`.
2. `range_chg` compared two 20-day rolling AVERAGES of daily range; the
   trained model's `range_chg` feature is `ranges.pct_change(RANGE_WINDOW)
   .shift(1)` -- a single day's range vs. the range exactly RANGE_WINDOW
   sessions earlier, not an average-vs-average. Caught the same way: this
   file's live-reconstructed feature vector for 2025-07-18 (p=0.42) didn't
   match round198's own reference feature row and model prediction for that
   real trade (p_ref=0.3920) even after bug 1 was fixed. Re-derived the
   correct two-point formula directly from round198's own pandas call and
   verified it reproduces the reference range_chg (0.564899) exactly on the
   same real data.
Re-verified after both fixes across 8 real dates spanning six months
(2025-07 through 2026-01): every date where round198's reference prediction
clears the 0.3501 threshold matches this file's own `on_bar()` output almost
exactly (0.38/0.38, 0.39/0.39, 0.38/0.38), and every date below threshold
correctly falls through to unfiltered VA-rejection or no trade, matching the
meta-labeling filter's intended behavior. Neither bug was ever live -- caught
during this file's own construction, before any real deployment.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import os
from typing import Any

import numpy as np
import pandas as pd

from live_bot.strategy_interface import Signal, SignalAction, Strategy

RISK_PER_TRADE = float(os.getenv("BRACKET_RISK_PER_TRADE", "300.0"))
MAX_CONTRACTS = int(os.getenv("BRACKET_MAX_CONTRACTS", "50"))
POINT_VALUE_MNQ = 2.0
TICK_MNQ = 0.25
STOP_MULT = 0.15
RANGE_WINDOW = 20
RANGE_MIN_PERIODS = 10
VA_PCT = 0.70
WIN_TRAIL = 20
ENTRY_GRACE_MINUTES = 15.0
RTH_START = dt.time(9, 30)
RTH_END = dt.time(16, 0)

_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "poc_meta_model.json")


def _load_model() -> dict:
    with open(_MODEL_PATH) as f:
        return json.load(f)


def _session_profile(day_df: pd.DataFrame) -> tuple[float, float, float, float] | None:
    """Identical to disciplined_bracket_strategy.py's own function -- kept
    duplicated, not imported, matching this repo's established
    self-containment convention for live_bot strategy files (see
    ote_fvg_strategy.py's docstring)."""
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


def _resolve_day_outcome(day_df: pd.DataFrame, direction: int, entry: float, sl: float, tp: float) -> float:
    """Causal, bar-by-bar: does this leg's stop or target get touched first
    today, else flat at the close. Same convention as
    idea_harness.resolve_bracket (stop wins a same-bar tie).

    REAL BUG CAUGHT BEFORE DEPLOYMENT 2026-09-29: the first version of this
    function returned `sl - entry` / `tp - entry` directly in the stop-hit
    and target-hit branches, without multiplying by `direction` -- correct
    for longs (sl < entry, tp > entry, so the sign already comes out
    right), but wrong for shorts (sl > entry, tp < entry -- a short's own
    stop-out came out POSITIVE and its own target-hit came out NEGATIVE,
    exactly inverted). Caught via parity check against round198's own
    real trail_winrate sequence before this file was ever wired in or run
    live -- diffing 20 real reconstructed trade dates against
    round198_meta_labeling_poc.py's own dataframe found 11 of 20 outcomes
    flipped, all on short trades. This is the second time this exact sign
    pattern has bitten a freshly-written P&L function in this session
    (see disciplined_bracket_strategy.py's day-cap check, 2026-09-29) --
    now written the one way that can't get the sign wrong: `direction x
    (exit_price - entry)` uniformly, matching the already-correct fallback
    branch below, rather than hand-writing the sign per case."""
    hi, lo, cl = day_df["high"].values, day_df["low"].values, day_df["close"].values
    for i in range(len(day_df)):
        if direction == 1:
            if lo[i] <= sl:
                return direction * (sl - entry)
            if hi[i] >= tp:
                return direction * (tp - entry)
        else:
            if hi[i] >= sl:
                return direction * (sl - entry)
            if lo[i] <= tp:
                return direction * (tp - entry)
    return direction * (cl[-1] - entry)


class CombinedStrategy(Strategy):
    """See module docstring: live-stage only, uncapped, meta-labeled POC
    + unfiltered VA, single leg at a time."""

    def __init__(self, history_source: str | None = None) -> None:
        self._model = _load_model()
        self._entered_today = False
        self._entered_date: dt.date | None = None
        # "cache" (default when the seed exists) = live_bot/session_history.py;
        # "bars" = the original rebuild-everything-from-the-bars-window path.
        source = (history_source or os.getenv("COMBINED_HISTORY_SOURCE", "cache")).strip().lower()
        self._history = None
        if source == "cache":
            from live_bot.session_history import SessionHistory
            h = SessionHistory()
            self._history = h if h.available else None

    def _model_predict(self, features: dict[str, float]) -> float:
        m = self._model
        x = np.array([features[c] for c in m["feature_order"]], dtype=float)
        z = (x - np.array(m["scaler_mean"])) / np.array(m["scaler_scale"])
        logit = float(np.dot(z, m["coef"]) + m["intercept"])
        return 1.0 / (1.0 + math.exp(-logit))

    def _size(self, direction: int, entry: float, sl: float, tp: float) -> tuple[int, float]:
        """Same $300-risk convention as the capped strategy, but no
        take-profit cap -- live-stage, uncapped by design."""
        dist_stop = abs(entry - sl)
        contracts = max(1, min(int(RISK_PER_TRADE // (dist_stop * POINT_VALUE_MNQ)), MAX_CONTRACTS))
        reward = abs(tp - entry) * POINT_VALUE_MNQ * contracts
        return contracts, reward

    def on_bar(self, bars: Any) -> Signal:
        if bars is None or len(bars) == 0:
            return Signal(action=SignalAction.HOLD, reason="no bars yet")

        df = bars.to_pandas().set_index("timestamp").sort_index()
        # Same fix as disciplined_bracket_strategy.py (2026-09-30): live bars arrive
        # tz-aware in Central time; RTH_START/RTH_END, the entry grace window and every
        # session profile are New York wall-clock. Naive timestamps are assumed NY.
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

        if self._history is not None:
            # History cache (2026-09-30, live_bot/session_history.py): the broker's feed
            # holds ~22 sessions, which reconstructs only 3-9 of the 20 POC trades
            # trail_winrate needs. The cache holds every session from the Databento seed
            # onward, built with this module's own functions, plus completed live sessions.
            self._history.update_from_bars(rth, today)
            hist = self._history.before(today)
            if len(hist) < RANGE_MIN_PERIODS + 1:
                return Signal(action=SignalAction.HOLD, reason=f"only {len(hist)} sessions in the history cache")
            ordered_dates = list(hist["date"])
            profiles = {r.date: (float(r.range), float(r.poc), float(r.val), float(r.vah)) for r in hist.itertuples(index=False)}
            poc_outcomes = [int(x) for x in hist["poc_outcome"].dropna()]
        else:
            ordered_dates, profiles, poc_outcomes, hold = self._inputs_from_bars(rth, today)
            if hold is not None:
                return hold
        return self._decide(rth, today, latest_time, ordered_dates, profiles, poc_outcomes)

    def _inputs_from_bars(self, rth: pd.DataFrame, today: dt.date):
        """The original, bars-only reconstruction (used when no history cache exists)."""
        dates_present = sorted(set(rth.index.date))
        prior_dates = [d for d in dates_present if d < today]
        if len(prior_dates) < RANGE_MIN_PERIODS + 1:
            return None, None, None, Signal(
                action=SignalAction.HOLD,
                reason=f"only {len(prior_dates)} prior sessions in the bars window -- "
                       f"need at least {RANGE_MIN_PERIODS + 1} to reconstruct trail_winrate "
                       f"(check BOT_INITIAL_DAYS/bars_needed)",
            )

        # Compute every prior session's own profile fresh from real bars.
        profiles: dict[dt.date, tuple[float, float, float, float]] = {}
        for d in prior_dates:
            prof = _session_profile(rth[rth.index.date == d])
            if prof is not None:
                profiles[d] = prof
        ordered_dates = sorted(profiles.keys())
        if len(ordered_dates) < RANGE_MIN_PERIODS + 1:
            return None, None, None, Signal(action=SignalAction.HOLD, reason="not enough usable prior-session profiles yet")

        # Reconstruct the real POC-reversion trade sequence across the window,
        # to get trail_winrate -- causal, using only each day's own prior-day
        # profile and range history, exactly as it would have been live.
        poc_outcomes: list[int] = []  # 1 = win, 0 = loss, chronological
        for i in range(RANGE_MIN_PERIODS, len(ordered_dates)):
            d = ordered_dates[i]
            hist = ordered_dates[max(0, i - RANGE_WINDOW):i]
            if len(hist) < RANGE_MIN_PERIODS:
                continue
            S_hist = float(np.mean([profiles[h][0] for h in hist]))
            prev_d = ordered_dates[i - 1]
            prev_poc_hist = profiles[prev_d][1]
            day_df = rth[rth.index.date == d]
            if day_df.empty or not (S_hist > 0):
                continue
            open_px = float(day_df.iloc[0]["open"])
            dist = prev_poc_hist - open_px
            if abs(dist) < STOP_MULT * S_hist:
                continue
            direction = 1 if dist > 0 else -1
            sl = open_px - direction * STOP_MULT * S_hist
            pnl_pts = _resolve_day_outcome(day_df, direction, open_px, sl, prev_poc_hist)
            poc_outcomes.append(1 if pnl_pts > 0 else 0)
        return ordered_dates, profiles, poc_outcomes, None

    def _decide(self, rth: pd.DataFrame, today: dt.date, latest_time: dt.time,
                ordered_dates: list, profiles: dict, poc_outcomes: list) -> Signal:
        """Everything after the history inputs: unchanged decision logic."""
        if len(poc_outcomes) < WIN_TRAIL:
            return Signal(
                action=SignalAction.HOLD,
                reason=f"only {len(poc_outcomes)} reconstructed POC-reversion trades in window, "
                       f"need {WIN_TRAIL} for trail_winrate",
            )
        trail_winrate = float(np.mean(poc_outcomes[-WIN_TRAIL:]))

        yesterday = ordered_dates[-1]
        _, prev_poc, prev_val, prev_vah = profiles[yesterday]
        range_hist_now = [profiles[d][0] for d in ordered_dates[-RANGE_WINDOW:]]
        S = float(np.mean(range_hist_now))
        # Matches round198_meta_labeling_poc.py's own feature exactly: a single day's
        # range vs. the range RANGE_WINDOW sessions earlier (ranges.pct_change(20).shift(1)),
        # NOT a comparison of two rolling averages -- an earlier version of this function
        # computed the average-vs-average version, which silently fed the live model
        # features it was never trained on. Caught by diffing against round198's own
        # reference feature row for a real trade (2025-07-18): reference range_chg=0.564899,
        # the average-vs-average version gave a different number for the same real day.
        range_21_before = ordered_dates[-1 - RANGE_WINDOW] if len(ordered_dates) > RANGE_WINDOW else None
        range_chg = (
            profiles[yesterday][0] / profiles[range_21_before][0] - 1.0
            if range_21_before and profiles[range_21_before][0]
            else 0.0
        )

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
        leg_name, sig = None, None

        if S > 0:
            dist = prev_poc - open_px
            if abs(dist) >= STOP_MULT * S:
                direction = 1 if dist > 0 else -1
                sl = open_px - direction * STOP_MULT * S
                features = dict(
                    strength=abs(dist) / S, S=S, dow=float(today.weekday()),
                    month=float(today.month), range_chg=range_chg, trail_winrate=trail_winrate,
                )
                p_win = self._model_predict(features)
                if p_win >= self._model["threshold"]:
                    leg_name = f"POC-reversion (meta-labeled, p={p_win:.2f})"
                    sig = (direction, sl, prev_poc)

        if sig is None:
            va_width = prev_vah - prev_val
            if va_width > 0:
                if open_px > prev_vah:
                    leg_name = "VA-rejection (unfiltered)"
                    sig = (-1, open_px + (open_px - prev_vah), prev_poc)
                elif open_px < prev_val:
                    leg_name = "VA-rejection (unfiltered)"
                    sig = (1, open_px - (prev_val - open_px), prev_poc)

        if sig is None:
            return Signal(action=SignalAction.HOLD, reason=f"neither leg fired/qualified (open={open_px:.2f})")

        direction, sl, tp = sig
        contracts, reward = self._size(direction, open_px, sl, tp)
        sl_rounded = round(sl / TICK_MNQ) * TICK_MNQ
        tp_rounded = round(tp / TICK_MNQ) * TICK_MNQ

        self._entered_today = True
        action = SignalAction.ENTER_LONG if direction == 1 else SignalAction.ENTER_SHORT
        return Signal(
            action=action,
            stop_loss_price=sl_rounded,
            take_profit_price=tp_rounded,
            size=contracts,
            risk_dollars=RISK_PER_TRADE,
            expected_reward_dollars=reward,
            entry_reference_price=open_px,
            reason=(
                f"[{leg_name}] open={open_px:.2f} POC={prev_poc:.2f} "
                f"VAL={prev_val} VAH={prev_vah} sl={sl_rounded:.2f} tp={tp_rounded:.2f} "
                f"contracts={contracts} reward=${reward:.0f} trail_winrate={trail_winrate:.2f} "
                f"(yesterday={yesterday}, {len(range_hist_now)} sessions range history, "
                f"{len(poc_outcomes)} reconstructed trades)"
            ),
        )
