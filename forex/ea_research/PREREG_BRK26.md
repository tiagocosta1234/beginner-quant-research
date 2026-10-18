# PREREG BRK26 - 26 more new breakout concepts (named indicators and price-action patterns) on the 38 MT5 broker

Registered 2026-10-18 19:18 local (local clock, second PC PC-2), before any P&L of these ideas was computed.
the trader (/goal): "keep testing untested breakout ideas, atleast 100 more". BRK100 tested 100 (79 new concepts + 21 out-of-sample
market extensions); this batch adds 26 NEW concepts so the new concepts alone pass 100 (79 + 26 = 105).
**Untested, checked by a repo-wide search before writing:** no earlier test of TRIX, Vortex, Chande momentum oscillator (CMO),
Ultimate Oscillator, Fisher transform, Mass Index, DPO, KST, Elder Ray, Hull MA, TEMA, Williams %R, StochRSI, Awesome Oscillator,
DeMark TD setup / TDST, Ichimoku kumo twist, Chaikin volatility, regression slope turns, Schaff Trend Cycle, RVI, Balance of Power,
inside-outside-inside days, three-bar reversals, marubozu bars or Al Brooks' High 2 (the hits were "matrix", "chandelier", Chaikin
money FLOW). Engulfing candles WERE tested (Broker-era round 222) and are left out. One family of FIXED rules, Bonferroni for 26.
**Pre-registration evidence (no commits on 18 Oct):** SHA-256 and time in `C:\work\scratch\brk26_prereg.sha256` before any P&L.

## Common rules
Exactly BRK30's: `brk50.Mkt` fills / rollover ban / mirror / R; H1 / H4 server-grid bars from minute mids (open = first mid);
**BC** = bar-close signal, entry at the next minute, H1 stop 1.5 ATR14 / exit 24 bars, H4 stop 2 ATR14 / exit 30 bars, one position
at a time; **BS** = stop order at the stated level for the stated bars; D-NEXT = market order at 08:00 local the next day; DL =
stop orders 08:00-18:59 local, stop 0.5 ATR, exit 20:45. Universe ALL = the 38 non-crypto markets, pooled.

## The 26 ideas
- P01 TRIX(15) ZERO CROSS H4: TRIX (rate of change of the triple-smoothed EMA) crosses above 0 -> BC long; below -> short.
- P02 TRIX SIGNAL CROSS H1: TRIX crosses above its 9-EMA signal while above 0 -> BC long; below while below 0 -> short.
- P03 VORTEX(14) CROSS H4: VI+ crosses above VI- -> BC long; below -> short.
- P04 CMO(14) +/-50 H1: Chande momentum crosses above +50 -> BC long; below -50 -> short.
- P05 ULTIMATE OSCILLATOR (7, 14, 28) H4: crosses above 70 -> BC long; below 30 -> short.
- P06 FISHER TRANSFORM(10) H4: the Fisher line crosses above its 1-bar trigger after a reading below -1.5 -> BC long; mirror above +1.5.
- P07 MASS INDEX REVERSAL BULGE H4: the 25-bar Mass Index (9-EMA of the range over its 9-EMA) above 27 within the last 10 bars and
  now crossing below 26.5 -> BC in the direction of the 9-EMA slope of closes.
- P08 DPO(20) ZERO CROSS D1: close minus the 20-day SMA of 11 days earlier crosses 0 -> D-NEXT, stop 1 ATR, exit 20:45 on the 5th day.
- P09 KST SIGNAL CROSS D1: KST (ROC 10 / 15 / 20 / 30 smoothed 10 / 10 / 10 / 15, weights 1-4) crosses its 9-day SMA -> D-NEXT,
  stop 1.5 ATR, exit 20:45 on the 10th day.
- P10 ELDER RAY H4: EMA13 rising, bull power (high - EMA13) > 0 and rising -> buy stop at the bar's high for the next bar, stop 2
  ATR14, exit 30 bars after the fill; mirror with bear power.
- P11 HULL MA(55) TURN H4: the Hull MA turns up (rises after falling) -> BC long; turns down -> short.
- P12 TEMA(20) CROSS H1: close crosses above the triple EMA -> BC long; below -> short.
- P13 WILLIAMS %R(14) BURST H1: %R crosses above -20 with a reading below -80 in the previous 5 bars -> BC long; mirror.
- P14 STOCHRSI(14, 14) BURST H1: %K (3-smoothed) crosses above 80 with a reading below 20 in the previous 10 bars -> BC long; mirror.
- P15 AWESOME OSCILLATOR ZERO CROSS H4: SMA5 - SMA34 of median prices crosses 0 -> BC in the crossing direction.
- P16 DeMARK TDST BREAK D1: a completed TD buy setup (9 consecutive closes below the close 4 days earlier) -> TDST = the highest high
  of the 9 days; a buy stop at TDST on each of the next 10 trading days (08:00-18:59 local) until filled, stop 1 ATR, exit 20:45 on
  the 5th trading day after the fill; mirror for sell setups (TDST = the lowest low).
- P17 ICHIMOKU KUMO TWIST H4: the unshifted span A crosses above span B (the cloud ahead turns bullish) with the close above the
  current cloud -> BC long; mirror.
- P18 CHAIKIN VOLATILITY EXPANSION H4: Chaikin volatility (10, 10) crosses above +50% on a bar closing in its top (bottom) quarter
  -> BC in that direction.
- P19 REGRESSION SLOPE TURN H4: the 20-bar least-squares slope of closes turns positive -> BC long; negative -> short.
- P20 SCHAFF TREND CYCLE (23, 50, 10) H4: STC crosses above 25 -> BC long; below 75 -> short.
- P21 RVI(10) SIGNAL CROSS H4: the Relative Vigor Index crosses above its 4-bar weighted signal -> BC long; below -> short.
- P22 BALANCE OF POWER H4: the 14-bar SMA of (close - open) / (high - low) crosses above +0.2 -> BC long; below -0.2 -> short.
- P23 INSIDE-OUTSIDE-INSIDE D1: an inside day, an outside day, then an inside day -> DL stop orders at yesterday's high and low.
- P24 THREE-BAR REVERSAL H4: a down bar, a bar with a lower low, then an up bar closing above the first bar's high -> BC long; mirror.
- P25 MARUBOZU CONTINUATION H4: a bar with body >= 90% of its range and range >= ATR14 -> a stop order at its far end (high for a
  bullish body) for the next 2 bars, stop at its other end, exit 30 bars after the fill.
- P26 AL BROOKS HIGH 2 H1: close above a rising EMA20; after a pullback (lower highs) the second bar whose high exceeds the previous
  bar's high while below the swing high -> buy stop at that bar's high for the next bar, stop at the pullback low, exit 24 bars after
  the fill; mirror (Low 2 below a falling EMA20).

## Periods, acceptance, dry run
DEV 2022-24 / VAL 2025 / HOLD 2026 (one look, passers only). DEV: n >= 150; mean > 0 with day-clustered t >= 2.89 (Bonferroni, 26
one-sided tests); >= 2 of 3 years positive; information over the mirror t >= 2.0. VAL: mean > 0, t >= 1.65. HOLD: mean > 0, t >= 1.65.
Account environment for the 5 best and any passer (universe at $50 a trade, at most 5 a day, from 95,472, MT5 broker rules). Dry run:
counts, truncation test (EURUSD, XAUUSD, NSDQ), hand checks.

## Honest prior
About 0 passes: these are the same kind of bar-close indicator signals as BRK30 (DEV t mean -1.6) and BRK100's named systems.
