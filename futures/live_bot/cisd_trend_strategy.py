"""
CISD + 1H Trend Filter strategy.

STATUS (2026-09-19): NOT VALIDATED. DO NOT WIRE INTO main.py OR PAPER-TRADE.
This started as Round 9b's candidate in futures/docs/EDGE_VALIDATION_RESULTS.md
(the one result to survive walk-forward + concentration + direction checks out of 30
variants) -- but building this actual implementation and testing it against real data
surfaced a genuine lookahead bug in the original backtest: it let a swing extreme
"confirm" a signal before enough bars had passed to know it was a swing at all. The
detection logic below has been corrected to be strictly causal (see the CAUSALITY FIX
comment in _last_bar_cisd_signal), and re-running the full walk-forward validation
with this corrected, single-source-of-truth function (Round 9c) showed the edge does
NOT survive: MNQ collapses to ~$0/trade (the entire apparent edge was the bug), and
MGC's tail concentration jumps to 64-83%, the same range as two other candidates
already rejected the same day. Zero variants have survived the full audit as of this
writing (31 tested, Rounds 1-9c).

This file is kept as a correctly-implemented, tested REFERENCE for the (corrected)
CISD+1H-trend detection algorithm -- useful groundwork if a future session finds a way
to strengthen it (e.g. additional filters, a different instrument, or more history) --
but it is not an active or recommended strategy. `main.py` continues to use
`NoOpStrategy`.

Definition (cross-verified against luxalgo.com/library and innercircletrader.net,
not guessed from memory):
  1. Find a fractal swing extreme: a bar whose high/low is the strict extreme among
     itself and K bars on each side.
  2. Walk backward from that extreme along the unbroken run of same-direction closes
     leading into it.
  3. The CISD level = the OPEN of the earliest candle in that run.
  4. Confirmation = a later candle's BODY close back through that level (wicks do
     not count).
  5. Only trade in the direction the 1-hour close is on relative to its own EMA(20)
     (long CISD confirmations only when 1H is bullish, short only when bearish) --
     required per the sources' own caveat that raw CISD "lacks statistical
     reliability" without this filter.

Position sizing: fixed dollar risk per trade (validated at $100-150 in the backtest;
NOT account-equity-proportional), one trade per day maximum -- both enforced here
since Strategy.on_bar() has no access to account state to enforce them any other way
per strategy_interface.py's design (a strategy must be a pure function of bars).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd

from live_bot.strategy_interface import Signal, SignalAction, Strategy


@dataclass(frozen=True)
class CISDTrendConfig:
    swing_k: int = 4
    ema_span: int = 20
    stop_buffer_points: float = 5.0  # validated for MNQ; use e.g. 1.0 for MGC
    target_r_multiple: float = 3.0
    risk_dollars: float = 150.0  # validated buffer-safe sizing; do not raise without re-running the audit
    point_value: float = 2.0  # $/point per contract; MNQ=2.0, MGC=10.0
    max_lookforward_bars: int = 20
    displacement_body_ratio_min: float = 0.5


def _polars_bars_to_pandas(bars) -> pd.DataFrame:
    """Accepts either a Polars DataFrame (the real broker_client.get_bars() return
    type, verified 2026-09-19 via brokerapi_py source) or an already-pandas
    DataFrame (for tests), and returns a pandas DataFrame indexed by timestamp with
    lowercase open/high/low/close/volume columns."""
    if hasattr(bars, "to_pandas"):
        df = bars.to_pandas()
    else:
        df = bars.copy()
    df = df.set_index("timestamp") if "timestamp" in df.columns else df
    return df.sort_index()


def _find_swings(df: pd.DataFrame, k: int) -> tuple[np.ndarray, np.ndarray]:
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)
    swing_low = np.zeros(n, dtype=bool)
    swing_high = np.zeros(n, dtype=bool)
    for i in range(k, n - k):
        window_lo = lows[i - k:i + k + 1]
        window_hi = highs[i - k:i + k + 1]
        if lows[i] == window_lo.min() and np.argmin(window_lo) == k:
            swing_low[i] = True
        if highs[i] == window_hi.max() and np.argmax(window_hi) == k:
            swing_high[i] = True
    return swing_low, swing_high


def _last_bar_cisd_signal(df: pd.DataFrame, cfg: CISDTrendConfig) -> dict | None:
    """Checks only whether the LAST bar in df is a fresh CISD confirmation --
    i.e. whether it's the first bar to close through some earlier swing's CISD
    level within cfg.max_lookforward_bars, with no deeper extreme having formed
    in between. Returns a dict with dir/entry/extreme, or None."""
    n = len(df)
    if n < 2 * cfg.swing_k + 10:  # matches build_cisd_signals' own minimum-session-length guard exactly
        return None
    opens = df["open"].values
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    last_i = n - 1

    # CAUSALITY FIX (found 2026-09-19 while building this live implementation --
    # the original backtest script had this bug too, and was corrected and
    # re-validated alongside this fix; see EDGE_VALIDATION_RESULTS.md Round 9c):
    # a swing at index i (needing k bars on each side) is not actually KNOWABLE
    # until bar i+k has closed. The original logic scanned for confirmation
    # starting at i+1, which lets a bar "confirm" a swing before enough time has
    # passed to know it was a swing at all -- lookahead bias. _find_swings is
    # still run on the full available data through last_i (safe: it only ever
    # marks index i as a swing once bars through i+k already exist, i.e. i <=
    # last_i - k, by construction of its own i in range(k, n-k) loop), but the
    # confirmation scan below must not start earlier than i+cfg.swing_k.
    swing_low, swing_high = _find_swings(df, cfg.swing_k)
    lo_bound = max(cfg.swing_k, last_i - cfg.max_lookforward_bars)
    hi_bound = last_i - cfg.swing_k

    for i in range(lo_bound, hi_bound + 1):
        if i >= len(swing_low):
            continue
        if swing_low[i]:
            j = i
            while j - 1 >= 0 and closes[j - 1] < opens[j - 1]:
                j -= 1
            if j != i:
                level = opens[j]
                extreme = lows[i]
                start_m = i + cfg.swing_k  # earliest bar at which this swing is actually knowable
                for m in range(start_m, last_i + 1):
                    if closes[m] > level:
                        if m != last_i:
                            break  # already confirmed on an earlier bar -- not fresh as of now
                        if cfg.displacement_body_ratio_min > 0:
                            body = abs(closes[m] - opens[m])
                            rng = highs[m] - lows[m]
                            if rng == 0 or body / rng < cfg.displacement_body_ratio_min:
                                break
                        return {"dir": 1, "entry": closes[m], "extreme": extreme}
                    if lows[m] < extreme:
                        break  # invalidated by a deeper low before confirming

        if swing_high[i]:
            j = i
            while j - 1 >= 0 and closes[j - 1] > opens[j - 1]:
                j -= 1
            if j != i:
                level = opens[j]
                extreme = highs[i]
                start_m = i + cfg.swing_k
                for m in range(start_m, last_i + 1):
                    if closes[m] < level:
                        if m != last_i:
                            break
                        if cfg.displacement_body_ratio_min > 0:
                            body = abs(closes[m] - opens[m])
                            rng = highs[m] - lows[m]
                            if rng == 0 or body / rng < cfg.displacement_body_ratio_min:
                                break
                        return {"dir": -1, "entry": closes[m], "extreme": extreme}
                    if highs[m] > extreme:
                        break
    return None


def _htf_bias(df: pd.DataFrame, ema_span: int) -> int | None:
    """1H trend bias as of the most recently CLOSED 1H bar strictly before the
    last 5m bar's timestamp. Returns +1 bullish, -1 bearish, or None if not
    enough 1H history yet."""
    h1 = df["close"].resample("1h").last().dropna()
    if len(h1) < ema_span + 1:
        return None
    ema = h1.ewm(span=ema_span, adjust=False).mean()
    last_ts = df.index[-1]
    idx = h1.index.searchsorted(last_ts, side="right") - 1
    if idx < 0:
        return None
    return 1 if h1.iloc[idx] > ema.iloc[idx] else -1


class CISDTrendStrategy(Strategy):
    """See module docstring. Emits at most one signal per calendar day (tracked
    internally) to match the one-trade/day cap the backtest was validated under --
    this is enforced here, not by main.py/risk_governor, since it's a property of
    this specific strategy's validated methodology, not a universal account rule."""

    def __init__(self, config: CISDTrendConfig | None = None) -> None:
        self.config = config or CISDTrendConfig()
        self._last_trade_date: dt.date | None = None

    def on_bar(self, bars) -> Signal:
        df_full = _polars_bars_to_pandas(bars)
        if df_full.empty:
            return Signal(action=SignalAction.HOLD, reason="no bars yet")

        last_date = df_full.index[-1].date()
        if self._last_trade_date == last_date:
            return Signal(action=SignalAction.HOLD, reason="already traded today (1/day cap)")

        # CRITICAL: the validated backtest (build_cisd_signals in the Round 9b script)
        # detects swings/runs/confirmations within EACH TRADING DAY'S OWN SESSION
        # SLICE independently -- it never treats yesterday's 16:00 bar and today's
        # 09:30 bar as adjacent. df_full is a rolling multi-day window, so it must be
        # sliced down to just today's session before running the same detection,
        # or the fractal-swing indices silently span session boundaries and produce
        # different (wrong) results than the backtest that was actually validated.
        df = df_full[df_full.index.date == last_date]

        sig = _last_bar_cisd_signal(df, self.config)
        if sig is None:
            return Signal(action=SignalAction.HOLD, reason="no CISD confirmation on last bar")

        bias = _htf_bias(df_full, self.config.ema_span)  # HTF trend uses the FULL rolling window, not the session slice
        if bias is None:
            return Signal(action=SignalAction.HOLD, reason="insufficient 1H history for trend filter")
        if sig["dir"] != bias:
            return Signal(action=SignalAction.HOLD,
                           reason=f"CISD dir={sig['dir']} conflicts with 1H bias={bias}, filtered out")

        entry = sig["entry"]
        extreme = sig["extreme"]
        direction = sig["dir"]
        stop_price = extreme - direction * self.config.stop_buffer_points
        risk_pts = abs(entry - stop_price)
        if risk_pts <= 0:
            return Signal(action=SignalAction.HOLD, reason="degenerate risk_pts, skipping")
        target_price = entry + direction * risk_pts * self.config.target_r_multiple
        qty = max(1, round(self.config.risk_dollars / (risk_pts * self.config.point_value)))

        self._last_trade_date = last_date
        action = SignalAction.ENTER_LONG if direction == 1 else SignalAction.ENTER_SHORT
        return Signal(
            action=action,
            stop_loss_price=stop_price,
            take_profit_price=target_price,
            size=qty,
            reason=f"CISD+1H confirmed: dir={direction} entry={entry:.2f} extreme={extreme:.2f} "
                   f"stop={stop_price:.2f} target={target_price:.2f} qty={qty}",
        )
