# BRK-HOURS result (breakout day round 25, 2026-10-15 13:41, local clock): no hour of the day makes 60-minute breakouts pay
Pre-registration `PREREG_BRK_HOURS.md` (committed by the 13:40 autosave, before the run), engine `brk_hours.py` (truncation PASS), rows `D:\finance\si_ledgers\BRK_HOURS.parquet`, cells `D:\finance\si_ledgers\BRK_HOURS_cells.csv`, chart `D:\finance\scratch\charts\BRK_HOURS.png`. 986,184 breakouts (46 markets x server hours 1..19 x days 2022-2026). Hour 20 cannot exist under the frozen rules (its order window ends at 23:00 after the 22:55 exit), so there are 95 cells, not 100.

**0 of 95 cells pass.** Net R is negative in 87 of 95 cells in 2022-24 and 86 of 95 in 2025. Breakout information (net minus a random entry) averages +0.003 R (DEV), +0.012 (VAL), +0.018 (2026): about half the cells above zero, i.e. noise around a tiny positive value.
| best cells by DEV t | DEV | VAL | 2026 | random control DEV / VAL |
|---|---|---|---|---|
| index, box 16:00 server (= the US cash open, 09:00-10:00 NY) | +0.047 (t 1.38) | +0.081 | -0.049 | -0.034 / -0.075 |
| index, box 15:00 server (pre-open) | +0.054 (t 0.96) | +0.009 | +0.015 | +0.010 / -0.018 |
| index, box 19:00 server | +0.043 (t 0.86) | -0.027 | -0.074 | |
| metal, box 15:00 server | +0.023 | -0.038 | -0.281 | |
| fx, box 08:00 server (London 06:00) | -0.026 | -0.085 | -0.109 | -0.086 / -0.113 |
The map by class: crypto loses at every hour (-0.06..-0.37 R; spreads), energy is least bad around the US session (server 15-17), FX is least bad around the London open and the US open (-0.02..-0.03 in DEV) and negative in every hour of 2025-26, metals and indices are near zero only around the US open (server 15-16). Only one cell is positive in all three periods (index, 15:00 server: +0.054 / +0.009 / +0.015, t < 1).

Reading: the hour of the day matters only through liquidity (spreads and box width): breakouts are least bad when the big session opens, and nowhere positive after costs. This confirms round 9 (anatomy) and round 10 (cost) from a different angle; there is no hidden "right hour".
