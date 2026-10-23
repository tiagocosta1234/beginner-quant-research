# READ_TEST2 result: the read v9 just misses its bar (23 Oct 2026 08:45 local, local clock)

Pre-registration: `PREREG_READ_TEST2.md`, with hashes in `PREREG_READ_TEST2.sha256`.
- Rules hashed 23 Oct 01:00:14, before the draw.
- Amendment 1 (scorer only) hashed 08:45:27, after T100 was locked and before any outcome was shown. It did two things:
  - a bracket whose entry was already beyond the target or stop counts as no trade. It dropped 0 read pairs and 1 naive pair.
  - the verdict now checks the third pre-registered condition, mean R > 0.

Calls: `READ_TEST2_CALLS.csv`, 100 rows, each hashed when locked. Scorer output: `READ_TEST2_OUTPUT.txt`. One look, after T100.

## Primary
| | Trades | Mean R | Mirror R | Excess over a random side | Wins | Sign-flip P |
|---|---|---|---|---|---|---|
| **Read v9 (v8 + with the 30-min trend only + signal 08:02 or later)** | 47 (53 no-trade days) | +0.093 | -0.228 | **+0.161** | 37 | **0.0377** |
| Pool A (2022) | 25 | +0.111 | | +0.240 | | 0.039 |
| Pool B (Jan-May 2024) | 22 | +0.073 | | +0.070 | | 0.269 |
| Naive: 08:00 candle in the 30-minute trend direction, same bracket | 99 | -0.093 | -0.241 | +0.074 | 68 | 0.130 |

**NOT SHOWN.** The bar was excess >= +0.10 R, P <= 0.03 and mean R > 0.
- Excess and mean R pass. P is 0.038, just above 0.03.
- Read excess minus the naive excess, on the days the read traded: +0.099 (47 trades).

Against v8 (`READ_TEST_RESULT.md`, 93 trades):

| | v8 | v9 |
|---|---|---|
| Excess | +0.066 | +0.161 |
| P | 0.143 | 0.038 |
| Mean R | +0.019 | +0.093 |
| Read minus naive | -0.014 | +0.099 |

- The two constraints moved every number the right way, on 100 days never looked at.
- It is still one look that missed its bar. Under the protocol that means no claim, no re-tuning and no second look at these days.

## Exploratory breakdown (`read_test2_breakdown.py`, `READ_TEST2_BREAKDOWN_OUTPUT.txt`, `READ_TEST2_TRADES.csv`)
Post-hoc, 47 trades split many ways: not evidence.

| Split | Trades | Mean R | Excess | Wins |
|---|---|---|---|---|
| Resumption / flag | 17 | -0.118 | -0.041 | 11 |
| Break of a high / low / base | 13 | +0.047 | +0.228 | 10 |
| Failed bounce / rollover | 7 | +0.198 | +0.216 | 6 |
| Signal 08:02-08:05 | 28 | +0.136 | +0.215 | |
| Signal 08:06 or later | 19 | +0.031 | +0.081 | |
| Shorts | 19 | +0.172 | | |
| Longs | 28 | +0.040 | | |

- **Resumption regressed.** It went 10 / 10 in the v8 test, here 11 / 17 with -0.118 R: the regression to the mean the pre-registrations warn about.
- **Passing paid.** On the 52 no-trade days with a scorable naive trade, the naive 08:00 trend trade would have made -0.133 R (35 / 52 wins at these brackets). Skipping chop, extended pushes and entries into the session extreme saved money.
- **One process slip.** On T078 a two-step scan loop passed an 08:02 candidate without a separate decision. It was a third push 1.56 ATR from the EMA, a pass under the same rule. Noted in the locked call.

## What it means
- With the trend, after 08:02, skipping chop, extended pushes and the session extreme, my read picks the side better than chance by about +0.16 R on these days.
- After desk costs that is +0.09 R a trade, and it does not clear the bar. Not a validated edge.
- The clean next evidence is forward only: live London calls logged and hashed before the outcome, on fresh days (`LIVE_CALLS.csv`).
- First one, 23 Oct 2026: long 4 MGC on TradingView Paper, 4027.5 to TP 4031.9, +$184, about +0.9 R. n = 1.
- These 100 days and the v8 test's 100 days are spent.
