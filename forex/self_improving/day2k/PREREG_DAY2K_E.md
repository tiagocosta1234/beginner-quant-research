# PREREG DAY2K-E - gold, a +/-2,000 day every day (about 99% resolved), side chosen with new information (written 2026-10-14)

the trader: "both chances should always add up to 100%", "go get whatever information source you need". Rounds A-D found no edge from price-only information; D left a lead (gold 24-hour continuation, best t 2.67, not confirmed).

## Trade object (fixed before any P&L; both resolve the day in about 99% of cases per the exploratory resolution check)
XAUUSD+ only, one trade a day, entry at the open of the bar T+60 s on the executable side, stop = target = k x ATR20, forced close at 21:55 (the remaining ~1-2% of days end with a partial result and are reported), tie in one bar = loss. Object O1: T 10:05, k 0.20 (98.9% resolved). Object O2: T 16:35, k 0.15 (98.0% resolved).

## New information (all free, all causal at T)
- Rates (FRED, from `D:\finance\data_macro`): 2-year nominal (DGS2), 10-year nominal (DGS10), 10-year real (DFII10), breakeven = DGS10 - DFII10. H.15 values for a date are published the next US afternoon, so on server day d only observations dated <= d minus 2 business days are used. Features: 1-day and 5-day changes of DGS2, DFII10, breakeven.
- Gold implied volatility GVZ and VIX (CBOE closes, `cboe/`): observations dated <= d minus 1 business day. Features: 1-day log change of each, GVZ percentile over the previous 250 observations.
- USD strength from the MT5 broker FX prices at T (mean signed 1-day and 5-day normalised change of the 7 USD pairs, the round-B code).
- Flow calendar from the date: business days to month end, first business day of the month, quarter-end window (last 3 business days of Mar/Jun/Sep/Dec), weekday.
- Kept from round D: m1, m5, am, pdh, pdl, apos, rr, spr, the MT5 USD calendar surprise (flipped) and USD importance-3 events ahead.
Tried and not usable: SPDR GLD holdings (the public archive URL returns a PDF, not data), Yahoo GC/GLD/ZN daily (ends 2025-01, no volume), retail sentiment (no free history).

## Trials (8) and acceptance
Per object: (1) HGB classifier (depth 3, 100 iterations, lr 0.06, min leaf 60) and (2) L2 logistic regression (standardised, C = 0.1), both predicting "long beats short" and taking the predicted side; walk-forward, quarterly refit, expanding window, scored from 2022-12-01; (3) rule REAL: side = opposite of the 1-day DFII10 change (no change: skip); (4) rule USD: side = opposite of the 1-day USD strength at T. 2 objects x 4 = 8 trials. Bonferroni for 8, one-sided 5%: DEV block-t >= 2.50 and mean R above the baseline; VAL 2025: mean R > 0, block-t >= 1.65, >= 200 days. The figure the trader asked for, the win share of resolved days (P of a +2,000 day), is reported for every cell with the always-long and the 24-hour-continuation yardsticks next to it. HOLD 2026-01-01..2026-09-30 opened once only for a survivor.

## Gates
Positive control (label leaked into both models, rules with oracle side) > +0.3 R; placebo worlds (labels permuted across days for the models, seeds 141-143; random sides for the rules) 0 survivors each. Causality: the lag rules above are checked in the dry-run by printing, for 5 random days, the dates of the observations used.

## Dry-run record (2026-10-14, before any cell P&L)
O1 (10:05, k 0.20): 1,005 valid days, 99.65% resolved by stop or target; O2 (16:35, k 0.15): 1,005 days, 99.15% resolved. Lag check on 5 random days: rates observations dated 2 business days before the trading day, GVZ/VIX 1 business day before (e.g. 2023-02-17 uses DGS2/DFII10 of 02-15 and GVZ of 02-16). Coverage 100% for the macro and calendar features, 97% for USD strength. The FRED breakeven download hung; breakeven is computed as DGS10 - DFII10 from files already on disk (same definition as T10YIE).
