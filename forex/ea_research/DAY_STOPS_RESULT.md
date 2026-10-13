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

# CORRECTED ranking: the day is the episode (multi-day, ends ONLY at +P or -L of equity), with MT5 broker's daily -2,500 enforced (2026-10-13, episode_mt5.py)
The ranking above reset the day at midnight, which is not the trader's rule ("(original wording omitted)"). Here no day ever closes in the middle: the episode runs across days and weekends until equity since its start touches +P or -L, then everything is closed and a new episode starts at once. MT5 broker's daily loss rule is enforced inside it: any server day in which equity falls 2,500 or more from the day's 00:00 level flags a breach on that episode (positions carried over days count their floating P&L). Account pass = cumulative episode results reach +8,000 (before MT5 broker's 2,000-a-day counting cap, so optimistic), breach = cumulative -8,000 or a daily-loss breach, evaluated from every starting episode of the pool. 5 sizes x 4 L x 4 P x 2 pools = 160 runs. Pair only (ManualDip excluded). Full table: D:\finance\si_ledgers\EP8_merged.csv.
Fastest rows (breach is the problem): x5 P2000 / L2500: 7 bd MT5 broker, 15 bd FT but breach 84% / 68%; x5 P2000 / L2000: 8 / 16 bd, breach 73% / 61%; x3 P2500 / L2000: 9 / 32 bd, breach 82% / 45%. Every configuration with a median under ~25 business days breaches in at least 40% of the starts.
Only 5 of the 80 configurations keep the breach at or under 5% in BOTH pools, and they are slow (profit limit P, loss limit L; median business days to +8,000, MT5 broker pool / FT pool; pass % MT5 broker / FT; breach % MT5 broker / FT; episodes ending at +P %):
| size | P | L | bd MT5 broker / FT | pass % | breach % | hit % |
|---|---|---|---|---|---|---|
| x1 | 1500 | 1000 | 54 / 118 | 100 / 100 | 0 / 0 | 67 / 63 |
| x2 | 1000 | 1000 | 57 / 112 | 100 / 99 | 0 / 1 | 64 / 64 |
| x2 | 1000 | 1500 | 62 / 91 | 100 / 98 | 0 / 2 | 72 / 75 |
| x1 | 1500 | 1500 | 67 / 141 | 100 / 100 | 0 / 0 | 76 / 71 |
| x1 | 1000 | 1000 | 74 / 148 | 100 / 100 | 0 / 0 | 69 / 67 |
For comparison, the installed rules (no episodes): 33 / 64 bd median to pass with breach 2.3% / 6.1%. Under the "days only end at the limits" rule no configuration is faster than the installed system at a breach rate near it; the safe ones need about twice as long (54-74 bd MT5 broker, 91-148 bd FT), and the fast ones breach 45-90% of the time because a multi-day episode holding positions loses 2,500 or more inside one server day. Replays of historical trade lists; ManualDip, swap and the 2,000-a-day counting cap are not modelled.
