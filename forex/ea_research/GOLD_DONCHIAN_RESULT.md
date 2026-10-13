# Gold "convex" second leg (H1 Donchian, tight ATR stop, chandelier trail): result (2026-10-09 ~10:14 local)

Pre-registration `PREREG_GOLD_DONCHIAN.md`, simulator `gold_donchian.py`, ledger `LEDGER.csv`; MT5 broker's own gold M1 bars. The 2026 hold-out, the correlation gate and the portfolio fit were NOT opened (G1 failed DEV).

## Verdict: G1 has no edge; round closed
| trial | DEV 2022-24 trades | exp R | PF | daily t | win | VAL 2025 trades | exp R | PF | daily t |
|---|---|---|---|---|---|---|---|---|---|
| G1 PRIMARY lookback 24, SL 1.5 ATR, trail 2.5 ATR | 558 | -0.01 | 0.99 | -0.05 | 30% | 202 | -0.00 | 1.00 | +0.01 |
| G2 lookback 48 | 400 | -0.05 | 0.95 | -0.37 | 27% | 139 | +0.16 | 1.34 | +1.25 |
| G3 lookback 12 | 840 | -0.01 | 0.98 | -0.19 | 29% | 285 | -0.04 | 0.97 | -0.19 |
| G4 SL 1.0 ATR, trail 2.0 ATR | 669 | -0.04 | 0.97 | -0.24 | 25% | 236 | +0.13 | 1.21 | +1.00 |
| G5 long only | 307 | +0.04 | 1.05 | +0.30 | 32% | 109 | +0.45 | 1.91 | +2.35 |
| G6 entries 03:00-19:00 server | 494 | -0.07 | 0.90 | -0.78 | 29% | 173 | +0.07 | 1.17 | +0.76 |
Registered bars for G1: DEV PF >= 1.10 and t >= 2.0 (got 0.99 and -0.05), VAL PF >= 1.05 (got 1.00).
## Reading
The convex shape is there (win rate about 30%, average win +2.0 R, average loss -0.9 R) but costs and chop leave an expectancy of zero over 2022-25, so the idea of a free-standing trend leg for gold fails on this data. The only variant that shines, long-only in 2025 (PF 1.91, t +2.35), is the 2025 gold rally (and was not eligible: DEV PF 1.05). A trend-following leg that only works in a bull year is the opposite of the diversifier asked for; nothing to build.
