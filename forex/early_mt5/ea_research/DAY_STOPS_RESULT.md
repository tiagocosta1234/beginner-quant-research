# Mandatory daily loss stop and daily profit stop, ranked by time to pass (2026-10-13, day_stops_grid.py)
the trader: "corrige o ranking, mas é obrigatório parar a perda diária naquele número (1000/1500/2000/2500) e parar o lucro diário naquele número (1000/1500/2000/2500)". Installed pair (SDB + XAU5 x size, CPI flat, ManualDip NOT included), minute-path simulator with BOTH stops built in (the day ends at the first of -L / +P: every open position closed, no more trades that day; otherwise at midnight), 5 sizes x 4 L x 4 P = 80 configurations. Bootstrap of the daily series (20,000 paths, 250 business days) with MT5 broker's rules ENFORCED: in-day low <= -2,500 or equity <= 92,000 is a breach, counted profit capped at 2,000 a day, pass at +8,000 counted (or the pass lock), fresh account, MIX of the MT5 broker and FT pools. Full table: D:\finance\si_ledgers\DAYSTOPS_all.csv.
## Ranking by median business days to pass (the fastest rows are NOT usable)
| # | size | loss stop | profit stop | median bd to pass | pass % | breach % | passed within 44 bd % |
|---|---|---|---|---|---|---|---|
| 1 | x5 | 2500 | 2000 | 12 | 13.6 | **86.4** | 13.5 |
| 2 | x5 | 2500 | 2500 | 12 | 10.6 | **89.4** | 10.6 |
| 3 | x5 | 2500 | 1500 | 15 | 15.8 | **84.2** | 15.7 |
| 4 | x3 | 2500 | 2000 | 18 | 23.9 | **76.1** | 22.7 |
| 5 | x3 | 2500 | 2500 | 18 | 20.9 | **79.1** | 19.8 |
A loss stop of 2,500 IS the MT5 broker breach line, so any overshoot past the stop is a breach: 9-33% of starts breach even at x1.5 and 76-89% at x3 and x5. These rows are fast only because the few that pass do so before the account breaches; the median is taken over the passes. With breach <= 5% (22 of 80 configurations survive):
| # | size | loss stop | profit stop | median bd | pass % | breach % | passed within 44 bd % |
|---|---|---|---|---|---|---|---|
| 1 | x1.5 | 2000 | 2000 | 52 | 94.1 | 4.0 | 39.0 |
| 2 | x1.5 | 1500 | 2000 | 54 | 93.9 | 3.7 | 38.0 |
| 3 | x1.5 | 1500 | 2500 | 54 | 93.2 | 4.5 | 37.9 |
| 4 | x1.5 | 1500 | 1500 | 61 | 92.7 | 3.8 | 30.7 |
| 5 | x2 | 2000 | 1000 | 65 | 92.2 | 4.9 | 27.3 |
| 6 | x1.5 | 1000 | 2000 | 67 | 92.9 | 3.4 | 27.8 |
| 7 | x1 | 2000 | 2000 | 68 | 94.2 | 0.7 | 26.9 |
Best passed-within-44-days among all 80: x5 loss 1500 profit 2000 (48.9%, breach 20.6%), x5 1500/1500 (48.8%, breach 13.6%), x2 2000/2000 (46.1%, breach 8.8%).
## Baseline without the profit stop (same engine, pair only, loss stop 1500 = the installed guard)
x1.0: median 68 bd, pass 94.9%, breach 0.6%, within 44 bd 26.7%. x1.5: median 49 bd, pass 94.1%, breach 3.9%, within 44 bd 42.3%. x2.0: median 50 bd, pass 85.5%, breach 13.3%, within 44 bd 37.7%.
## Reading
The mandatory profit stop does not shorten the pass: the best admissible configuration (x1.5, loss 2000, profit 2000: median 52 bd, 39.0% within 44) is slower than the same size without a profit stop (median 49 bd, 42.3%). Stopping the day at +P gives up the strong trend days; the +2,000 stop is the least harmful (MT5 broker counts at most 2,000 a day anyway) and the +1,000 / +1,500 stops cost the most. The loss stop works best at 1,500-2,000: 1,000 stops out too often, 2,500 equals the breach line. Faster rows exist only by accepting 9-90% breach. ManualDip is excluded; the numbers are replays on historical trade lists (see EPISODE_GAME_RESULT.md for the caveats).
