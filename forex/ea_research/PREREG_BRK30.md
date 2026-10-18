# PREREG BRK30 - 30 untouched breakout ideas on the MT5 broker, tested in one round

Registered 2026-10-18 17:42 local (local clock, second PC PC-2), before any P&L of these ideas was computed.
the trader (18 Oct, after BRK50B): "quick resume on everything that has worked and then keep testing untouched breakout ideas".

**Window note.** the trader's 40-variant window closed with GN13 and he asked for more batches; like BRK50 / BRK50B this is one
pre-registered family of FIXED rules (no tuning, no variants), judged with a Bonferroni bar for its 30 tests.
**Untouched, checked against the repo before writing:** excluded are everything in `PREREG_BRK50.md` (its 54 ideas and ~45 closed
families), BRK50B's 50, GN1-GN13, BRK_PATTERNS (triangles, wedges, trendlines, head and shoulders, Darvas, VCP), the ICT rounds,
UT Bot / ATR-trailing flips (so Supertrend, Heikin-Ashi and Parabolic SAR flips), GOTOBI, EIA_OIL, FX3_OPEN (equity-session
leads for FX), the basket / USD-index rounds, weekly-open levels (EDGE_VALIDATION), Turtle 55 (FINCEPT_mt5), Reversal Signal
Detector (RSI / MACD divergence). A repo-wide search found no test of: double / triple tops and bottoms, broadening formations,
Ichimoku, Aroon, MACD zero / signal crosses, CCI, regression channels, EMA crosses, golden crosses, choppiness, KAMA, Elder's
Triple Screen, Bill Williams fractals / Alligator, copper / gold / VIX / rate leads for FX, OPEX-Friday pinning, quarter-end flows.
**Pre-registration evidence (still no commits on 18 Oct):** the SHA-256 of this file and the time go to
`C:\work\scratch\brk30_prereg.sha256` before any P&L; the file is committed unchanged later.

## Common rules
- Data, clock, daily H / L / C / ATR, fills, rollover ban, mirror trade and R exactly as BRK50 / BRK50B (`brk50.Mkt`).
- Universe ALL = the 38 non-crypto MT5 broker (`brk50.NONC`), pooled per idea; gold (XAUUSD) and Nasdaq (NSDQ) reported apart.
- Bars: H1 / H4 on the server-hour grid from minute mids (open = first mid, high / low = mid extremes, close = last mid).
  ATR14 = 14-bar mean true range of those bars.
- **Bar-close signal (BC):** at the close of the signal bar, enter at the next minute's open (ask / bid; skipped in the rollover
  window); stop k x ATR14 of the bars (H1 k = 1.5, H4 k = 2); exit at the start of the bar N bars after the signal bar (H1 N = 24,
  H4 N = 30; moved out of the rollover window as BRK50); one position per idea and market at a time.
- **Bar stop order (BS):** a stop order at the stated level, live for the stated number of following bars, first touch, stop and
  exit as stated.
- **Daily entries:** D-NEXT = market order at 08:00 LIS of the next trading day; DL = BRK50B's daily-level rule (stop orders
  08:00-18:59 LIS, stop 0.5 ATR, exit 20:45 LIS).
- **London box (LB):** 08:00-08:29 LIS bid high / low, stop orders 08:30-10:59 LIS, stop at the other side, exit 17:00 LIS.
  **New York box (NB):** 09:30-09:59 NY, orders 10:00-11:59 NY, stop at the other side, exit 15:55 NY.
- Swing points: a pivot low (high) is a bar whose low (high) is the extreme of the 7 bars centred on it; it is known 3 bars later.

## The 30 ideas
PATTERNS
- K01 DOUBLE BOTTOM / TOP H1, ALL: two consecutive pivot lows 5-40 bars apart within 0.25 ATR14 of each other; when the second
  is known, a buy stop at the highest high between them (the neckline) for 12 bars; stop at the lower low; exit 24 bars after the
  fill. Mirror for tops.
