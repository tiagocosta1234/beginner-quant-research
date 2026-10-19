# MANUALRULE result: the trader's described 12 EMA + FVG setup, mechanical version, 0 of 12 on MT5 broker gold and Nasdaq (2026-10-19)

Pre-registration `PREREG_MANUALRULE.md` (sha256 11888251..., commit 64829dea, before any P&L), engine `manualrule_test.py`, output `MANUALRULE_OUTPUT.txt`, table `MANUALRULE_TRIALS.csv`. MT5 broker M1 bid/ask 2022-2025, 2026 hold-out sealed.
Rule: first candle in the first 15 minutes after the London / NY open that opens and closes on opposite sides of the 12 EMA with body > bigger wick and body >= 0.5 ATR; target = nearest unfilled FVG on the target side
(K1 whole FVG if small, middle if big; K2 near edge; K3 far edge); stop = 2 x target distance (0.5 RR).
## Verdict
0 of 12 candidates. DEV 2022-24 mean R is negative in all 12 (-0.05 to -0.15 R a trade, 520-600 trades each, t -1.7 to -5.0); win rate 56-62% against the 66.7% needed at 0.5 RR; years 2022, 2023, 2024 all negative.
VAL 2025 is positive only in the NY sessions of gold (+0.07, t 1.5) and Nasdaq K1/K3 (+0.05, t 0.9): not significant, and negative in DEV, so nothing is opened on the 2026 hold-out.
| market session | K1 DEV R (t) | K1 VAL R (t) |
|---|---|---|
| XAUUSD London | -0.106 (-3.6) | -0.175 (-3.4) |
| XAUUSD NY | -0.050 (-1.7) | +0.070 (+1.5) |
| NSDQ London | -0.089 (-3.0) | -0.146 (-2.8) |
| NSDQ NY | -0.099 (-3.1) | +0.050 (+0.9) |
Median target distance is small (gold London 1.2 USD, NY 2.1; spread 0.19), which is why the spread alone costs about 0.1 R.
## Does it reproduce the trader's trades? No
Dry-run: the rule trades on 22 of his 30 gold session-days but in his direction on only 10 (45%, below chance); his 30 trades are positive (+0.22 R on MT5 broker prices) while the same rule over his four weeks is not. Calibration (`calib_rule.py`, `calib2.py`):
a candle that opens / closes either side of the EMA exists within 10 bars before his entry on 23 of 30 sessions, but 21.7% of all 1-minute bars qualify (about 20 of 30 by chance); body > bigger wick 20 of 30; the target equals an unfilled FVG edge on 7 of 17 (within 0.30 USD).
So what he describes is not what the data shows him doing, or it hides discretion the words do not carry (which candle, which FVG, what "clearly" means, when he skips). This test says the rule AS WRITTEN has no edge; his +0.22 R remains unexplained.
## Next
Forward logging before each entry (side, candle, FVG chosen, reason, time) and comparison with the mirror trade on MT5 broker data. Account untouched.
