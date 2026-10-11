# Pre-registration: Family GF, opening-gap fade on US index CFDs (written 2026-10-11 ~14:45, before any code or result)

Idea: at the US cash open, small/medium overnight gaps tend to be partly filled during the day (liquidity provision against overnight
order imbalance); very large gaps tend to continue. Widely cited in practitioner work on SPY/ES; not tested in this repo (ledger has no
gap family; index_daily tested the overnight hold and a 30-min opening-range breakout, not a fade). Intraday only (flat by 15:55 NY):
no overnight or weekend risk, one decision a day, unrelated to gold.

## Data and clock
MT5 broker M1 bid/ask for SP+, NSDQ+, DOW+, converted to New York time with the `.dt` accessor (NA lesson). Shorts use 1 - exit/entry style
(entry - exit in price units here: P&L = side x (exit - entry) / entry). Cost: bars' bid/ask + 0.1 bp slippage each side.

## Rule
- prev = mid at the close of the 15:59 NY minute of the previous trading day; open = mid at the open of the 09:30 minute.
- gap g = open / prev - 1; sigma = std of the previous 60 daily gaps (min 40) of that index.
- Trade at the open of the 09:31 minute AGAINST the gap (g > 0: sell; g < 0: buy), at the bid (sell) / ask (buy).
- Target: prev (the gap fully filled); exit at the target when a minute's bid high / ask low reaches it (filled at the target).
- Otherwise exit at the open of the 15:55 minute. No stop (the day's end is the stop; sizing in the account would be by the gap size).
- Result per trade in bp of notional; daily result = mean over the indices traded that day.

## Variants (3, fixed now)
- GF1: trade when 0.5 sigma <= |g| <= 2.0 sigma (medium gaps).
- GF2: trade when |g| > 2.0 sigma (large gaps; the literature expects continuation, i.e. GF2 should LOSE; a positive GF2 would be a surprise).
- GF3: GF1 with exit at 11:00 NY instead of 15:55 (the fill usually happens early or not at all).

## Periods and acceptance
DEV 2022-01-01..2024-12-31, VAL 2025, HOLD 2026-01-01..2026-09-30 (one look, only for passing variants).
Accept for the hold-out: DEV daily t >= 2.4, DEV mean > 0, VAL mean > 0, >= 150 DEV trade days.
Then for the account: correlation with the pair <= 0.3 and pass70 MIX uplift >= 3 points by 22 Dec with at most +1 point breach.
