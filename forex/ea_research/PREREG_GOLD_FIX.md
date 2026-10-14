# Pre-registration GOLD-FIX: trading around the LBMA gold price auctions (written 2026-10-14 ~20:15, before any code or result)
the trader: "we cook up a new idea for a system" -> chose "gold fix flows". Mechanism: the LBMA Gold Price is set twice a day in London (10:30 and 15:00 London time). Banks, ETFs, miners and central banks that must trade AT the benchmark create predictable order flow around it (literature: Caminschi & Heaney 2014, pre-fix price leakage; Abrantes-Metz & Metz, PM-fix price patterns). Gold is the only market where this repo has found an edge; an intraday gold leg would add little correlation to the swing pair. Related lead: DAY2K-D found gold continuation at 16:35 server (14:35 London, just before the PM fix) positive every year 2022-25 (DEV t 2.67, VAL t 0.96).
Untested in this repo for gold (the London-fix family LF tested the 16:00 WM/R FX fix on USD majors only).

## Data and clock
MT5 broker XAUUSD M1 bid/ask (server clock, Europe/Athens), London times converted with time zones (Athens and London share EU DST rules, the offset is +2 h). London business days only; a day is skipped if any needed minute bar is missing. Entry/exit at the OPEN of the stated minute: long at the ask, exit at the bid (short mirrored); 0.1 bp slippage per side. Net basis points per trade, one trade per day per cell.

## Cells (6): for each auction F in {AM 10:30, PM 15:00}
- PRE (momentum into the fix): signal = mid(F-15) / mid(F-60) - 1; trade in its sign from F-15 to F (exit at the open of minute F).
- POST (fade the fix move): signal = mid(F+5) / mid(F-30) - 1; trade AGAINST it from F+5 to F+65.
- DRIFT (unconditional): short from F-30 to F+5 (the classic "price falls into the fix" pattern).
Statistics are two-sided: a significantly negative mean means the opposite direction works and is reported as such (no new cell).

## Periods and gates
DEV 2022-01-03..2024-12-31, VAL 2025, HOLD 2026-01-01..2026-09-30 (sealed; opened once only for a cell that passes 1-4).
1. DEV |t| >= 2.64 (two-sided 5% / 6 cells), mean |net| >= 1.0 bp.  2. VAL same sign, t >= 1.65 in that direction.  3. Same sign in at least 3 of the 4 years 2022-2025.
4. Placebo times: the same three cells at six fake auction times (London 08:45, 12:30, 16:30, 17:30, 18:30, 19:30); the real cell's |DEV t| must exceed the maximum |DEV t| over the 18 placebo cells of its kind... (all 18 placebo cells together: the cell must beat the 95th percentile of |t| over all placebo cells and both sides).
Robustness reported, not gated: PM cells without days that have a high-impact USD release at 10:00 New York (15:00 London) from the MT5 calendar (coverage to 2026-08-15); by-year table.
Honest prior: ~10% (a documented anomaly, but the post-2015 auction reform and electronic trading may have removed it).
