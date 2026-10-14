# DAY2K-B result (2026-10-14): a learned quality score for one 1:1 setup a day - NO EDGE

Pre-registration `PREREG_DAY2K_B.md` (commit 7349fd84), engine `day2kb.py`, cells in `D:\finance\si_ledgers\DAY2KB_cells.csv`. Same trade object and outcome matrix as `DAY2K_RESULT.md`. 28 MT5 broker FX pairs x 2 sides = 56 candidates a day; the model's top candidate is the day's single setup. Walk-forward, quarterly refit, expanding window, scored from 2022-12-01. HOLD (2026-01-01..08-14) never loaded.

## Information added versus round 1
Currency strength (8 currencies aggregated over the pairs containing them, 1 and 5 days), MT5 economic-calendar surprises already published that day (impact = actual vs forecast, 87.5% agreement with the sign of actual - forecast), importance-3 events due in the next 4 hours, tick-volume ratio since 01:05, Asian-range position and size, previous-day high/low distance, 20-day change, range ratio, spread/ATR, weekday.

## Gates
Truncation 40/40 identical; positive control (realised label leaked in): dev R +0.80..+1.00 (pipeline sees an edge); placebo worlds 91-93 (labels permuted across days): 0 survivors, best DEV' t 0.90 / -0.35 / 0.05.

## Result (10 cells)
S1 survivors **0**. DEV' (about 540 days OOS per cell): every ML cell is between -0.032 and 0.000 R, t between -1.2 and 0.0, i.e. the same as the no-skill baseline of the same (T,k) (-0.019..-0.034 R = spread). VAL (259 days): -0.056..+0.011 R, t -1.29..+0.34. FULL (calendar + volume) is no better than PRICE: the new information adds nothing the ranker can use at this horizon. The currency-strength hand rule: T10:05 -0.004 R (t -0.09, VAL +0.018), T16:35 -0.043 R (t -1.40, VAL -0.098, t -2.20).
Power: about 540 DEV' days give SE about 0.043 R: an edge of +0.12 R or more would have shown; a smaller one would not.

## Reading
A tree model that sees price structure, cross-pair currency strength, the calendar surprise and activity cannot rank the 56 daily candidates better than chance for a stop-and-target trade held up to 12 hours. Together with `DAY2K_RESULT.md` this closes the "one 1:1 FX setup a day, picked by a rule or a model" design on MT5 broker data: nothing to deploy, no HOLD opened. The cost of the trade object itself (spread about 3% of R) means a real edge needs to be about +0.05 R just to break even.
