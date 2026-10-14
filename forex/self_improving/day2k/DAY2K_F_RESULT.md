# DAY2K-F result (2026-10-14): round-number level reactions as the daily 1:1 setup - NO EDGE

Pre-registration `PREREG_DAY2K_F.md` (commit adc9017f), engine `day2kf.py`, cells `D:\finance\si_ledgers\DAY2KF_cells.csv`. 11 instruments (gold 25 USD grid, SP 50, NSDQ/DOW/DAX 250, six FX pairs at 0.0050 / USDJPY 0.50), first level cross of the day (10:06-20:00 server), trade FADE or CONTINUE with stop = target = 0.3 or 0.6 ATR20, mid-price level with half-spread entry cost, close 21:55. Control: grids shifted by 0.37 / 0.23 / 0.61 of the step. HOLD unopened.

## Gates
Oracle side +0.55..+0.91 R; truncation 53/53; shifted-grid placebos: 0 cells at t >= 3.10 (best t 2.18 / 1.77 / 1.74).

## Result (44 cells)
S1 survivors **0**; no cell reaches the DEV bar (t 3.10) or the difference bar. Win share of resolved trades 43-56% (fade 43-53%, continue 44-56%), i.e. the "P of a +2,000 day" stays around 50%.
Pattern worth recording (descriptive): fading a first touch of a round number does WORSE than fading a touch of a shifted level (all-instrument mean -0.032 R vs +0.006 R) and continuing through it does better (+0.004 R vs -0.031 R); 4 of 22 continue-cells have a difference t above 2 (XAUUSD k0.3, USDCHF k0.3 and k0.6, USDJPY k0.6). Round numbers behave slightly like magnets that price tends to run through, not like walls. The absolute continue result is about 0 R, below what the spread costs the other side, so it is not a trade.

## Reading
A level-reaction setup at round numbers adds a real but tiny structural effect (about 0.03 R relative to a shifted grid) and no absolute edge. Six registered rounds (A-F) now close the "one 1:1 setup a day" design with price-structure, calendar, rates, volatility, volume and level information on MT5 broker prices.
