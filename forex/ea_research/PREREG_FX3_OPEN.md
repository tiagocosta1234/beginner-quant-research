# Pre-registration FX3-OPEN: does the first hours of a regional equity session lead EURUSD, GBPUSD, USDJPY? (written 2026-10-14 before any code or result)

Goal context: the trader "master trading EURUSD, USDJPY, GBPUSD". Option 1 of the FX3 map: information from OTHER MT5 broker (MT5-native: prices only).
Mechanism: risk sentiment is revealed first in the home equity market of each region (Nikkei cash open -> JPY, DAX open -> EUR/GBP, SP/NSDQ open -> all);
FX may adjust with a lag of an hour or more. Earlier work used daily/hourly USD-basket, SP and gold features inside indicator models (CONFLUENCE_H1); it did
not test a registered session-to-session transfer with fixed local-time windows. This is a small family: 14 cells.

## Data and clock
MT5 broker M1 bid/ask `forex/data_mt5/<M>_M1_rates.parquet` (t is the SERVER clock, Europe/Athens naive; converted via tz_localize then to the exchange's local zone).
Markets: targets EURUSD, GBPUSD, USDJPY; drivers NIKKEI (Asia/Tokyo), DAX (Europe/Berlin), SP (America/New_York). Weekdays in the driver's zone.

## Rule (per cell, at most one trade per day)
- Driver window (local): NIKKEI 09:05-11:00, DAX 09:05-11:00, SP 09:35-10:30. Driver return D = mid close of the last minute / mid open of the first minute - 1,
  required >= 80% of the window's minutes present for driver and target; days with a half-day or holiday are skipped by that rule.
- Trade: side = sign(D) (risk-on = long the pair; for USDJPY long USDJPY, for EURUSD/GBPUSD long the pair). Entry at the open of the minute 5 minutes after the
  driver window ends, at ask (buy) / bid (sell); exit H = 2 h or 4 h later at bid/ask. Skip a trade whose entry or exit minute falls in server hours 23 or 0
  (rollover rule). No stop, no filter, no threshold.
- Result in bp of mid, net of the actual bid/ask paid + 0.1 bp slippage per side.
- Cells: USDJPY x {NIKKEI, DAX, SP}, EURUSD x {DAX, SP}, GBPUSD x {DAX, SP}, each with H in {2h, 4h} = 14 cells, plus the reversed sign reported (not traded).

## Periods and acceptance
DEV 2022-01-01..2024-12-31, VAL 2025-01-01..2025-12-31, HOLD 2026-01-01..2026-09-30 (looked at once, only for a cell that passes 1-3).
1. DEV net mean > 0 and |t| >= 2.9 (Bonferroni 14 cells, two-sided 5%), computed on daily trades with Newey-West-free plain t (one trade per day).
2. VAL net mean > 0 and t >= 1.65 (one-sided, same sign as DEV).
3. Net mean >= 0.3 bp per trade in both, and positive in at least 3 of the 4 calendar years 2022-2025.
4. Calibration: 200 permutations pairing each trade's side with the driver sign of a different random day (same pair/hour grid); the max |t| over the 14 cells in DEV must be
   below 2.9 in >= 95% of permutations, else the bar is raised to that 95th percentile before the real run is read.
Kill rule: no variants beyond these 14. A pass is then audited (by year, by season/DST, by weekday, latency +1 min) before any claim. Honest prior: P(a cell survives) ~5%.
