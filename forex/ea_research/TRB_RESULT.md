# TRB result (2026-10-14 ~23:10): reel 13's breakout method, run walk-forward - NO EDGE; the selection picks noise
Pre-registration `PREREG_TRB.md` (commit 1be1a5cc), engine `trb.py` (cache `data\tmp\trb_cache`), trades `data\si_ledgers\TRB_trades.parquet`. Source: `reels/13_breakout_lesson/NOTAS.md`. 2026 never loaded.

Dry-run: 2,808 configurations x every day x 46 markets simulated (153 s); truncation test PASS (EURUSD, XAUUSD); hand check NSDQ 2024-03-05, 09:30-10:00 NY box 17,991.0-18,100.6 (range 109.6), sell stop filled 10:08 NY, BOTH / SL 1 / TP 1 = +1.0 R (target), TP 2 = +1.33 R (time exit) - matches the cache.

| cell | DEV n | DEV net R | gross | t | VAL n | VAL net | gross | t | random-pick placebo DEV |
|---|---|---|---|---|---|---|---|---|---|
| W1 his process, 46 markets | 22,097 | -0.128 | -0.001 | -8.06 | 9,407 | -0.127 | +0.020 | -5.70 | -0.198 .. -0.147 |
| W2 his process, SP/NSDQ/DOW/DAX | 2,254 | -0.071 | -0.002 | -1.72 | 923 | +0.026 | +0.086 | +0.19 | -0.148 .. -0.006 |
0 of 2 pass. W1 negative in every year; W2 negative in 2022 and 2023 (-0.12, -0.14), about zero in 2024-25. No market is positive in both periods. Indices by market (DEV / VAL): DAX -0.108 / +0.170, DOW -0.100 / +0.041, NSDQ -0.109 / -0.086, SP +0.031 / -0.021.

## The in-sample illusion (the main finding)
The configurations his process selects averaged **+0.362 R a trade** over the 3 months they were selected on, and **-0.141 R a trade** in the month after; across 1,828 market-months the correlation between the two is +0.028. Choosing the best of thousands of time/box/R:R/direction sets on 3 months (then the better of two on 6) finds the luckiest set, and luck does not repeat: what the selection window shows is selection, not edge. The process does beat picking a random candidate (placebo -0.15 to -0.20 R) only because the random pick includes more of the costliest sets; before costs both are zero.

## Reading
A trader who follows the video faithfully on MT5 broker prices 2022-2025, re-selecting every month, loses about 0.13 R a trade on all markets and breaks even before costs on the indices. Gross zero, as in BRK. Fixed 2-point targets on NQ futures could have different costs than MT5 broker CFDs, but the gross result (before any cost) is zero here too, so costs are not what is missing. Closed; HOLD sealed.
