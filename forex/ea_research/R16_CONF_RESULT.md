# R16_CONF result - no confluence improves reel 16's NY-box breakout (0 of 8 kept)

Run 2026-10-17 23:49-23:50 local (local clock, second PC). Pre-registration `PREREG_R16_CONF.md` (registered 23:49; amendment 1 at 23:50
after the first run crashed on an empty group, engine fix only; hashes in `data\scratch\r16_conf_freeze.txt`). Engine
`r16_conf.py`, output `R16_CONF_OUTPUT.txt`. Base: R16-T1 on MT5 broker NSDQ (DEV 728 trades +0.067 R, VAL 236 trades +0.024 R).
Selection on DEV 2022-24 only; 2025 shown for each flag as a descriptive check; HOLD 2026 stays sealed.

| confluence | DEV with: n, R | DEV without: n, R | t | kept | 2025 with / without (descriptive) |
|---|---|---|---|---|---|
| C1 unmitigated FVG inside the box | 421, +0.086 | 307, +0.041 | +0.68 | no | +0.001 / +0.058 |
| C2 with the 20-day trend | 382, +0.097 | 346, +0.034 | +0.98 | no | +0.037 / +0.010 |
| C3 box not in the smallest third (box/ATR >= 0.272) | 485, +0.041 | 243, +0.119 | -1.11 | no | -0.004 / +0.066 |
| C4 gap in the break direction | 378, +0.080 | 350, +0.052 | +0.44 | no | -0.078 / +0.109 |
| C5 strong signal candle (outer 25%) | 544, +0.061 | 184, +0.083 | -0.29 | no | +0.027 / +0.016 |
| C6 beyond the session TWAP | 728, +0.067 | 0 | - | no (always true: a close outside the box is always beyond the TWAP) | - |
| C7 S&P outside its own box the same way | 496, +0.092 | 232, +0.013 | +1.13 | no | +0.012 / +0.064 |
| C8 volatility expanding (ATR20 > ATR100) | 287, +0.035 | 441, +0.087 | -0.78 | no | -0.003 / +0.059 |

## Reading
- Nothing reaches the keep bar (t >= 2.0 on DEV). The three that looked best on 2022-24 - the FVG (+0.045 R), the 20-day trend
  (+0.063) and S&P confirming (+0.079) - each reverse or shrink in 2025 (FVG and S&P now worse than without; trend +0.027):
  the 2022-24 gaps were noise of the size expected from ~400-trade splits.
- Small boxes (C3 false) did BETTER here (+0.119 vs +0.041), the opposite of the general finding for touch entries; with a
  close-confirmation entry and a 1 R target, a small box means a small stop that the target reaches easily. Not a rule either.
- The base stays what it was: +0.067 R (t 2.09) in 2022-24, +0.024 R in 2025.

## In the account's environment (base rule, NSDQ, 2022-25 trades, from 95,472, MT5 broker rules; pass% / breach%)
| risk a trade | 22 Dec | 31 Mar 2027 | 30 Jun 2027 |
|---|---|---|---|
| $250 | 0.0 / 0 | 0.0 / 3 | 0.0 / 4 |
| $500 | 0.0 / 11 | 1.3 / 22 | 8.6 / 25 |
At $500 a trade, breach is about three times as likely as a pass by mid-2027; at $250 it never reaches the target in time.
