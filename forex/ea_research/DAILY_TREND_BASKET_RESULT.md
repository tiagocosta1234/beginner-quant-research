# T1: vol-scaled daily trend basket (28 FX + gold + NSDQ/SP/DOW) on MT5 broker prices: result (2026-10-09 16:06 local, 2026-10-09)

Pre-registration `PREREG_DAILY_TREND_BASKET.md`, simulator `daily_trend_basket.py`, output `DAILY_TREND_BASKET_OUTPUT.txt`, ledger family daily_trend_basket (ledger 50 of 51). The 2026 hold-out was NOT opened.
## Verdict: FAILS acceptance 1 and 2; idea closed
| period | days | net Sharpe | daily t | mean bp/day | gross Sharpe (before costs) | ex-gold net Sharpe |
|---|---|---|---|---|---|---|
| DEV 2022-06..2024-12 | 668 | -0.63 | -1.02 | -8.0 | -0.53 | -0.69 |
| VAL 2025 | 259 | +0.32 | +0.32 | +4.6 | +0.41 | +0.09 |
| 2022-06..2025 pooled | 927 | -0.34 | -0.65 | -4.5 | -0.25 | -0.45 |
Registered bars: DEV Sharpe >= 0.8 and t >= 2.0 (got -0.63 / -1.02), VAL Sharpe >= 0.3 (got +0.32, the only number that clears a bar, with DEV failing).
## Reading
The time-series momentum basket lost money in 2022-06..2024 even BEFORE costs (gross Sharpe -0.53): whipsaw regimes in FX and indices (2022 H2 reversals, 2023-24 range markets). 2025 was positive (tariff shock year) but gross Sharpe only +0.41. Turnover about 2 units of notional per day is not the problem; there is no stable premium in this window. Diagnostics: no price glitches (large moves are real events: Apr 2025 tariffs, Jan 2026 gold); equal-risk weights over 7 JPY crosses create correlated clusters (-4.9% in one day in Jan 2023), a weighting weakness of the registered rule, not used to rescue it.
