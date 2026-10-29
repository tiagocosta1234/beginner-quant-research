# ICT_GRID_RESULT - every combination of the core ICT concepts on every MT5 broker symbol (2026-10-15, local clock 18:16)
Pre-registration PREREG_ICT_GRID.md. Code ict_grid.py, output ICT_GRID_OUTPUT.txt, tables data/si_ledgers/ICT_GRID_*. Dry run: truncation identical (22,186 trades), killzone times checked by hand.

## Verdict: 0 of 21,363 cells, 0 of 2,375 pools; no class pick survives 2025 and 2026, so no out-of-time check was triggered
8 entry models (sweep of prior-day / Asian liquidity, sweep + MSS, sweep + MSS + FVG limit, FVG continuation, BOS + order-block limit) x 4 killzones (London, NY AM, silver bullet, NY PM) x 3 biases (none, daily, premium / discount) x 5 targets (1R, 2R, 3R, opposite liquidity, 15:55 NY) x 46 symbols; 1,709,297 rule trades on MT5 broker bid/ask with a matched random trade (same day, killzone, stop distance and target) for each.
1. **Every model loses with every target** (all symbols, 2022-25): sweep reversals -0.15 R a trade, MSS -0.08, MSS + FVG -0.06..-0.09, FVG continuation -0.16, order block -0.18..-0.20. The target changes the result by <= 0.03 R. Every year 2022-2026 is negative (-0.10 to -0.19 R).
2. **Against the matched random trade:** sweeps and MSS market entries are no better than random (sweep_PD -0.15 vs -0.14). The limit-order models (MSS + FVG, FVG, OB) look 0.02-0.09 R better than their random twin only because a limit fills at the level while the twin pays the spread at market; they still lose.
3. **Killzones and bias:** silver bullet -0.113, NY AM -0.122, London -0.154, NY PM -0.203 R; bias none -0.146, daily -0.154, premium / discount -0.143. Neither helps.
4. **Cells:** highest t 4.07 (EURUSD MSS_PD NY AM daily-bias 1R, 87 trades, +0.344 / +0.461 / **-0.033**), bar 4.59; the matched null reaches 3.24; 335 of 21,363 cells are positive in all three periods.
5. **Pools (rule x class):** highest t 1.32 vs 1.51 on the null.
6. **Walk-forward (best of 480 per symbol on 2022-24):** DEV +0.331 -> 2025 **-0.181** -> 2026 **-0.242** R; 3 of 46 positive in both. The best rule per class on DEV is negative in 2025 for all five classes.

## Reading for the trader
Written as fixed rules, the ICT concepts (liquidity sweeps, market-structure shifts, fair value gaps, order blocks, killzones, daily bias, premium / discount, opposite-liquidity targets) lose on every MT5 broker market, in every killzone and every year, about as much as random entries with the same stops. Picking the best combination per symbol on 2022-24 gives +0.33 R a trade in sample and -0.18 / -0.24 R afterwards. If ICT works for a trader, it is in discretion that these rules do not capture; the way to show it is a written model or a log of real trades, tested the same way.
