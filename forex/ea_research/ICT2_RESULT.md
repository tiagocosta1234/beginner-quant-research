# ICT2 result (2026-10-14 ~22:20): SMT divergence, ICT 2022 model, NWOG on MT5 broker - NO EDGE
Pre-registration `PREREG_ICT2.md` (commit c3d5d0a6), engine `ict2.py`, trades `data\si_ledgers\ICT2_trades.parquet`, cells `ICT2_cells.csv`. 2026 never loaded.

## Dry-run
Truncation test PASS (EURUSD, XAUUSD, SP, DAX); hand check EURUSD LONDON 2022-07-27: EURUSD traded 0.1 pip under its Asian low (1.01277 vs 1.01278) while GBPUSD stayed above its own (1.20400 vs 1.20352), close back inside -> bullish SMT, long 10:01 server, stop at the low. SMT runs on 13 markets (SP has two twins), as corrected in the pre-registration before any P&L.

## Cells (net R with real bid/ask; gross = mid; t on the daily portfolio, Newey-West lag 1)
| cell | DEV n | DEV net | DEV gross (t) | VAL n | VAL net | VAL gross (t) | win % DEV |
|---|---|---|---|---|---|---|---|
| SMT (2R target) | 5,827 | -0.124 | +0.009 (-0.9) | 1,917 | -0.176 | +0.021 (-0.1) | 30.2 |
| MSS2022 (sweep -> MSS -> FVG limit, 2R) | 6,558 | -0.087 | +0.039 (+1.8) | 2,304 | -0.105 | +0.054 (+1.6) | 32.0 |
| NWOG (1:1 to Friday close) | 2,054 | -0.131 | -0.037 (+0.1) | 849 | -0.134 | -0.061 (-0.3) | 43.8 |
Placebo (same trades re-entered at random minutes of random days, seeds 41-43): DEV net -0.07 to -0.23 R, gross -0.04 to +0.02, DEV t -2.9 to -10.9 (95th percentile -3.01). 0 of 3 cells pass; every cell fails gates 1-3 (negative net in every year 2022-2025).

## Reading
- **SMT divergence adds nothing.** When one market sweeps its range and its twin does not, the swept market's reversal is worth +0.009 R before costs (DEV) and +0.021 (VAL): the same as no signal. Win rate 30% at a 2R target is what a random 2R bracket gives.
- **The 2022 model is the closest to information, and it is not enough.** Gross +0.039 R (t 1.8) in DEV and +0.054 (t 1.6) in VAL, but the killzone carrying it flips (London +0.061 in DEV, New York +0.121 in VAL), and the spread takes 0.13 R a trade: net -0.09 / -0.10. Its placebo is costlier (market entries instead of limits), so its better t against the placebo is a cost difference, not skill.
- **The new-week opening gap is not a magnet.** Gross -0.04 / -0.06 R; FX gaps keep running (gross -0.10 / -0.07). Gold/silver (+0.19 / +0.17 gross on 99 / 38 trades) is too small to read and was not a registered cell.
With `ICT_SCAN_RESULT.md` (sweeps, FVG, killzones, Silver Bullet), `FIB_OB_RESULT.md` (fib + order block), the ManualFVG real-tick test and this round, the core ICT toolkit has been tested causally on MT5 broker prices 2022-2025 and none of it beats the spread. Closed; HOLD stays sealed.
