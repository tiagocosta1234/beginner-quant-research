# FX3: what the repo knows about EURUSD, USDJPY, GBPUSD (descriptive map, 2026-10-14; not a trial, no P&L opened)

the trader's goal (2026-10-14): "master trading EURUSD, USDJPY and GBPUSD". "Master" is defined here so it can be falsified:
a pre-registered rule on these three pairs with positive NET return (MT5 broker bid/ask, real costs), t above the Bonferroni bar in
DEV and VAL, positive in the untouched 2026 hold-out, and a sizing that does not breach the MT5 broker daily line. Nothing in the repo meets it.

## Cost wall (MT5 broker M1 bid/ask, 2025-01..2026-10, median, server hours 2-21)
| pair | spread (bp) | round trip (bp) | 1-minute sd, hours 10-17 (bp) | hour 0 spread (bp) |
|---|---|---|---|---|
| EURUSD | 0.46 | ~0.9 | 1.46 | 2.95 |
| GBPUSD | 0.45 | ~0.9 | 1.47 | 5.15 |
| USDJPY | 0.40 | ~0.8 | 1.63 | 4.52 |
No commission on account <acct>. A signal must earn more than ~0.9 bp per round trip; hour 0 (rollover) is 6-12x wider and is excluded by rule.

## Already tested on these pairs, all closed with no edge after cost
- FX_HOURS (working-hours drift), FX_NR7 (+fade), LONDON_FIX, FX_SESSIONS, ICT_SCAN, SEASONAL_HOUR (K3), CONFLUENCE_H1 / PANEL
  (indicator confluence, ridge, boosting), HF on real ticks (48 cells, calibrated), ML on 15-minute bars, MT5-calendar event study
  (5/15/60 min and tick level), ensemble of weak rules, free-form rule search (173k + 185k rules), DAY2K-K (next-day direction,
  best FX group 56% against the 80% asked), Reversal Detector (EURUSD R per trade -0.17), 1,220-EA batch and 28-pair EA screen.
- Only open lead: USDJPY in the 22:00 server bar, +0.77 bp per hour, cost 0.51 bp, t +4.3 on 2022-25, i.e. about +0.26 bp a day
  (~65 bp a year before any sizing). The 2026 hold-out for that single cell has NOT been opened (registered rule in
  PREREG_SEASONAL_HOUR.md). Even if it confirms, the size is too small to move a broker account.

## Reading
The three pairs are the most efficient and cheapest markets on the list. Cost is not the obstacle (0.9 bp round trip); the absence
of a predictive signal at 1 minute to 1 day is. Mastery here cannot be delivered by more price-only indicator work; only new
information (not public price patterns) or a different objective could change that, and neither has produced anything yet.
