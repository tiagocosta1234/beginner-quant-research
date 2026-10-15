# BRK-META result (breakout day round 5, 2026-10-15 11:50): a model trained on past breakouts adds ~0.1 R by picking index breakouts, not enough
Pre-registration `PREREG_BRK_META.md` (amendment A1 before any P&L: causal breadth), engine `brk_meta.py`, events `D:\finance\si_ledgers\BRK_META_events.parquet` (53,898 session breakouts, 21 features). Truncation PASS on the features.

| (R per trade, hold to close) | DEV 2023-24 | VAL 2025 | 2026 | placebo DEV (3 worlds) |
|---|---|---|---|---|
| all breakouts (no model) | -0.062 | -0.076 | -0.037 | |
| M1 xgboost, top fifth | +0.018 (t -0.51, 3,540 trades) | -0.019 (t -0.68) | -0.030 | -0.061 / -0.075 / -0.095 |
| M2 linear, top fifth | +0.038 (t +1.17, 3,251) | +0.004 (t -0.34) | +0.030 | -0.075 / -0.087 / -0.062 |
0 of 2 pass (gates 1-2 fail; both beat the shuffled-label placebos and the base by about 0.07-0.10 R).

What it learned: the selections are mostly INDEX breakouts (M2: 1,980 of 3,251 DEV picks; M1: 1,063 + 1,961 FX), and the top features are box size relative to ATR, the market class, weekday, hour, box volume and trend alignment. Combining every weak feature lifts the breakout from -0.06 to about 0 to +0.04 R: the model rediscovers "trade index breakouts, with the trend, with a normal-size box", and still does not clear the cost by a margin that survives 2025.
