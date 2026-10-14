# Pre-registration MPROFILE: market-profile (time-at-price) trading on every MT5 broker market (written 2026-10-14 ~22:00, before any code or result)
the trader: "try another way to analyze the chart" (after ANALOG, chart-shape memory, found nothing). Market profile reads the chart as an auction: where did the market spend its TIME yesterday (point of control POC, value area VA = 70% of the time around it), and does today accept or reject that value? Untested here: the swing-level S/R family, SD zones and the ICT scan used swing highs/lows and candle structures, never the time-at-price distribution. The four classic profile plays are tested as written in the trading literature (Dalton, "Mind over Markets"; the "80% rule").

## Data and clock
MT5 broker M1 bid/ask, 46 markets, server clock, data loaded only before 2026-01-01 (2026 sealed). Mid = (bid + ask) / 2.
Profile of day D-1 (previous day of that market with at least 300 bars): server hours 01:00-22:59 (rollover hours 23 and 0 excluded), range split into 50 bins, each M1 bar spreads one unit of time evenly over the bins between its mid low and mid high. POC = fullest bin; VA grows from the POC, adding the fuller neighbour, until it holds 70% of the time; VAH/VAL = its edges, VAw = VAH - VAL.
Day D trading window: entries 02:05-18:00 server, every trade closed by 22:55. "Open" = mid at the 02:05 bar. Half-hour closes = mid close of the bars ending at :29 and :59. Entries at the open of the minute after the signal; a minute :00 is moved to :01 (first-minute rule). Long at the ask, exits at the bid (short mirrored). Stop and target checked on the bid (long) / ask (short); if both are hit in one bar the stop counts; a stop gapped through fills at the bar open; unresolved trades close at the 22:55 open (on an early-close day: the open of the last bar of the day). At most one trade per cell per market per day.

## Cells (direction fixed by the rule; one-sided)
1. **VA80 (80% rule)**: open outside the VA; the first two consecutive half-hour closes back inside the VA (from 02:29, signal by 18:00) -> trade toward the far edge. Target = far edge; stop = 0.5 VAw beyond the edge price came back through.
2. **DRIVE (open-drive, value rejected)**: open outside the VA and all six half-hour closes 02:29-04:59 stay outside on the same side -> at 05:05 trade away from the VA. Target = 1 VAw; stop = the near VA edge, at least 0.25 VAw away.
3. **EDGE (fade the value edge)**: open inside the VA; first touch of VAH or VAL (03:00-18:00; a bar touching both = no trade) -> fade toward the POC. Target = POC; stop = 0.5 x (edge - POC) beyond the edge; skipped if the POC is within 0.1 VAw of that edge.
4. **NPOC (naked POC magnet)**: at 10:05, if yesterday's POC has not been traded today (02:00-10:04 range) -> trade toward it. Target = POC; stop at the same distance on the other side (1:1); skipped if the distance is below 0.2 VAw.
P&L in R = signed (exit - entry) / |entry - stop| with real bid/ask (net); a gross (mid) R is reported next to it.

## Periods, statistics, gates
DEV 2022-01..2024-12, VAL 2025, HOLD 2026-01-01..09-30 (sealed; one look only for a cell that passes 1-5). Daily portfolio series = mean net R of the trades entered that day; Newey-West t, lag 1.
1. DEV mean net >= +0.05 R and t >= 2.50 (Bonferroni, 4 one-sided cells).  2. VAL mean net > 0 and t >= 1.65.  3. Net positive in at least 3 of the 4 years 2022-2025.
4. Placebo levels: 3 worlds (seeds 95-97) in which each day's VAL/POC/VAH are shifted together by u x VAw, u = random sign x Uniform(0.5, 1.5), same rules; the real cell's DEV t must exceed the 95th percentile of the 12 placebo cells' DEV t.
5. No single market makes more than 40% of the DEV net R.
Lesson from ANALOG applied: no two-sided gate; a negative cell is a negative cell.

## Dry-run (no P&L)
Counts per cell and period; truncation test (levels and every trade entered before a cut identical when the data after the cut is removed); hand check of one day's levels and one trade.

## Honest prior
About 4%: market profile is a different reading of the same price data (time at price instead of swing points); the S/R random-level placebo found swing levels no better than random ones.
