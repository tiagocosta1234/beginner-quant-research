# PREREG BRK50 - brief and pre-registration of 52 untested breakout ideas, all tested in one round

Registered 2026-10-17 22:48 local (local clock, second PC PC-2), before any P&L of these ideas was computed.
the trader (/goal): "brief on next breakout ideas (at least 50) and test all of them". The ~45 breakout families already closed
(`BREAKOUT_KNOWLEDGE.md`, `BREAKOUT_DAY_2026-10-15.md` rounds 1-44, and on 2026-10-16 BRK_PATTERNS, BRK_CONFIRM, BRK_TWOWAY,
BRK_FVG) are excluded: intraday session boxes (London / NY / Asia, 5-, 15-, 30-, 60-min, hour-of-day map), Donchian / turtle
intraday, Larry Williams, Crabel inside day, NR4/NR7, TTM squeeze, flags, round numbers, retests, buffers, tested levels,
stop-and-reverse, pyramiding, exits grids, weekly / monthly opening boxes, month-opening range, first-of-month, news days,
weekdays, cash gaps, overnight range, initial balance, partner / laggard / crowd / USD-index confirmation, relative strength,
tick volume, volatility regime, ML selectors, ICT models, chart patterns, 52-week highs, candle-close confirmation, two-way
confluence classifier, FVG confluence. The 52 below are new: other LEVEL types, exchange-specific opens, volatility STATES,
cross-asset alignment, calendar ranges, crypto ranges and bar-close channel signals, with fade twins where a fade is natural.

**Window note:** the repo's kill rule is 40 variants per research window; the trader's goal asks for >= 50. This round is one
pre-registered family of 52 fixed rules (no tuning, no variants), judged with a Bonferroni bar for 52 tests.

