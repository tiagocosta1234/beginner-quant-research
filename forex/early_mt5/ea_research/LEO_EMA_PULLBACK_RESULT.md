# E1: the LeoTrades morning US500 pullback setup, mechanical version, on SP / NSDQ / DOW (MT5 broker M1 bars): result (2026-10-09 16:28 local, 2026-10-09)

Pre-registration `PREREG_LEO_EMA_PULLBACK.md`, simulator `leo_ema_pullback.py`, output `LEO_EMA_PULLBACK_OUTPUT.txt`, ledger family leo_ema_pullback (ledger 52). The 2026 hold-out was NOT opened.
## Verdict: FAILS acceptance 1 and 2; idea closed (the mechanical version)
| period | trades | mean R | net bp | PF | daily t | win | per index (R) |
|---|---|---|---|---|---|---|---|
| DEV 2022-24 | 4,607 | -0.087 | -0.87 | 0.84 | -4.80 | 44.9% | DOW -0.064, NSDQ -0.078, SP -0.120 |
| VAL 2025 | 1,530 | -0.124 | -1.24 | 0.78 | -3.87 | 43.8% | DOW -0.052, NSDQ -0.100, SP -0.220 |
| 2022-25 pooled | 6,137 | -0.097 | -0.97 | 0.83 | -6.09 | 44.6% | all three negative |
## Reading
- Every index loses in both periods by about 0.1 R (1 bp) a trade, which is the cost of one round trip (spread 0.7-0.8 bp + 0.24 bp slippage): the gross edge is about ZERO. A 0.10% stop with a 1:1 / 1:2 exit just converts a random walk plus costs into a 44% win rate and a profit factor of 0.8; nothing about touching the EMA predicts the next ten basis points.
- What the video cannot tell: his discretion (candle reading, only 'strong / weak' setups, 5 entries on 3 days, all with hindsight and on a demo account) is not tested here; this only says the mechanical version of his setup has no edge on MT5 broker prices.
