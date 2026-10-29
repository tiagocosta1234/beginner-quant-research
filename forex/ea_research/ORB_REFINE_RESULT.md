# ORB-REFINE result (2026-10-15 ~10:40 local): six refinements of the card's two breakouts - none passes; one lead
Pre-registration `PREREG_ORB_REFINE.md` (commit 6a0a66c7), engine `orb_refine.py`, trades `data\si_ledgers\ORB_REFINE_<MKT>.parquet`, cells `ORB_REFINE_cells.csv`. 2026 never loaded.
Dry-run: truncation test PASS both markets; hand check 2024-06-12: gold box 2,311.96-2,315.36, short filled 2,311.96 at 10:34 server (stop 3.40 = the box); Nasdaq box 19,343.92-19,474.42, long filled 19,474.42 at 17:14 server = 10:14 NY (stop 65.25 = half the box).

## What the card's two trades did (base, net R per trade, all days)
| | 2022 | 2023 | 2024 | 2025 | DEV t | win rate |
|---|---|---|---|---|---|---|
| Gold London breakout | +0.037 (245) | +0.082 (254) | -0.106 (254) | +0.081 (237) | +0.08 | 33-40% |
| Nasdaq New York breakout | +0.042 (248) | +0.067 (251) | +0.183 (254) | +0.011 (253) | +1.91 | 35-42% |
Gold is zero (DEV +0.004 R, VAL +0.081 R, t 0.93). Nasdaq is positive in all four years (DEV +0.098 R, t 1.91; VAL +0.011 R), not significant.

## The 12 cells (net R per trade; gates: 1 DEV >= +0.10 R and t >= 2.65; 2 VAL > 0 and t >= 1.65; 3 >= 3 positive years; 4 beats random subsets; 5 >= 100 trades)
| cell | Gold DEV / VAL | Nasdaq DEV / VAL |
|---|---|---|
| A trend-with | +0.017 / +0.171 | **+0.185 (t 2.54) / +0.100 (t 0.84)**, every year positive, beats random subsets (95th 0.181): gates nnYYY |
| B small box | +0.009 / +0.122 | +0.077 / +0.068 |
| C overnight-aligned | +0.018 / +0.199 | +0.166 / -0.091 |
| D fast trigger | +0.002 / -0.033 | +0.113 / -0.044 |
| E regime skip (last 20 trades > 0) | +0.035 / +0.138 | +0.070 / -0.040 |
| F regime flip (fade when failing) | -0.010 / +0.036 | -0.044 / -0.149 |
0 of 12 pass. The regime ideas (E, F: switch on the strategy's own recent results) do not help; flipping to the fade when breakouts have been failing makes both markets worse.

## Reading
Breakouts do not "change pattern" in a way the last 20 trades can see: the regime rules add nothing. The only refinement with a consistent shape is taking the Nasdaq New York breakout only in the direction of the daily trend (previous close vs 20-day average): +0.185 R a trade in 2022-24 and +0.100 R in 2025, positive in each year, but it misses the DEV bar (t 2.54 < 2.65) and is not significant in 2025 (128 trades). A lead, not an edge; HOLD stays sealed. The base Nasdaq trade itself is the only card leg positive in all four years; the gold leg is a coin flip.
