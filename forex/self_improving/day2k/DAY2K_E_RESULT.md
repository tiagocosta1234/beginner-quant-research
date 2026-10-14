# DAY2K-E result (2026-10-14): gold, +/-2,000 almost every day, side from new information - NO EDGE

Pre-registration `PREREG_DAY2K_E.md` (commit ae9e4fda), engine `day2ke.py`, cells `D:\finance\si_ledgers\DAY2KE_cells.csv`. Gold only, one trade a day with stop = target small enough that 99.2-99.7% of days end at exactly +2,000 or -2,000 (the trader's "both chances add up to 100%"). HOLD unopened.

## Information used (free; paid feeds not bought)
Rates from FRED on disk (2-year, 10-year real, breakeven = 10-year - real; lagged 2 business days), CBOE GVZ and VIX (lagged 1 business day), USD strength from the 7 MT5 broker USD pairs at the decision time, flow calendar (days to month end, first day, quarter end, weekday), MT5 USD calendar surprises and upcoming events, price structure. GLD holdings (SPDR archive returns a PDF), Yahoo futures (end 2025-01) and retail sentiment (no free history) were not usable.

## Gates
Leak / oracle control +0.93..+0.96 R; placebo worlds 141-143: 0 survivors (best DEV t 0.71 / 0.89 / 0.84).

## Result (8 cells)
S1 survivors **0**. Win share of resolved days (= P of a +2,000 day): DEV 44.1-53.7%, VAL 47.4-55.6%; no cell is above 50% in both periods with significance. Best DEV: O1 HGB 53.7% (t 1.55) -> VAL 49.8%. REAL rule (gold against the real-yield change): DEV 44.1% (t -3.2, wrong sign) -> VAL 55.6% (t 1.59): sign flip. Yardsticks: always long 51.2% / 49.6% (O1), 47.7% / 47.6% (O2); the round-D 24-hour-continuation lead is 48.0% / 49.4% (O1) and 49.9% / 51.2% (O2): it does not survive at stops this tight.

## Reading
When the stop is small enough that the day always resolves, the outcome is decided by intraday noise inside a fraction of the daily range, and no information tested here (price, rates, gold volatility, USD, calendar flows, macro surprises) moves the chance of a +2,000 day away from 50%. Five registered rounds (A-E) now close the "one 1:1 setup a day" design on MT5 broker data.
