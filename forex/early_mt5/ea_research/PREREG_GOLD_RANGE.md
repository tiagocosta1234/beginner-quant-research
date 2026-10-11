# Pre-registration: Family GR, gold range system for the months the pair stalls (written 2026-10-11, before any code or result)

Goal (the trader 2026-10-11: "we shouldn't depend this much on gold trend"): a gold system that earns when gold is NOT trending. The pair makes
about +0.7K a month in the two thirds of months with small gold moves and +4.1K in the big-move third (2022-26, x1.2).
Prior evidence AGAINST, stated now: GOLD_B G1 (2026-10-09) faded M15 Bollinger(20,2) breaks in quiet gold (ADX14 < 20) and lost
-0.25 R a trade, gross edge negative: in quiet gold, short-horizon band breaks tend to continue. This family tests only LONGER horizons
(H1 and daily, regime measured over weeks), which G1 did not. If all three fail, gold mean reversion is closed for this campaign.

## Data and execution
MT5 broker XAUUSD M1 bid/ask (`forex/early_mt5/data_mt5/XAUUSD_M1_rates.parquet`, server clock). Decisions only on bar closes; fills at the next minute's
open at the ask (buy) or bid (sell). Stops checked on every M1 bar (bid low for longs, ask high for shorts), filled at min/max(stop, bar open).
Shorts' P&L = entry - exit (no ratio error). Slippage 0.10 USD/oz each side. One position at a time per variant.
Size for the test: risk 500 USD at the stop per trade (results reported in R and in USD at that size).

## Variants (3, fixed now)
- GR1 DAILY: daily bar = server day, decision at the close of the 22:00 server minute. ER20 = |ln(c_t / c_t-20)| / sum |daily ln returns|
  over 20 days. Ranging if ER20 < 0.30. z = (c - SMA20) / SD20 of closes. Ranging and z <= -1.5: long; ranging and z >= +1.5: short.
  Exit at the decision minute when the close crosses SMA20, or after 5 decisions, or at a stop 2.5 x ATR20 (daily) from the fill.
- GR2 DAILY, NO REGIME FILTER: GR1 without the ER20 condition (tells whether the filter does the work).
- GR3 H1: hourly bars (server hours 01-22 only; no entries at hours 23 and 0). ER100 over 100 hourly closes < 0.25 = ranging;
  z over 50 hourly closes; enter at |z| >= 2.0 against the move; exit when z crosses 0, after 24 hourly bars, or at 3 x ATR50(H1).

## Periods and acceptance
DEV 2022-01-01..2024-12-31, VAL 2025, HOLD 2026-01-01..2026-09-30 (one look, only for passing variants).
Accept for the hold-out: DEV daily t >= 2.4 (daily USD P&L incl. zero days), DEV mean > 0, 2022-23 combined > 0, VAL mean > 0,
at least 60 DEV trades; correlation of daily P&L with the pair (clean_boot_lib.series("FT", 1.2)) <= 0.3.
After the hold-out: the pass70 account test (MIX uplift >= +3 points by 22 Dec, breach <= +1 point).
