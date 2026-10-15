# PREREG_LON_RISK - risk-per-trade sweep for the 7 kept London rules and their 127 combinations (written 2026-10-15 local clock 21:40, before running)
the trader: "tenta com riscos por trade diferentes". Same series, cycle rules and bias warning as PREREG_LON_COMBO (the 7 symbols were kept for being positive in 2025 and 2026; only 2020-21 was never used to choose anything).
Sizing schemes:
- FLAT: the same risk X on every symbol, X = 100, 200, ..., 1,500 USD (15 sizes).
- EQRISK: risk per symbol inversely proportional to the standard deviation of its daily R in 2022-24 (fixed weights, scaled so the average risk per trade equals X; same 15 X).
Each combination x scheme x X is run on MT5 broker cycles (balance-based 2,500 daily line, optimistic = day net; +2,000 a day counted; floor 92,000; target 108,000) starting every business day; reported: pass and breach within 30 and within 90 calendar days, for starts in 2026 (Jan..Aug / Jan..Jun for 90 d), 2022-25 and 2020-21.
Output: for each period, the best pass rate with breach <= 10%, and whether the configuration that is best on 2022-25 holds up in 2020-21. No acceptance bar; promising only if pass > breach and pass >= 30% within 90 days in 2020-21.
