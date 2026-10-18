# USDJPY London-open breakout re-checked for MT5 broker's zero-spread minutes (2026-10-16 18:24 local, local clock, second PC)

Diagnostic re-measurement of the registered rule (no new trial, no selection; the three variants were written into the
script docstring before any number was computed). Rule unchanged (`usdjpy_sens.run(E, lc, 8, 30, 17)`): 08:00-08:30 London
box, one-cancels-other stop orders until 11:00, stop at the other side, no target, exit 17:00 London. Script
`usdjpy_spreadfix.py`, output `USDJPY_SPREADFIX_OUTPUT.txt`. Why: `BRK_PATTERNS_RESULT.md` found the MT5 broker MT5 M1 spread field
is 0 on many minutes, so bar backtests fill those minutes at no cost.

## Where the zeros are (USDJPY, 08:00-17:00 London)
2022 13% of minutes, **2023 72%**, 2024-26 about 0%. Median non-zero spread 0.1-0.2 pip in 2022-23, 0.6-0.7 pip since 2024.
Inside the 08:30-11:00 entry window: 12% (2022), 69% (2023).

## Result (mean net R a trade; t in brackets; ~250 trades a year)
| period | A raw bars | B zero fix | C 0.6 pip floor (today's cost) |
|---|---|---|---|
| 2022 | +0.409 (2.50) | +0.409 (2.50) | +0.282 (1.87) |
| 2023 | -0.154 (-1.29) | -0.155 (-1.30) | -0.158 (-1.33) |
| 2024 | +0.185 (1.24) | +0.185 (1.24) | +0.185 (1.24) |
| **DEV 2022-24** | **+0.146 (1.74)** | **+0.146 (1.74)** | **+0.103 (1.27)** |
| VAL 2025 | +0.108 (0.89) | +0.108 (0.89) | +0.108 (0.89) |
| 2026 (to 10-16) | +0.111 (0.62) | +0.111 (0.62) | +0.111 (0.62) |

A reproduces `USDJPY_SENS_RESULT.md` (+0.146 / +0.108 / +0.114; 2026 now runs to 16 Oct instead of 3 Oct), so the
second PC's freshly pulled data matches the main PC's.

## Reading
1. **The zero-spread flaw does not touch this lead.** The fix replaces the zero minutes with about 0.1 pip, and the
   risk per trade is the box (median 18.9 pips, 10th percentile 9.0), so the fix costs about 0.005 R a trade: every
   figure is unchanged to the third decimal.
2. **What does matter is that MT5 broker's USDJPY spread went from 0.1-0.2 pip (2022-23) to 0.6-0.7 pip (2024-26).** At today's
   cost the 2022-24 figure drops from +0.146 to +0.103 R (t 1.27), almost all of it from 2022 (+0.41 -> +0.28). 2025 and
   2026 were already priced at today's spread and stay at +0.11 R a trade.
3. **Since 2023 no single year is significant** (t 1.24 / 0.89 / 0.62), and 2023 lost. The bar model says a small
   positive edge of about +0.1 R a trade at today's cost; the 2020-21 out-of-time check said +0.20 R at today's spread
   (`BREAKOUT_KNOWLEDGE.md` section 2).
4. **Unchanged and still the binding caveat:** on MT5 broker real ticks (Oct 2025 - Oct 2026, 300 ms latency) the same rule
   earned -0.02 R a trade against +0.07 R on the bars for the same days (`USDJPY_TICKS_RESULT.md`). Real execution
   (variable spread, spikes, gaps through the stop) costs 0.05-0.08 R a trade more than any bar model, zero fix or not.
   Net of that the edge is about +0.03..+0.06 R a trade at today's cost: at most marginal, and about zero last year.

## Status
The lead stands exactly where it stood: real on bars, not significant in any recent year, about zero on real ticks.
The zero-spread finding does not weaken it, and it does not strengthen it either. Its forward test (LDN3F paper log from
2026-10-19, `PREREG_LDN3F.md`) is the right place to learn more; no money should ride on it before that.
