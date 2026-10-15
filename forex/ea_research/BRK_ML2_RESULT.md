# BRK-ML2 result (breakout day round 33, 2026-10-15 14:11, local clock): a model can find the LOSING breakouts, not winning ones
Pre-registration PREREG_BRK_ML2.md (amendments A1, A2 before any P&L), engine brk_ml2.py (truncation PASS after A2), rows D:/finance/si_ledgers/BRK_ML2.parquet. Walk-forward XGBoost on 986,184 hour-map breakouts (15 features known at entry), trading the events predicted in the top decile of each model's training predictions.
| S1 top-decile selection (net R) | DEV (2023-24) | VAL (2025) | 2026 | the unselected events DEV / VAL / 2026 |
|---|---|---|---|---|
| (n 23,759 / 12,150 / 10,127) | -0.017 (t -0.8) | +0.015 (t 0.1) | +0.038 | -0.111 / -0.116 / -0.099 |
0 of 1 passes (gate 3 yes, gates 1-2 no).
Mean R by prediction decile, test years 2023 / 2024 / 2025 / 2026: lowest decile -0.35 / -0.32 / -0.31 / -0.32, then rising steadily, highest decile -0.02 / -0.04 / +0.01 / +0.02. The model ranks breakouts consistently out of sample, and its main input is the box width in spreads (feature importance 0.28-0.44): it learns WHERE THE COST IS, which separates bad from average, but even its best decile only breaks even. Selected trades by class (DEV / VAL / 2026): metals +0.085 / +0.109 / +0.020, indices -0.017 / +0.061 / +0.047, FX -0.027 / -0.020 / +0.041.
Reading: with everything known at the entry, machine learning confirms the day's conclusion: breakouts on MT5 broker can be made less bad (avoid narrow boxes, crypto, busy hours), not profitable.
