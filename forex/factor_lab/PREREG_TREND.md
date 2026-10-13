# S1 pre-registration: diversified time-series trend following (written 2026-10-07 before any result)

Why: the best-documented real edge class (decades, many markets, many countries). Not a new idea: it is the opposite of rule-mining on 5 years. Question: does a vol-targeted 12-month trend portfolio over the markets we can trade as CFDs have a positive net Sharpe in 2001-2020, and does it hold in 2021-2026 at MT5 broker-like costs?

## Data (already in the repo or downloaded in Track A; no new source)
- Equity indices (price, daily close): `futures/data/external_index_daily/` spx, ndx, dji, ftse, dax, cac, n225, hsi (1987-2026).
- Futures (Yahoo continuous, daily close): gold GC, silver SI, copper HG, 10-year note ZN (`futures/data/daily_ohlc/`, 2000-2026). Crude oil is EXCLUDED on purpose (monthly rolls and the April 2020 negative price distort a continuous series). Residual roll gaps in the other futures are small (basis under about 1% per roll); daily returns above 15% in absolute value are set to 0 and counted.
- FX: 9 currencies vs USD from FRED (`forex/factor_lab/data/fred/`, noon rates) with the interest-rate differential accrual `(r_ccy - r_usd)/12` per month (OECD 3-month rates, Track A files).
- 21 markets in four classes: EQUITY 8, METAL 3 (gold, silver, copper), RATE 1 (ZN), FX 9.

## Construction (monthly, no look-ahead)
Signal at the last business day of month t: sign of the 12-month price return (close_t / close_{t-12} - 1) [H1], or the average of the signs of the 1-, 3- and 12-month returns [H2]. Each market is scaled to 10% annual volatility using the standard deviation of its daily returns over the last 63 trading days (leverage capped at 3). Weight_i = signal_i x min(3, 0.10 / vol_i) / N (N = markets with data that month). Held for month t+1, rebalanced monthly. Monthly return = sum of weight x (price return of the next month + FX carry accrual for FX).
COSTS (MT5 broker-like): 1.5 bp per unit of notional traded for indices and metals, 1.0 bp for ZN, FX as in Track A (1.2 / 1.5 / 4 bp); financing markup 2.0% a year on the gross notional (|weights|), both long and short (assumed from MT5 broker tester swap, not from a rate card); no other cost. Reported also with zero markup (INTERBANK-LIKE) for reference.

## Hypotheses (k = 2)
H1 TSMOM-12 (sign of the 12-month return). H2 TSMOM-MULTI (average sign of 1 / 3 / 12 months).

## Phases and HIT rule (MT5 broker-like costs)
DEV 2001-01..2012-12, VAL 2013-01..2020-12, HOLD 2021-01..2026-08 (by holding month; HOLD printed only after the DEV+VAL rule passes).
1. DEV+VAL pooled (2001-2020, 240 months): annualised net Sharpe >= 0.4 AND t-stat of the mean monthly return >= 2.3 (k = 2).
2. Positive net mean in DEV and in VAL separately.
3. Not one asset class: drop each of the 4 classes in turn, pooled Sharpe >= 0.25 for at least 3 of the 4.
4. HOLD: net Sharpe > 0 and positive in both halves (2021-01..2023-12, 2024-01..2026-08).
Reported always: annual return, vol, Sharpe, worst month, max drawdown of the monthly curve (monthly data understates the daily drawdown: stated), by phase and by year, per class contribution, and the leverage needed to reach 1% a month (descriptive).
After a hit: placebo (random signs, 200 draws), the MT5 broker simulation of a scaled version, then and only then a claim. If neither hypothesis passes, S1 is closed; nothing is tuned.
Dry run: coverage per market and month counts, no returns.
