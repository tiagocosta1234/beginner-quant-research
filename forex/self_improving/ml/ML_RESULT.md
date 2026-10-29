# Machine learning on the raw 15-minute bars: result (2026-10-13)

Pre-registration: PREREG_ML.md (with Amendment 1). Code: ml_lab.py, check script ml_hour_check.py (scratchpad). Ledgers: data\si_ledgers\ML_real_run1_rollover.csv, ML2_real.csv, ML2_placebo5{4,5,6}.csv (and the calibration ML_placebo5{1,2,3}.csv). 2026 never loaded.

## Setup
Raw input: the last 48 bars (12 hours) of a market, OHLC of the bid as log(price / current close) over the bar volatility, plus two M1-derived numbers per bar (1-minute realised variance over volatility squared, spread over its median), hour and weekday encodings and the log of the volatility regime: 293 numbers, no hand-made indicator. One XGBoost model per class (idx, fx, cmd, crypto) and horizon (1 hour, 4 hours, 1 day) = 12 cells, trained on window A (2022-01..2023-06), early stopping and signal threshold on B (2023-07..2024-12), looked at on VAL (2025) once per design. Entries on the grid of spacing H (no overlap), real bid / ask and the conservative flat carry. Cell passes only if VAL net >= +3 bp, >= 100 trades, >= 20 weekly clusters and excess p < 0.05/12.

## Run 1 (no rollover restriction): an artefact
0 of 12 pass the net floor, but fx H=4 had VAL IC +0.0997 and excess z 17.2 (net -1.7 bp) and fx H=16 IC +0.059, z 4.3, far above the placebo ceiling (IC 0.024, z 2.8). By server hour the IC was +0.52 at hour 0, +0.40 at hour 23 and about 0 elsewhere; without those two hours +0.020; the most used inputs were the hour and the spread of the last bars. The model learned the rollover spread artefact (bid moves as the spread widens and normalises around the 17:00 New York rollover), already found by the free-form search in v4 and not carried into this pre-registration (my omission). Amendment 1: no decision and no exit in server hours 23 and 0. Disclosure: 2025 had been looked at once, so the amended VAL is not a clean one-look; a pass would have needed the sealed 2026 as the clean confirmation.

## Calibration (amended code): PASSED
Never-seen placebo worlds 54, 55, 56: 0 of 12 cells pass in each; noise ceiling over the 36 cells: max VAL IC +0.0199, max excess z 1.62.

## Amended real run
| class | H (1h / 4h / 1d) | VAL IC | VAL net bp per trade | VAL excess z |
|---|---|---|---|---|
| fx | 4 / 16 / 96 | +0.0056 / +0.0012 / +0.0040 | -1.0 / -0.8 / -0.2 | -1.27 / -0.32 / -0.02 |
| idx | 4 / 16 / 96 | +0.0005 / +0.0071 / +0.0051 | -1.6 / +1.1 / -1.9 | -0.77 / 1.03 / 0.79 |
| cmd | 4 / 16 / 96 | -0.0080 / -0.0145 / -0.0210 | -7.4 / -3.7 / -45.7 | -1.84 / 0.72 / -2.29 |
| crypto | 4 / 16 / 96 | +0.0038 / -0.0162 / -0.0097 | -21.9 / -24.0 / -25.1 | 0.40 / -0.98 / -0.61 |
0 of 12 cells pass. Max VAL IC +0.0071 and max excess z 1.03: BELOW the placebo noise ceiling (0.0199 and 1.62). No cell reached a net mean of +3 bp. The convolutional network of the pre-registration (run only if the trees showed a signal) was therefore not run.

## Verdict
A flexible learner on 12 hours of raw 15-minute bars finds nothing out of sample in 2025 once the rollover spread artefact is excluded: information coefficients of about 0.00-0.01 (the placebo ceiling is 0.02), net means below zero in almost every cell. The only large signal it found (IC 0.10) is the rollover spread effect, which cannot be traded. Nothing goes to the environment, the add-on test or the tester; 2026 not read; the installed system stays.
