# 12 EMA backtest (the trader's FX Replay, gold): MT5 broker replay and Monte Carlo (2026-10-19 02:2x local clock, main PC)

Source: Notion database "12 ema backtest" (https://app.notion.com/p/3fd46e084a8d80b88f5ec1c879b19ad4; it shares its data source with
"breakout backtest"). 30 rows, all XAU, one FX Replay screenshot each (OANDA:XAUUSD 1m, blue EMA, long/short position tool, no spread applied;
the trader: some sessions skipped by mistake, no look-ahead). Added to Notion on 19 Oct (Claude): Entry, Stop, Target, "Alvo / stop (R)", "R sem spread",
Data; Claude check = OK on 30/30 (outcome in the image matches the trader's Win/Loss). Prices read by eye from the position labels (+-0.01).

## What the images show
- Target is 0.525 R of the stop (0.507-0.545 on all 30), so break-even win rate = 65.6%, not 50%. Targets USD 0.87-5.18 (median 2.27), stops 1.66-10.02 (median 4.34).
- Entries cluster at the London open (08:00-08:15 chart time) and the NY open (14:30-14:45). Trades last 0-29 minutes (median 4).
- Dates are NOT on the charts. They were inferred by matching entry price and outcome to MT5 broker XAUUSD M1 (`match.py`): exactly one chronologically
  consistent assignment, 14 Apr to 12 May 2025, entry prices within a few cents of MT5 broker mid. Written to the Notion Data column.

## MT5 broker bid/ask replay (`replay.py`, `mae.py`)
Long entered at the ask, short at the bid, same USD stop/target distances, exits on the real side of the book, entry minute = best price match.
Recorded 25/30 wins, mean R +0.270 (t 2.56) -> MT5 broker 24/30 wins, mean R +0.219 (t 1.93); only row 30 flips. Spread at the entry minute: mean 0.28 USD
(MT5 broker Apr-Jul 2025 open windows: London 0.27, NY 0.30). The four wins that touched the target by < 0.1 USD (rows 12, 14, 20, 23) still win on MT5 broker
prices. Winners' mean adverse excursion 0.34 R (max 0.86). By session: London 14/17, +0.25 R; NY 10/13, +0.17 R; difference not significant
(permutation p 0.92). Not significant overall (t 1.93) and a single four-week regime.

## Monte Carlo at USD 2,000 risk per trade (`mc.py`)
95,472 start, target 108,000, floor 92,000, daily loss -2,500 on equity (adverse excursion included), +2,000 a day counted; trades bootstrapped
from the 30 MT5 broker-replayed trades; win rate Beta(25, 7) (mean 78%, 90% interval 65-89%). Business days.
| trades per day | pass | breach | mean days to pass | pass by 30 Nov (31 d) | by 22 Dec (47 d) |
|---|---|---|---|---|---|
| 1 or 2 (as in the sample) | 31% | 69% | 13 | 31% | 31% |
| 2 | 23% | 77% | 9 | 23% | 23% |
| 1 | 70% | 30% | 26 | 52% | 64% |
Fixed win rate, 1-2 a day: 80% -> 32% pass; 70% -> 9%; 65.6% -> 4%; 60% -> 1%. Risk USD 1,000 (1-2 a day, uncertain win rate): 84% pass, 16%
breach, 43 days mean. One trade a day, one session, USD 2,000: London 55% / 65% / 70% pass (30 Nov / 22 Dec / ever), breach 30%; NY 40% / 49% / 55%, breach 45%.

## Caveats and next step
30 trades, 14 Apr-12 May 2025 only, independent-trade bootstrap, no slippage or news. The exact entry rule (what triggers the entry on the EMA, stop
placement) is not written down; the trader was asked for it. Next: pre-register that rule and test it mechanically on MT5 broker 2022-2026 with real bid/ask (own
40-variant count, 2026 hold-out sealed). Run the scripts from this folder (they read each other with relative paths).
