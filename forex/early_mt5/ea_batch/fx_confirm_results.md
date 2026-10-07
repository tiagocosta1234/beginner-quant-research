# Out-of-time check of the top FX EAs (2026-10-06 night), default inputs, real ticks, $100K, 2022-2025
Pre-registered pass: net > 0 and tester equity drawdown <= 10% in at least 3 of the 4 years.
| EA (id) | 2022 | 2023 | 2024 | 2025 | Verdict |
|---|---|---|---|---|---|
| BADX, EURUSD M30 (23029) | +3,370 (7.9%) | +1,962 (6.2%) | -1,169 (6.7%) | -2,019 (8.0%) | FAIL: 2 of 4 years positive, profit factor 1.05 |
| Babi Ngepet, EURUSD H1 (64444) | +2,482 (7.0%) | +1,844 (2.8%) | +1,612 (1.1%) | +2,069 (**30.2%**) | passes the written rule (3 of 4), but it is a LOT-ESCALATING (martingale / grid) EA: volumes 0.03-7.68 lots, average win 7.3 vs average loss -37.5, worst trade -530; the 30% drawdown in 2025 would breach any MT5 broker limit. Not deployable. |
| Invest System 4.5, EURUSD M30 (19968) | -1,576 (6.1%) | +2,148 (1.4%) | -2,118 (5.8%) | +2,262 (1.8%) | FAIL: 2 of 4 years positive |
Lesson: a high win rate with low drawdown in three years and a 30% drawdown in the fourth is the signature of a martingale tail; the written rule should also cap the worst year (add: no year above 10% drawdown). Data: `results_<year>/<id>.csv`.
