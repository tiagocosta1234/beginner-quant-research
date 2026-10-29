# DAY2K-C result (2026-10-14): the daily 1:1 / 2,000 USD trade over all 46 MT5 broker - NO EDGE

Pre-registration `PREREG_DAY2K_C.md` (commits 88a35eb9, amendment A1 ab850ae6), engine `day2kc.py`, cells `data\si_ledgers\DAY2KC_cells.csv`, yardsticks `DAY2KC_yardsticks.csv`. 28 FX + gold, silver, Brent, WTI, SP, NSDQ, DOW, DAX, NIKKEI, ASX + 8 cryptos; up to 92 candidates a day. HOLD unopened.

## Gates
Truncation 40/40 (non-FX included). Oracle side (rules) +0.35..+0.65 R; ML with the label leaked +0.93..+1.00 R. Placebo worlds: rules 101-103 and ML 111-113: 0 survivors in all six. A1 (before any P&L): FX-only currency-strength features, empty in this universe, removed from the ML list after they crashed the first calibration.

## Result (28 cells)
S1 survivors **0**. The 24 rule cells lose -0.03..-0.15 R per trade in DEV (t -1.3 to -5.5): picking the largest normalised move over a universe that contains crypto picks altcoins, whose MT5 broker spread is 13% of a 0.4-ATR stop at the median (LTC 33%, ADA 23%, against FX 2.5%, gold 1%, US indices 1-2%). That is cost, not a signal. The 4 ML cells (price features + volume + asset class) are -0.02..-0.09 R in DEV' and -0.03..+0.03 R in VAL, the same as or worse than the baseline.

## Yardsticks (always long / always short, class average)
FX -0.01..-0.04 R either side; indices long +0.005..+0.010 (DEV), short -0.04..-0.06; metals long k0.7 +0.013 DEV / +0.054 VAL (t 0.6 / 1.4: the gold trend, not significant per trade); energy negative; crypto -0.19..-0.34 R in DEV (spread). Nothing reaches significance per trade except the crypto losses.

## MT5 broker view
A random daily pick over the 46 markets (T10:05, k0.4) passes an MT5 broker test in 32% of finished rolling starts and breaches in 68%; over the 28 FX pairs alone 43% / 57% (round A). Widening the pool lowers the odds because of crypto costs.

## Reading
Three registered rounds (A: 24 FX rule cells; B: learned ranker with calendar and volume on FX; C: 28 cells over every MT5 broker market) find no daily 1:1 setup with an edge on MT5 broker prices 2021-12..2025. The only positive per-trade number anywhere is "long gold", which is the drift the live gold pair already harvests. A setup picked every day without an edge is a coin flip that passes about 32-43% of attempts and breaches the rest.
