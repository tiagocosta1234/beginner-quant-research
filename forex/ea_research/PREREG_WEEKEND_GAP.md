# PREREG_WEEKEND_GAP - fading the weekend reopen gap on MT5 broker (written 2026-10-15, before any P&L; commit time = registration time)

## Idea
Practitioner lore says weekend gaps "fill": the Sunday reopen often jumps on thin liquidity and drifts back during Monday. Not tested in this repo (the breakout rounds tested cash-open gaps on indices at 16:30 server, not the weekend reopen). MT5-native, one decision a week per market.

## Rules (fixed now)
- Friday mark: last bar at or before 22:55 server on the last trading day of the week (bid/ask mid). Monday entry: the bar opening at 01:05 server on the first trading day of the next week (hour 0 is excluded by the standing rule; the reopen hour itself is never traded). Gap = entry mid / Friday mid - 1.
- Trade only if |gap| > 2 x the entry spread (relative): FADE the gap (sell after an up gap at the bid, buy after a down gap at the ask). Exit at the bar opening at 10:00 server (E1) or 16:00 server (E2) the same day, at the opposite side. One trade per market per week. P&L in bp of price, net of MT5 broker's real spread at entry and exit.
- Cells (4 trials, Bonferroni over 4): G1 FX 7 majors (EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD) exit 10:00; G2 FX exit 16:00; G3 SP, NSDQ, DAX, NIKKEI, XAUUSD exit 10:00; G4 same exit 16:00.
- Statistic: Monday clusters (all trades of a cell on the same Monday averaged), t over Mondays.

## Periods
DEV 2022-01..2024-12, VAL 2025, OOT 2020-01..2021-11 (HistData M1, bid only: the ask is bid + MT5 broker's median spread at that server hour in 2022-24; for 01:05 that is the hour-1 median; DAX not available in OOT, PREREG_SWAPFREE_DRIFT Amendment 1), HOLD 2026-01..2026-10-02 one look for a passer. Real-tick check of a passer on MT5 broker ticks 2025-10..2026-10.

## Acceptance (all required)
1. DEV+VAL Monday-cluster t >= 2.50.
2. Mean > 0 in DEV, VAL and OOT.
3. HOLD mean > 0.
4. Real-tick mean >= 75% of the M1 mean on the same weeks.

## Dry run
Counts of Mondays and trades per cell and period, median entry spread at 01:05 vs the rest of the day (if 01:05 spreads are still rollover-wide, say so), truncation test (the trade decision uses only bars up to 01:05), hand check of one week.

## Honest prior
Reopen gaps on CFDs are often quote artefacts that the broker's first prints already correct before 01:05; what is left at 01:05 may be real news (which continues). Prior about 10%.
