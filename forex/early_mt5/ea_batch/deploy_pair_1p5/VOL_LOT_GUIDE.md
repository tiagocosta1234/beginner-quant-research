# Lot guide by gold's volatility (2026-10-07, from iteration 8 of the intraday lab)
Gold's average daily range (20-day) was USD 25 in 2022, 58 in 2025 and 123 in 2026 (average); on 2026-10-02 it is **USD 89**. The pair's dollar profit per lot followed that range, so the loaded lots (Stochastic 0.31 / XAU5min 0.10 at the 1.5x step, frozen at 2026 volatility) carry about the 2026 dollar risk only while the range stays near USD 123.
Rule (risk cap, never scale up): lots factor = min(1, 123 / ATR20). Re-check the 20-day range at the start of each week (average of the last 20 daily high-low ranges of XAUUSD) and set the lots of the NEXT trades to the table; open positions are left alone.

| ATR20 (USD) | factor | Stochastic / XAU5min at the 1.5x step | at the 1.0x step | 0.6x step |
|---|---|---|---|---|
| up to 123 | 1.00 | 0.31 / 0.10 | 0.21 / 0.07 | 0.12 / 0.04 |
| 160 | 0.77 | 0.24 / 0.08 | 0.16 / 0.05 | 0.09 / 0.03 |
| 200 | 0.61 | 0.19 / 0.06 | 0.13 / 0.04 | 0.07 / 0.02 |
| 250 | 0.49 | 0.15 / 0.05 | 0.10 / 0.03 | 0.06 / 0.02 |

Today (ATR20 = 89, 0.72 x the 2026 average) the factor is 1.0: keep the loaded lots. It also means each lot earns about 28% fewer dollars than the 2026 average if the EAs' edge per unit of range is unchanged. The 2-Step replay at constant risk (iteration 8: pass 52% / breach 43% with the ladder) is the cautious expectation; the fixed-lot replay (72% / 28%) assumes 2024-26 volatility continues.
