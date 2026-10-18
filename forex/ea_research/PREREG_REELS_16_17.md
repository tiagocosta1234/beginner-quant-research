# PREREG REELS_16_17 - reel 16 (NY box: breakout close vs retest) and reel 17 (first 5-min candle vs 12 EMA, trailing stop)

Registered 2026-10-17 ~23:41 local (local clock; corrected from a guessed 23:45, the file was frozen at 23:42:32, second PC PC-2), before any P&L of these rules was computed.
the trader: "i put some other reels for you to test". Notes: `reels/16_ny_box_breakout_vs_retest/NOTAS.md`,
`reels/17_nq_first_5min_candle_vs_ema12/NOTAS.md`; reel 15 (Zenith) shows no rules and is not testable
(`reels/15_zenith_nq_prop_81pct_no_rules/NOTAS.md`). Related closed results: touch vs 5/15-min close (BRK_CONFIRM, 0/4),
break-and-retest (BRK_RETEST, 0/6), the Zarattini 5-min ORB (BRK_CLASSICS).

## Data
MT5 broker NSDQ (NAS100 CFD) M1 bid/ask, 2021-12..2026-10-16, zero-spread minutes repaired as in `PREREG_BRK_PATTERNS.md`.
Descriptive extension (not trials): the same rules on SP and DOW.

## Reel 16 rules
- Box 09:30-10:00 New York: high = highest bid high, low = lowest bid low of the box minutes (>= 24 minutes).
- Signal: the first clock-aligned 5-minute MID candle from 10:00 to 12:00 New York whose close is above the box high (long) or
  below the box low (short).
- **R16-T1 (breakout):** market entry at the open of the minute after the signal candle (ask for longs, bid for shorts).
  Stop = the other side of the box; target = entry + side x (entry - stop) (1 R); exit at 16:00 New York if neither is hit.
- **R16-T2 (retest):** after the same signal, a limit order at the box edge (buy limit fills when the ASK low reaches the box
  high, at min(edge, ask open); sell limit mirrored on the bid); the SAME stop and target LEVELS as R16-T1; if the target is hit
  before the limit fills, no trade that day; the limit lives until 16:00 New York. On the fill minute only the stop counts.
- Size: both traders trade the same size, so R16-T2's result is measured in R16-T1's R (points / T1's entry-stop distance);
  points are also reported (the reel's dollars).

## Reel 17 rules
- 5-minute mid candles on the clock grid, EMA12 (span 12, `adjust=False`) of the 5-minute closes over all hours.
- Signal candle 09:30-09:35 New York: long if its close > EMA12 at that close, short if <. Entry at the open of the first minute
  at or after 09:35 (ask / bid). Initial stop: the signal candle's mid low (long) / mid high (short); R = |entry - stop|.
- **R17-EMA:** at every later 5-minute close the stop moves to that close's EMA12 if this is tighter.
- **R17-SWING:** at every later 5-minute close the stop moves to the lowest mid low (long) / highest mid high (short) of the
  last 3 completed 5-minute candles if this is tighter.
- Stops never loosen; a stop hit on the M1 bars exits at the stop or at the minute's open if it gapped; exit at 16:00 New York
  otherwise. One trade per day.

## Trials (4): R16-T1, R16-T2, R17-EMA, R17-SWING on NSDQ
## Periods
DEV 2022-01-01..2024-12-31, VAL 2025, HOLD 2026-01-01..2026-10-16 (one look, only for a trial passing DEV and VAL).

## Acceptance
- DEV: n >= 300; mean net R > 0 with day-clustered t >= 2.5 (Bonferroni, 4 trials); positive in >= 2 of 3 DEV years.
- VAL: mean > 0, t >= 1.65. HOLD: mean > 0, t >= 1.65.
- Account environment (standing rule): NSDQ at $250 a trade from 95,472, MT5 broker rules (`usdjpy_account_env.account`), printed for
  all four trials; usable only if P(pass) > P(breach) by 30 Jun 2027.

## Descriptive (the reels' own claims)
- Reel 16: total points of T1 and T2; share of days T2 never filled; T2 vs T1 on the days both traded; T1 on the no-retest days.
- Reel 17: win rate and profit factor against the claimed 57% / 1.29.

## Honest prior
About 5%. A 5-min close entry was worse than the touch on these boxes (BRK_CONFIRM); retests select the weaker breakouts
(BRK_RETEST); a PF of 1.29 with opening-candle stops leaves little room for MT5 broker's 1-2 point NSDQ spread.

## Amendments
(none yet)