- K02 DOUBLE BOTTOM / TOP H4, ALL: the same on H4; orders for 6 bars; exit 30 bars after the fill.
- K03 TRIPLE BOTTOM / TOP H4, ALL: three consecutive pivot lows within 0.3 ATR14 of each other, spanning <= 60 bars; buy stop at
  the highest high since the first for 6 bars; stop at the lowest of the three; exit 30 bars after the fill. Mirror.
- K04 BROADENING FORMATION H4, ALL: the last two pivot highs rising and the last two pivot lows falling; if the latest pivot is a
  low, a buy stop at the latest pivot high for 6 bars, stop at the latest low; if a high, the mirror; exit 30 bars after the fill.
- K05 MORNING / EVENING STAR D1, ALL: day -3 a bearish body > 0.6 of its range with range > 0.8 ATR, day -2 a body < 0.25 of day
  -3's with its midpoint below day -3's close, yesterday bullish closing above the middle of day -3's body -> DL buy stop at
  yesterday's high; mirror.
INDICATORS (BC unless noted)
- K06 ICHIMOKU KUMO BREAK H4, ALL: close crosses above the cloud top (max of span A / B, both shifted 26) with Tenkan(9) > Kijun(26)
  -> long; below the cloud bottom with Tenkan < Kijun -> short.
- K07 ICHIMOKU KUMO BREAK D1, ALL: the same on daily bars; D-NEXT; stop 1 ATR; exit 20:45 on the 10th trading day.
- K08 ICHIMOKU TK CROSS ABOVE THE CLOUD H4, ALL: Tenkan crosses above Kijun while the close is above the cloud -> long; mirror.
- K09 MACD ZERO CROSS H4, ALL: MACD(12, 26) crosses above 0 with histogram (MACD - signal 9) > 0 -> long; mirror.
- K10 MACD SIGNAL CROSS ABOVE ZERO H1, ALL: MACD crosses above its signal line with both above 0 -> long; mirror below 0.
- K11 RSI MOMENTUM BURST H1, ALL: RSI(14) closes above 60 within 10 bars of a close below 40 -> long; mirror.
- K12 ADX TREND BIRTH H4, ALL: ADX(14) crosses above 25 with +DI > -DI -> long; with -DI > +DI -> short.
- K13 AROON CROSS H4, ALL: Aroon-up(25) crosses above 70 while Aroon-down < 30 -> long; mirror.
- K14 CCI +/-100 D1 (Lambert), ALL: CCI(20) crosses above +100 -> D-NEXT long; below -100 -> short; stop 1 ATR; exit 20:45 on the
  5th trading day.
- K15 CCI +/-100 H4, ALL: the same signal on H4 bars.
- K16 REGRESSION-CHANNEL BREAK H1, ALL: least-squares line of the last 100 closes; a close above line + 2 residual SD (the
  previous close inside) -> long; mirror.
- K17 EMA 9 / 21 CROSS H1, ALL: EMA9 crosses above EMA21 -> long; below -> short.
- K18 GOLDEN / DEATH CROSS D1, ALL: SMA50 crosses above SMA200 -> D-NEXT long; below -> short; stop 2 ATR; exit 20:45 on the 20th
  trading day.
- K19 LOW-CHOP DONCHIAN H1, ALL: Choppiness Index(14) < 38.2 -> BS at the prior 20 bars' high / low for the next bar; stop 1.5
  ATR14; exit 24 bars after the fill.
