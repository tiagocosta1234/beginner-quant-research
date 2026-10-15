# PREREG_ORB11_GRID - is the stop / target the problem of the trader's 30-minute ORB? (written 2026-10-15, before any P&L; commit time = registration time)
the trader: "(original wording omitted)".

## Entries (fixed, exactly ORB11)
30-minute box at 08:00 London and 09:30 New York, first touch of the high -> long (ask), of the low -> short (bid), all 46 MT5 broker symbols, MT5 broker M1 bid/ask; plus ORB11's random-entry control (random minute in the same window, random side).

## Exit grid (in box widths B = box high - box low, measured from the fill price)
- Stop distance SL in {0.10, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2, 3} B (1.0 = about the other side of the box).
- Target TP in {0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 10} x SL, plus NONE (hold to the session end).
- 9 x 11 = 99 exits x 2 sessions x 46 symbols = 9,108 cells, plus pooled cells (session x class, session x all).
- Same-minute stop and target: stop first (pessimistic). Stops fill at the level or the minute's open if it gapped through. Exit at the session end (17:00 London / 15:55 New York, capped 22:55 server) if neither is hit. Result in R (net P&L / SL distance) and in box units.

## Tests
1. Exit can create an edge only if the BREAKOUT grid beats the RANDOM-ENTRY grid: for every pooled cell, the best of the 99 exits on breakouts vs the best of the 99 exits on random entries (same dates). If breakouts' best is not clearly above random's best, the exits are not the problem.
2. Selection honesty: choose the best exit per (symbol, session) on DEV 2022-24 only, then read VAL 2025 and 2026 for the chosen exit (walk-forward). Report the mean VAL / 2026 result of the 92 chosen cells and how many stay positive.
3. A cell passes only if: DEV+VAL daily t >= 4.4 (one-sided 5% over 9,108 + pooled tests), mean > 0 in DEV, VAL and 2026, and better than random's same exit.

## Honest prior
This morning's BRK_EXITS found exits move the result by <= 0.03 R and that exits on random entries look the same as on breakouts. Expected: no passing cell; the walk-forward chosen exits lose out of sample.
