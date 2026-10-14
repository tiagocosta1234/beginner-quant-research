# Pre-registration TREND-PORT: multi-asset time-series trend portfolio on the MT5 broker universe (written 2026-10-14 before any run)
the trader chose option 1 ("multi-asset trend and carry portfolio, judged on portfolio Sharpe"). Carry is not testable (no historical swap/rate feed that MT5 broker's MT5 supplies; the account is swap-free), so this is the TREND half. the trader's data rule stands: 2020 onward only (he declined pre-2020 data on 2026-10-14).

## Universe, data, clock
MT5 broker-listed markets with daily history from MT5 broker D1 (`forex/data/<name>_D1.parquet`, close, server day): 15 FX pairs (AMENDMENT A1 before any P&L: the 13 other MT5 broker crosses have no daily file from 2020 and are algebraic combinations of these 15: AUDCAD AUDCHF AUDJPY AUDNZD AUDUSD CHFJPY EURGBP EURJPY EURUSD GBPJPY GBPUSD NZDUSD USDCAD USDCHF USDJPY); indices SP (US500.cash), NSDQ (US100.cash), DOW (US30.cash), DAX (GER40.cash), NIKKEI (JP225.cash), ASX (AUS200.cash); metals XAUUSD, XAGUSD; oil BRENT (UKOIL.cash), WTI (USOIL.cash); crypto BTCUSD, ETHUSD, LTCUSD, XRPUSD, BNBUSD, ADAUSD, DOGEUSD. A market joins the portfolio on the first day it has the full lookback; SOLUSD (history starts 2025) is excluded.
Only prices from 2020-01-01 are used (warm-up included). The measured window starts 2021-01-04 so that the 250-day lookback is filled with 2020 data. Weekdays only (Mon-Fri close-to-close, holidays forward-filled with zero return; crypto weekend moves roll into Monday).
## Strategy
Signals at each Friday close (information through that day): s = sign of the L-day return, L in {20, 60, 120, 250}; COMBO = mean of the four signs. Weight per market w = s x 0.10 / (sigma x N), sigma = EWMA(span 60) annualised vol of daily returns, N = number of active markets. Held from the next trading day until the next Friday. P&L = sum of w x daily return minus cost = |change in w| x half-spread (bp, median MT5 broker M1 spread of the last 12 months in hours 2-21, halved) at each rebalance. Swap-free, so no financing term.
Cells (15): signal in {L20, L60, L120, L250, COMBO} x universe in {ALL (32 markets), FX (15 pairs), NONFX (17 markets)}.
Yardstick (reported, not a cell): the same sizing with s = +1 on every market (long-only drift portfolio) per universe; a trend cell must beat its yardstick's Sharpe.
## Periods and gates
DEV 2021-01-04..2023-12-31, VAL 2024-01-01..2025-12-31, HOLD 2026-01-01.. (the script loads nothing after 2025-12-31 unless `--hold`).
Power statement (written before the run): five years cannot confirm a Sharpe below about 1.2 at p <= 0.05/15; a true Sharpe of 0.5-0.8 would be missed. Therefore:
- CLAIM (portfolio edge): combined 2021-25 Sharpe >= 1.2 and block-bootstrap one-sided p <= 0.0033 (stationary bootstrap, mean block 21 days, 2,000 draws), net of costs; DEV Sharpe >= 0.8 and VAL Sharpe >= 0.5; Sharpe above the long-only yardstick of the same universe; above the 95th percentile of a placebo (the same signals cut into 60-day blocks and re-ordered at random in time, 300 draws).
- SUGGESTIVE (reported, no claim): positive in both DEV and VAL, combined Sharpe >= 0.5 and above the yardstick: recorded as a lead that would need the pre-2020 out-of-time check the trader has declined, or a forward log.
- Everything else: no edge.
Cost sensitivity: all cells are also run at 2x costs (reported).
Kill rule: 15 cells, no more; no parameter tuning after the run.
