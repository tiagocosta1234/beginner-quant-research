# Pre-registration: Family CX, weekly cross-sectional momentum / reversal in MT5 broker's 8 crypto CFDs (written 2026-10-11, before any code or result)

Source: Liu, Tsyvinski, Wu (2022) "Common Risk Factors in Cryptocurrency" (JF): a weekly cross-sectional momentum factor (1-4 week past
returns) earns a premium; short horizons can reverse. Not tested here (crypto_trend / btc_*_ta were time-series rules on BTC/ETH).
Market-neutral (long 2 / short 2), so expected to be unrelated to gold and to the crypto market's direction. MT5 broker crypto CFDs trade every day.
Costs are large (median spread 2025: BTC 6.5, ETH 14, BNB 13, XRP 8, ADA 28, BCH 31, SOL 30, LTC 45 bp; 2022 much higher): the test pays them.

## Data and rule
MT5 broker M1 bid/ask for BTCUSD, ETHUSD, LTCUSD, XRPUSD, ADAUSD, BCHUSD, BNBUSD, SOLUSD (2021-12 onward; ADA/BCH/BNB/SOL exported 2026-10-11
from the portable data terminal). Rebalance every Monday at 12:00 server time (outside the rollover). Price for signals: mid at 12:00.
- CX1 momentum 1 week: rank by return over the previous 7 days; long the top 2, short the bottom 2, hold 7 days.
- CX2 reversal 1 week: the mirror of CX1 (long bottom 2, short top 2).
- CX3 momentum 4 weeks: rank by return over the previous 28 days; long top 2, short bottom 2, hold 7 days.
Equal notional per leg. Every week every leg is closed and reopened (full round-trip cost at the bid/ask of the two 12:00 minutes,
+0.1 bp slippage each side; this overstates costs when a coin stays in the same leg: conservative). A coin without a quote at either
minute is skipped that week. Weekly result = mean of the 4 legs, in bp.

## Periods and acceptance
DEV 2022-01-03..2024-12-31 (about 156 weeks), VAL 2025, HOLD 2026-01-01..2026-09-30 (once, only for passing variants).
Accept for the hold-out: DEV weekly t >= 2.4, DEV mean > 0, VAL mean > 0. Then the account tests (correlation <= 0.3, pass70 uplift >= 3 points).
