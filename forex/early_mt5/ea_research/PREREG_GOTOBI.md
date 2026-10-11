# Pre-registration: Family GT, USDJPY before / after the Tokyo 09:55 fix ("Gotobi"), written 2026-10-11 before any code or result

Source: Ito & Yamada (2017), "Puzzles in the Tokyo fixing in the forex market: order imbalances and biased pricing", JIMF; Bessho et al.
(gotobi days). Mechanism: Japanese importers buy USD at the 09:55 JST fixing, heaviest on gotobi days (days 5/10/15/20/25 and month-end).
Reported: USDJPY tends to rise into the fix and fall after it. Not tested in this repo (ledger has no gotobi / tokyo-fix family).
Fit for the account: FX, unrelated to gold, intraday (under 2 hours), MT5 broker USDJPY+ spread about 0.38 bp outside the server 00:00 rollover.

## Data and clock
MT5 broker M1 bid/ask `forex/early_mt5/data_mt5/USDJPY_M1_rates.parquet`, server clock Europe/Athens converted to Asia/Tokyo with the `.dt` accessor
(lesson of the NA bug). Tokyo weekdays only; Japanese public holidays are NOT removed (no calendar; they only dilute).
Gotobi date: calendar day 5, 10, 15, 20, 25, or the month's last calendar day (stands for "30"; also covers February); a gotobi day on
Saturday/Sunday moves to the previous Friday.

## Variants (3, fixed now)
- GT1: every Tokyo weekday, BUY at the ask at the open of the 08:00 JST minute, SELL at the bid at the open of the 09:54 JST minute.
- GT2: GT1 on gotobi dates only.
- GT3: gotobi dates only, SELL at the bid at the open of the 09:56 JST minute, BUY back at the ask at the open of the 11:00 JST minute.
A trade needs both minutes present. Cost: the bars' bid/ask plus 0.1 bp slippage each side. Result in bp of notional per trade day.

## Periods and acceptance
DEV 2022-01-01..2024-12-31, VAL 2025, HOLD 2026-01-01..2026-09-30 (opened once, only for variants that pass).
Accept for the hold-out: DEV t >= 2.4, DEV mean > 0, VAL mean > 0, at least 100 DEV trades.
Then for the account: correlation with the pair <= 0.3 and an uplift in the clean simulation with at most 1 point more breach.
