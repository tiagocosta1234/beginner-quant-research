# ICT result: liquidity sweeps, fair value gaps and killzones on 46 MT5 broker symbols (2026-10-12)

Pre-registration: PREREG_ICT_SCAN.md. 4 variants (SWEEP_ASIA, SWEEP_PD, FVG_KZ, SB) x 46 symbols = 184 tests (154 with at least 80 DEV trades), result in R multiples, spread floor from the real-tick period, MT5 broker bid/ask.

## Verdict: 0 survivors (Benjamini-Hochberg q = 0.10 on DEV passes 0 of 154).
- 7 tests with one-sided p < 0.05 in DEV against about 8 expected by luck: no excess.
- SWEEP_ASIA, SWEEP_PD and SB are negative nearly everywhere (pooled -0.04 to -0.37 R per trade by class in DEV, VAL and HOLD alike): sweeping a high and closing back inside, or buying the silver-bullet gap, loses after costs on every asset class.
- FVG_KZ (the fair-value-gap retracement in the London / NY AM killzones) is the only variant with positive pooled results, and only on equity indices (+0.021 / +0.043 / +0.047 R in DEV / VAL / HOLD); FX is flat (+0.007 / -0.019 / -0.018 R).
- Nearest to a setup: **DAX FVG_KZ**, 1,345 DEV trades (about 448 a year), +0.116 R (t 3.16), VAL 448 trades +0.248 R, HOLD 342 trades +0.108 R: positive in all three windows, but its DEV p-value 0.00080 misses the Benjamini-Hochberg line (0.00065) and the best t of 154 pure-noise tests would already be about 2.72. EURJPY FVG_KZ (+0.102 R, t 2.8, VAL +0.107, HOLD -0.095) is second. The 2026 hold-out was seen through this scan for all tests, so DAX has no clean unseen window left on MT5 broker data: a lead to follow forward on demo with Telegram messages labelled unvalidated, not a setup to trade.

## Follow-up: DAX FVG_KZ in dollars (2026-10-12, the trader: "se arriscasse 1000$ por trade, o ano fazia cerca de 150$?")
0.116 R is per TRADE (116 USD per trade at 1,000 USD risk), about 448 trades a year, so the result is tens of thousands, not 150 USD. Per year (USD):
| Risk per trade | 2022 | 2023 | 2024 | 2025 | 2026 (9 months) | per month | worst day | max drawdown |
|---|---|---|---|---|---|---|---|---|
| 500, no slippage | +44,656 | +10,107 | +23,523 | +55,478 | +21,494 | 2,644 | -1,139 | 11,032 |
| 1,000, no slippage | +89,312 | +20,215 | +47,046 | +110,956 | +42,989 | 5,288 | -2,279 | 22,064 |
| 500, 1 point of slippage | +38,025 | +699 | +15,612 | +50,279 | +17,824 | 2,062 | -1,218 | 16,930 |
| 1,000, 1 point of slippage | +76,049 | +1,398 | +31,224 | +100,557 | +35,648 | 4,125 | -2,436 | 33,860 |
Slippage sensitivity of the mean (DEV / VAL / HOLD): 0 pt +0.116 / +0.248 / +0.108 R; 1 pt +0.081 / +0.224 / +0.087; 2 pt +0.045 / +0.201 / +0.065; 3 pt +0.010 / +0.178 / +0.044.
Trade geometry: 3,802 trades 2022-26, stop distance median 26.8 points (0.146% of price), spread 1.36 points (the stop is 21 spreads), at most 2 trades a day; 500 USD risk = about 3x the account in notional, 1,000 = 7x.
The 2022-24 range that selected DAX is not clean evidence; the 2025 window (+0.248 R, 448 trades, t about 3.5 on its own) was not used to pick it, but 2026 was already seen. It needs a real-tick tester run.
