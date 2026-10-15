# BRK-EXITS result (breakout day round 1, 2026-10-15 11:30): no exit makes the session breakout pay
Pre-registration `PREREG_BRK_EXITS.md`, engine `brk_exits.py`, rows `D:\finance\si_ledgers\BRK_EXITS.parquet`. 46 markets, 33,041 DEV / 12,229 VAL / 8,736 2026 breakouts and as many random-entry controls. Dry-run: truncation PASS; hand check NSDQ 2024-06-12 long filled 17:14 server (as ORB-REFINE), every exit near -0.07 R at the close (price came back to the entry by the end of the FOMC day).

| exit | breakout DEV / VAL / 2026 (R per trade) | random-entry control DEV / VAL | win % DEV | avg win / loss (R) |
|---|---|---|---|---|
| X1 target 1R | -0.058 / -0.090 / -0.057 | -0.088 / -0.110 | 47% | +0.97 / -0.96 |
| X2 target 2R | -0.040 / -0.099 / -0.044 | -0.087 / -0.107 | 35% | +1.48 / -0.94 |
| X3 target 3R | -0.041 / -0.103 / -0.025 | -0.085 / -0.115 | 32% | +1.87 / -0.95 |
| X4 no target, close at session end | **-0.032** / -0.076 / -0.037 | -0.079 / -0.111 | 30% | +2.07 / -0.95 |
| X5 breakeven after +1R | -0.037 / -0.081 / -0.053 | -0.088 / -0.120 | 21% | +2.22 / -0.65 |
| X6 trail 1R | -0.058 / -0.082 / -0.073 | -0.091 / -0.118 | 36% | +0.98 / -0.64 |
| X7 trail 2R | -0.041 / -0.094 / -0.043 | -0.088 / -0.113 | 33% | +1.62 / -0.87 |
| X8 half at 1R + breakeven | -0.048 / -0.086 / -0.055 | -0.088 / -0.115 | 47% | +0.98 / -0.96 |
| X9 time stop 60 min | -0.056 / -0.063 / -0.040 | -0.085 / -0.114 | 35% | +1.14 / -0.69 |
0 of 9 exits pass (every one negative in every period).

What it teaches:
- **Exits move the result by 0.03 R at most; entries decide.** The best exit is the simplest: no target, hold to the session close (X4). Breakeven and trailing stops cut losers but cut the winners more.
- **Breakout entries do carry a little information:** with every exit they beat random entries by 0.03-0.05 R (DEV). That is less than the cost of a round trip, so the breakout is still negative on the whole universe.
- **Indices are the exception:** session breakout with the stop at the other side of the box and the exit at the close: +0.049 R (t 1.97) DEV, +0.057 (t 1.21) VAL, but -0.038 in 2026; random entries on the same indices -0.009 / -0.049 / -0.028. SP +0.160 / +0.076 / -0.105, NSDQ +0.141 / +0.077 / -0.088, DAX +0.112 / +0.096 / -0.011; by year +0.101 (2022), +0.025, +0.022, +0.057, -0.038 (2026). Crypto, energy and metals lose with every exit.
