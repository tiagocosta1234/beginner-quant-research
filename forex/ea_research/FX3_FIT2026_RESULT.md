# FX3-FIT2026 (2026-10-14, the trader: "be extremely profitable on 2026 on those 3 pairs")
Search of 378 simple hourly rules (pair x server hour x lookback x continuation/reversal, MT5 broker bid/ask, K3 execution) developed ON 2026, then checked on 2022-25. `fx3_fit2026.py`, `FX3_FIT2026_OUTPUT.txt`. Descriptive, not a pre-registered claim.
- Even selecting on 2026 itself the best rule reaches only t 1.55 (+1.28 bp per trade, GBPUSD hour 15 reversal); pure noise gives a best-of-378 t of 1.91 (median) / 2.66 (95th). Nothing here is extremely profitable, not even in-sample.
- The top 10 by 2026 average +0.86 bp in 2026 and -0.54 bp in 2022-25 (all 378 rules: -0.49 bp); only 8% of the top 50 are positive in 2022-25.
- A flexible enough model can be made to look extremely profitable on 2026 alone; it would be a fit to 195 days of noise and would not carry forward.