- K20 KAMA CROSS H1, ALL: close crosses above Kaufman's adaptive MA (10, 2, 30) -> long; below -> short.
SYSTEMS
- K21 ELDER TRIPLE SCREEN, ALL: weekly EMA13 of weekly closes rising (the last completed week vs the one before) and daily
  stochastic %K(5, 3) below 30 yesterday -> buy stop at yesterday's high (08:00-18:59 LIS), stop at yesterday's low, exit 20:45 on
  the 5th trading day; mirror (EMA13 falling, %K > 70, sell stop at yesterday's low, stop at its high).
- K22 BILL WILLIAMS FRACTAL + ALLIGATOR H1, ALL: up-fractal = a bar whose high is the highest of 5 (known 2 bars later); with the
  Alligator open upward (lips SMMA5 > teeth SMMA8 > jaw SMMA13 of median prices, shifted 3 / 5 / 8) and the close above the
  teeth, BS 1 point above the latest up-fractal for 6 bars, stop 1.5 ATR14, exit 24 bars after the fill; mirror.
CROSS-ASSET (new information for FX and metals)
- K23 COPPER -> AUD: AUDUSD and AUDJPY LB only in the direction of copper futures' (Yahoo HG) last daily change.
- K24 GOLD -> AUD: AUDUSD and AUDJPY LB only in the direction of XAUUSD's move from 01:00 server to 07:59 LIS.
- K25 VIX SPIKE -> SAFE HAVENS: after a VIX close change >= +8%: LB on USDJPY and USDCHF short-only and XAUUSD long-only; after a
  change <= -5%: the opposite sides.
- K26 US RATES -> USDJPY: USDJPY LB only in the direction of the 10-year yield's last daily change (ZN down = yields up = long).
CALENDAR / FLOWS (indices)
- K27 OPEX-FRIDAY PINNING FADE: on the third Friday of each month, SP / NSDQ / DOW NB fade (first touch, enter the other way at the
  next minute, stop 0.5 box beyond, exit 15:55 NY).
- K28 QUARTER-END REBALANCING: on the last 2 trading days of a quarter, box breakouts only AGAINST the quarter-to-date return
  (since the quarter's first 01:00 server mid): SP / NSDQ / DOW on the NB, DAX on 08:00-08:29 LIS (orders to 10:59, exit 16:00
  LIS), NIKKEI on 09:00-09:29 JST (orders to 11:29, exit 14:55 JST).
STRUCTURE
- K29 OUTSIDE-WEEK FOLLOW, ALL: last week engulfed the week before and closed in its top (bottom) 30% -> this week a buy (sell)
  stop at last week's high (low), Monday 08:00 to Thursday 18:59 LIS, stop 1 ATR, exit Friday 20:45.
- K30 MORNING-RANGE AFTERNOON FADE, ALL: fade the first touch of the 01:00 server - 11:59 LIS range between 14:00 and 18:59 LIS,
  stop 0.5 ATR beyond the entry, exit 20:45 ("the day's high or low is set early").

## Periods
DEV 2022-01-01 .. 2024-12-31; VAL 2025; HOLD 2026-01-01 .. 2026-10-16 (Yahoo-file ideas to 2026-09-21), one look, only for ideas
passing DEV and VAL. A 2020-21 CME-futures check on the NQ / ES / GC / SI subset is descriptive only.

## Acceptance (per idea, pooled over its universe)
- DEV: n >= 150; mean net R > 0 with day-clustered t >= 2.94 (Bonferroni, 30 one-sided tests at 5%); positive in >= 2 of the 3
  years; direction information mean(R - R_mirror) > 0 with t >= 2.0.
- VAL: mean > 0 with t >= 1.65. HOLD: mean > 0 with t >= 1.65.
- Account environment: the 5 best by DEV t and any passer replayed from 95,472 with the MT5 broker rules on 2022-25 trades: universe at
  $50 a trade (at most 5 trades a day, earliest first) and NSDQ + XAUUSD at $250; usable only if P(pass) > P(breach) by 30 Jun 2027.
- Multiple-testing context: the 30 DEV t-values against the null (about 1.5 above t 1.65 by luck).

## Dry run (no P&L)
Counts per idea and period, long share, median stop in spreads, markets per idea; truncation test (cut at random times on
EURUSD, XAUUSD, NSDQ: entries >= 35 days before the cut identical); hand check of one entry for 8 ideas.

## Honest prior
About 0-1 pass. Indicator signals of these kinds are the bread and butter of retail platforms; on MT5 broker costs every similar family
(Keltner, Bollinger, Donchian, UT Bot, flags, patterns) came out at minus the spread.
