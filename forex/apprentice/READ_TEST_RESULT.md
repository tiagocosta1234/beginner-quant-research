# READ_TEST result: the apprentice's frozen read does not pass (23 Oct 2026 ~00:5x local, local clock)

Pre-registration: `PREREG_READ_TEST.md`. Its hashes are in `PREREG_READ_TEST.sha256`, recorded 22 Oct 22:35:52, before the draw. Calls: `READ_TEST_CALLS.csv` (100 rows, each hashed when locked). Scorer output: `READ_TEST_OUTPUT.txt`. One look, after T100.

## Primary
| | Trades | Mean R | Mirror R | Excess over a random side | Wins | Sign-flip P |
|---|---|---|---|---|---|---|
| **Read (frozen v8, lessons 1-20)** | 93 (7 no-trade days) | +0.019 | -0.112 | **+0.066** | 68 | **0.143** |
| Pool A (2023) | 45 | -0.046 | | +0.105 | | 0.128 |
| Pool B (Jun-Dec 2025) | 48 | +0.080 | | +0.029 | | 0.372 |
| Naive: 08:00 candle in the 30-minute trend direction, same bracket | 100 | -0.022 | -0.174 | +0.076 | 70 | 0.112 |

**NOT SHOWN** (bar: excess >= +0.10 R and P <= 0.03).
- The read picked the side a little better than chance, but no better than the naive trend rule. On the days the read traded, its excess minus the naive excess was -0.014.
- The in-sample +0.217 on the trader's 33 days shrank to +0.066 on unseen days, as the pre-registration warned it might.
- After desk costs the read made +0.019 R a trade: nothing to trade on.

## Exploratory breakdown (`read_test_breakdown.py`, `READ_TEST_BREAKDOWN_OUTPUT.txt`, `READ_TEST_TRADES.csv`; post-hoc, 93 trades split many ways, not evidence)
- **With the 30-minute trend:** 69 trades, mean R +0.119, excess +0.153.
- **Against it:** 24 trades, mean R -0.269, excess -0.185.
  - The counter-trend lessons lost out of sample: held level against the trend (17), sweep and turn (18), and stall under the gap against the 30-minute bounce (19).
  - Family results: stall / end of bounce, 19 trades, excess -0.046; sweep, 15 trades, -0.003; held level, 30 trades, +0.031.
- **Signal time:**
  - 08:03 or later: 23 trades, mean R +0.188, excess +0.214;
  - 07:59-08:02: 70 trades, mean R -0.037, excess +0.017.
  - Waiting for the open to show its hand did better.
- **Resumption after a pullback (lesson 7):** 10 / 10 winners, mean R +0.435. Tiny n.
- **Longs** +0.129 (52 trades) against **shorts** -0.121 (41). This is probably gold's upward drift in both pools.

## What it means
- Imitating the trader's discretion, learned on 33 of his days, gives no tradeable edge on fresh gold days. This joins every mechanical form tested before (EMA12, MANUALRULE, TRAP12, the rubric).
- The one pattern worth a fresh, pre-registered look is "with the 30-minute trend, after a pullback, not at the first candle". It was chosen after seeing these trades, so it needs new days: 2020-2022, Jan-May 2024 or Dec 2024-Mar 2025, never these 100 or the 2026 hold-out.