## Common rules (every idea)
- Data: MT5 broker M1 bid/ask, 46 markets, 2021-12..2026-10-16 (`forex/data_mt5`), zero-spread minutes repaired (previous month's median
  non-zero spread; months without spread data take the next month's), as in `PREREG_BRK_PATTERNS.md`. Server clock = Athens;
  "day" = server trading day; daily H / L / C from M1 mids of that day; ATR = 20-day mean of daily ranges of completed days.
- Universes: ALL = 38 non-crypto markets; FX = 28 pairs; IDX = ASX DAX DOW NIKKEI NSDQ SP; MET = XAUUSD XAGUSD; ENE = WTI BRENT;
  USD = AUDUSD EURUSD GBPUSD NZDUSD USDCAD USDCHF USDJPY; JPY = AUDJPY CADJPY CHFJPY EURJPY GBPJPY NZDJPY USDJPY;
  CRY = 8 crypto.
- Level ideas: a level is armed only if, at the window start, the mid price is on the near side of it (inside a two-sided
  range). FOLLOW: buy stop at the upper level (fills when ASK reaches it, at max(level, ask open)) / sell stop at the lower
  level; first touch wins, a minute touching both is skipped. FADE: at the first touch, enter the opposite way at the next
  minute's open (sell at bid / buy at ask). One trade per idea, market and day (weekly / monthly / quarterly ideas: per period).
  No fills in the server 23:00-00:59 rollover window. Stops as listed; no profit target; exit at the listed time (bid for
  longs, ask for shorts), `brk_patterns.walk` rules (gap = open beyond the stop; on the entry minute only the stop counts).
- R = net P&L / |entry - stop|. Times are local (LIS) unless marked NY / JST / SYD / UTC; "20:45" = 20:45 local (22:45 server).
- Direction information: for every trade, the MIRROR trade (opposite side, entry at the next minute's open, same stop
  distance, same exit) is also computed; info = R - R_mirror.

## The 52 ideas (brief rationale in brackets)
LEVELS - prior periods
- I01 PDH/PDL BREAK, ALL: prior day high / low, window 08:00-19:00, stop 0.5 ATR from the entry, exit 20:45. [the most watched intraday levels; never traded directly here]
- I02 PDH/PDL FADE, ALL: same levels and window, fade the first touch, stop 0.5 ATR, exit 20:45. [stops above the high get swept and reverse]
- I03 PDH/PDL H1-CLOSE, ALL: enter at the first 1-h candle (server grid) closing beyond the level, entry at the next minute, stop 0.5 ATR, exit 20:45. [confirmation on a higher timeframe]
- I04 PDH/PDL WITH STRONG CLOSE, ALL: long break of PDH only if yesterday closed in its top 20% (short at PDL only if bottom 20%), stop 0.5 ATR, exit 20:45. [continuation of a strong close]
- I05 PRIOR-WEEK H/L BREAK, ALL: last week's high / low, window Mon-Fri 08:00-19:00 (first touch of the week), stop 0.5 ATR, exit Friday 20:45. [weekly levels, swing hold]
- I06 PRIOR-WEEK H/L FADE, ALL: fade the first touch of the week, stop 0.5 ATR, exit 20:45 the same day. [weekly liquidity sweep]
- I07 PRIOR-MONTH H/L BREAK, ALL: last month's high / low, stop 1 ATR, exit after 5 trading days at 20:45. [monthly levels]
- I08 PRIOR-MONTH H/L FADE, ALL: fade the first touch, stop 0.5 ATR, exit 20:45 the same day.
- I09 PRIOR-QUARTER H/L BREAK, ALL: stop 1.5 ATR, exit after 10 trading days at 20:45. [rare, big levels]
- I10 INSIDE-WEEK BREAK, ALL: if last week's range lies inside the week before's, trade the break of last week's high / low this week, stop 1 ATR, exit Friday 20:45. [weekly compression]
- I11 FLOOR PIVOT R1/S1 BREAK, ALL: P = (H+L+C)/3, R1 = 2P-L, S1 = 2P-H of yesterday; stop at P; exit 20:45. [floor-trader levels]
- I12 FLOOR PIVOT R1/S1 FADE, ALL: fade the first touch of R1 / S1, stop at R2 / S2 (P +/- (H-L)), exit 20:45.
- I13 CAMARILLA H4/L4 BREAK, ALL: H4/L4 = C +/- 1.1 (H-L)/2; stop at H3/L3 = C +/- 1.1 (H-L)/4; exit 20:45. [Camarilla breakout rule]
- I14 CAMARILLA H3/L3 FADE, ALL: fade the first touch of H3 / L3, stop at H4 / L4, exit 20:45. [Camarilla reversal rule]
- I15 WEEKLY PIVOT R1/S1 BREAK, ALL: pivots from last week's H/L/C; window Mon-Fri 08:00-19:00 (first touch of the week), stop 0.5 ATR, exit 20:45 that day.
- I16 YESTERDAY'S BODY BREAK, ALL: levels max / min of yesterday's open (01:00 server mid) and close; stop at the other body edge (skip if < 0.1 ATR); exit 20:45. [real-body range instead of wicks]
- I17 3-DAY RANGE BREAK, ALL: high / low of the last 3 completed days, stop at the 3-day mid, exit 20:45.
- I18 OUTSIDE-DAY FOLLOW, ALL: if yesterday was an outside day closing in its top (bottom) 30%, buy (sell) the break of its high (low) only, stop 0.5 ATR, exit 20:45.
- I19 POST-EXPANSION BREAK, ALL: if yesterday's range > 1.8 ATR, break of yesterday's high / low, stop 0.5 ATR, exit 20:45. [momentum after a big day]
- I20 POST-EXPANSION FADE, ALL: same days, fade the first touch, stop 0.5 ATR, exit 20:45. [exhaustion after a big day]
VOLATILITY STATE / INTRADAY RANGES
- I21 CRABEL STRETCH, ALL: open O = 01:00 server mid; stretch = 10-day mean of min(|O-H|, |O-L|); buy stop O + stretch, sell stop O - stretch, window 01:05 server-19:00, stop at O, exit 20:45. [Crabel's opening-range stretch]
- I22 MORNING EXPANSION FOLLOW, ALL: if the 01:00 server-12:00 range > 1 ATR, trade the break of that range 12:00-19:00, stop 0.5 ATR, exit 20:45.
- I23 MORNING COMPRESSION BREAK, ALL: if the 01:00 server-11:00 range < 0.3 ATR, trade its break 11:00-19:00, stop at the other side, exit 20:45.
- I24 HALF-DAY RANGE BREAK, ALL: range 01:00 server-12:00 (any size), break 12:00-19:00, stop at the range mid, exit 20:45.
- I25 PRIOR NY RANGE IN LONDON, ALL: yesterday's 14:30-21:00 range, window today 08:00-12:00, stop at the other side (0.5 ATR if wider than 1 ATR), exit 17:00.
- I26 TRIPLE COMPRESSION, ALL: if the Asian range (01:00-07:00) < 0.25 ATR and the London box (08:00-08:30) < 0.10 ATR, trade the London box break 08:30-11:00, stop at the other side, exit 17:00.
- I27 TIGHT-ASIA BREAK, ALL: if the Asian range (01:00-07:00) < 0.25 ATR, trade its break 07:00-11:00, stop at the other side, exit 17:00.
- I28 TWAP 2-SIGMA BREAK, ALL: time-weighted mean and SD of minute mids since 08:00 (each minute's band uses the minutes before it); the first touch of TWAP +/- 2 SD between 09:00 and 16:00, stop at the TWAP, exit 17:00.
- I29 TWAP 2-SIGMA FADE, ALL: fade that touch, stop at TWAP +/- 3 SD, exit 17:00.
EXCHANGE / FIXING OPENS (box = the first 30 min unless noted; stop at the other side of the box)
- I30 FRANKFURT OPEN, EUR / GBP / CHF pairs + DAX: box 07:00-07:30, window to 09:30, exit 16:00.
- I31 NY FX OPEN, USD + XAUUSD: box 08:00-08:30 NY, window to 10:00 NY, exit 16:00 NY.
- I32 PRE-DATA RANGE, USD + XAUUSD + DOW NSDQ SP: box 07:30-08:29 NY, break 08:30-10:00 NY, exit 16:00 NY. [range before the 08:30 US releases]
- I33 COMEX GOLD OPEN, MET: box 08:20-08:50 NY, window to 11:00 NY, exit 13:30 NY.
- I34 NYMEX OIL OPEN, ENE: box 09:00-09:30 NY, window to 11:30 NY, exit 14:30 NY.
- I35 TOKYO OPEN, JPY + NIKKEI: box 09:00-09:30 JST, window to 11:30 JST, exit 15:00 JST.
- I36 SYDNEY OPEN, ASX + AUD / NZD pairs: box 10:00-10:30 Sydney, window to 12:30 Sydney, exit 16:00 Sydney.
- I37 LONDON CLOSE / FIX, FX + MET: box 15:30-16:00, break 16:00-17:30, exit 20:45.
- I38 NY LUNCH RANGE, DOW NSDQ SP + USD + MET: box 12:00-13:30 NY, break 13:30-15:00 NY, exit 15:55 NY.
CROSS-ASSET ALIGNMENT (London / NY 30-min boxes, stop at the other side)
- I39 RISK-ALIGNED YEN CROSSES, JPY crosses without USDJPY: London box break taken only if NSDQ's move from 01:00 server to 08:00 has the same sign as the cross's side (risk-on = yen down). Exit 17:00.
- I40 RISK-ALIGNED INDICES, DAX ASX NIKKEI: London box break only if NSDQ's 01:00 server-08:00 move agrees. Exit 17:00.
- I41 OIL-ALIGNED USDCAD, USDCAD: NY box (09:30-10:00 NY) break only if WTI's move since 09:30 NY is opposite in sign to the USDCAD side. Exit 16:00 NY.
- I42 GOLD-SILVER CONFIRMED, MET: London box break of one metal only if the other's mid moved the same way since 08:30. Exit 17:00.
- I43 QUIET-LONDON NY BREAK, IDX US + USD: NY box break only if the 08:00-14:30 range < 0.5 ATR. Exit 16:00 NY. [quiet London, expansion in NY]
CALENDAR / ENTRY MECHANICS
- I44 MONDAY BREAK OF FRIDAY, ALL: on Mondays, Friday's high / low, window 08:00-19:00, stop 0.5 ATR, exit 20:45.
- I45 FRIDAY AFTERNOON BREAK, ALL: on Fridays, the 01:00 server-12:00 range broken 12:00-19:00, stop at the range mid, exit 20:45.
- I46 RE-BREAK AFTER FAILURE, ALL: London box: after a first break that trades back inside the box, the next break on the SAME side 08:30-11:00, stop at the other side, exit 17:00.
- I47 LARGE-BOX FADE, ALL: London box >= 0.4 ATR: fade the first touch 08:30-11:00, stop 0.5 box beyond the entry, exit 17:00.
BAR-CLOSE CHANNELS
- I48 KELTNER H1, ALL: 1-h close above EMA20 + 2 ATR14(H1) / below EMA20 - 2 ATR14 -> follow at the next minute, stop 1.5 ATR14(H1), exit after 24 H1 bars (moved out of the rollover window).
- I49 BOLLINGER H1, ALL: 1-h close outside SMA20 +/- 2 SD -> follow, stop 1.5 ATR14(H1), exit after 24 H1 bars.
- I50 BOLLINGER RE-ENTRY FADE, ALL: a 1-h close back inside the bands right after a close outside -> trade back toward the mean, stop 1.5 ATR14(H1), exit after 12 H1 bars.
- I51 DONCHIAN H4, ALL: stop orders at the prior 20 H4 bars' high / low, stop 2 ATR14(H4), exit after 30 H4 bars.
CRYPTO
- I52 CRYPTO DONCHIAN H4, CRY: as I51 on the 8 crypto markets (7 days a week).
- I53 CRYPTO UTC-OPEN ORB, CRY: box 00:00-01:00 UTC, window to 08:00 UTC, stop at the other side, exit 20:00 UTC (every day).
- I54 CRYPTO WEEKEND RANGE, CRY: Saturday-Sunday (UTC) range broken Monday-Friday 20:00 UTC, stop at the range mid, exit Friday 20:00 UTC.
(54 ideas listed; the Bonferroni bar is set for 54.)

## Periods
DEV 2022-01-01..2024-12-31, VAL 2025, HOLD 2026-01-01..2026-10-16 (one look, only for ideas passing DEV and VAL).

## Acceptance (per idea, pooled over its universe)
- DEV: n >= 150; mean net R > 0 with day-clustered t >= 3.12 (Bonferroni for 54 one-sided tests at 5%); positive in >= 2 of
  the 3 DEV years; direction information mean(R - R_mirror) > 0 with t >= 2.0.
- VAL: mean > 0, t >= 1.65. HOLD: mean > 0, t >= 1.65.
- Account environment (standing rule): a full passer is replayed from 95,472 with the MT5 broker rules (`usdjpy_account_env.account`)
  (a) on NSDQ + XAUUSD at $250 a trade if they are in its universe, (b) on its whole universe at $50 a trade, at most 5 trades a
  day (earliest first); usable only if P(pass) > P(breach) by 30 Jun 2027. The account view of the 5 best ideas by DEV t is
  printed regardless of the verdict.
- Multiple-testing context: the distribution of the 54 DEV t-values is reported against what 54 independent null tests give.

## Dry run (no P&L)
`python -m forex.ea_research.brk50 --dry-run`: trade counts per idea and period; truncation causality test (cut the data at random
times on 3 markets: every entry before the cut day identical); a hand check of one entry for 10 ideas.

## Honest prior
About 1-2 passes expected by luck at a raw 5% level, ~0 at the Bonferroni bar. Every breakout family so far showed breakout
information below the spread; the new level types and conditions are the untested remainder, not a reason for optimism.

## Amendments
1. (2026-10-17, before any P&L) I53 exit 23:00 UTC -> 20:00 UTC (23:00 UTC falls in the server rollover window in winter);
   I28 / I29 window end stated (16:00).
2. (2026-10-17, after the dry run, before any P&L was looked at) The dry run's truncation test flagged the bar ideas I48-I51:
   the truncated run kept December 2021 warm-up trades that the full build drops (`day >= 2022-01-01`); with the same filter the
   test is identical on EURUSD, XAUUSD, NSDQ and BTCUSD (entries, sides, R and mirror R; `C:\work\scratch\brk50_trunc2.txt`).
   Test artefact only, no rule change. Hand check: I21 EURJPY 2023-03-22 stop of 635 spreads verified (10-day stretch 0.635 JPY,
   MT5 broker spread 0.001 JPY in March 2023).
