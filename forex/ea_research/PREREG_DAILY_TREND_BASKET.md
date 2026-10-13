# Pre-registration: a vol-scaled daily trend basket over 28 FX pairs, gold and three US indices on MT5 broker prices (family T, one rule, 32 instruments)

Written 2026-10-09 just after 16:04 local (local clock), BEFORE any simulation of this rule. the trader: "(original wording omitted)" (idea 3 of 3 listed; idea 1 failed: INDEX_INTRADAY_MOM_RESULT.md). Ledger 49 of 51 before this trial (+1 here, +1 for the SDB exits); Bonferroni bar: daily t >= 2.0 with a Sharpe floor.
Idea: classic time-series momentum (a documented trend premium across FX, metals and equity indices) as a DIVERSIFIER: many slow, low-cost trades across 32 markets, so the daily 2% profit cap is rarely binding and the exposure is far from the gold pair. MT5 broker accounts are swap-free, which removes the carry/swap cost that made the earlier FX trend study swap-sensitive. It will not be fast: it is for the live account and 2027, and only if it passes.

## Rule T1 (fixed now, no tuning)
Instruments (MT5 broker M1 bid/ask bars, server clock): the 28 FX pairs, XAUUSD, NSDQ, SP, DOW (BTC/ETH/LTC/XRP are out). Observation and trading price once a day: the BID OPEN of the 22:00 server-time M1 bar (before the NY close and the rollover spread widening); no look-ahead (the signal uses prices up to that bar).
Signal at day t for instrument i: s = mean over L in {20, 60, 120} observation days of sign( P_t / P_(t-L) - 1 ), a value in {-1, -1/3, +1/3, +1}.
Weight: w = s x 0.002 / sigma, with sigma = standard deviation of the last 60 daily returns (clipped below at 0.1%), i.e. each instrument targets 0.2% of capital daily volatility (the portfolio level is irrelevant for Sharpe / t).
Return from day t to the next observation day t+1 (weekends and holidays included): R = sum_i w_i x (P_(t+1)/P_t - 1) - sum_i |w_i - w_i(previous day)| x cost_i, with cost_i = (half of the 22:00 bar's spread)/P + slippage (0.2 bp FX, 0.4 bp gold, 0.12 bp indices) per unit traded. No financing (swap-free). Missing observation (holiday): the price is carried forward up to 5 days (0% return, no trade cost).
Statistics per period: annualised Sharpe of the net daily R (mean / sd x sqrt(252)), daily t, mean bp of capital per day, maximum drawdown of the cumulative net R, average daily turnover (sum |dw|), gross Sharpe (before costs, diagnostic) and the same for the 31 instruments WITHOUT gold (diagnostic, not a trial).
Periods: first signal after 120 observation days (about 2022-05-20): DEV 2022-06-01..2024-12-31, VAL 2025, POOL 2022-06..2025, HOLD-OUT 2026-01-01..2026-09-30 (one look, only if DEV and VAL pass).

## Acceptance (Bonferroni, 51 variants)
1. DEV net: Sharpe >= 0.8 AND daily t >= 2.0 (about Sharpe 1.2 over 2.6 years).
2. VAL 2025 net: Sharpe >= 0.3.
3. HOLD-OUT 2026 net: Sharpe > 0 (one look).
4. Gate for any use: correlation of its daily P&L with the gold pair <= 0.3; in the clean simulation the leg raises P(pass) of the pair without extra breach; it is slow, so only for the live stage / 2027; a port to MQL5 as one EA with fixed risk per instrument, hard stops, AccountGuard-compatible.
If 1 fails the idea is closed (no hold-out).

## Honest prior
About 8%. The trend premium is real over decades but 2022-2025 was a mixed period for CTA-type trend (strong 2022, poor 2023, mixed 2024), 2.6 years of DEV make a t of 2.0 need a Sharpe of 1.2, and with this speed it cannot change the pass odds this year.
