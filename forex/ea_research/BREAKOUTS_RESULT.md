# BRK result (2026-10-14 ~22:55): classic breakouts on 46 MT5 broker - NO EDGE (two weak leads)
Pre-registration `PREREG_BREAKOUTS.md` (commit 8ddbeac2), engine `breakouts.py`, trades `D:\finance\si_ledgers\BRK_trades.parquet`. 2026 never loaded. The first real run was stopped after 10 minutes and rerun with the placebo's day lists computed once per market (speed only; no rule, cell or threshold changed; no statistic had been printed).

Dry-run: truncation test PASS; hand check NSDQ 2022-02-16: 09:30-10:00 NY box 14,378.2-14,512.1, first M5 close above it at 14:20 NY -> long 14:25 NY, stop at the box low (1.21%).

| cell | DEV n | DEV net R | gross | t | VAL n | VAL net | gross | t | win % | median R |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 opening-range breakout (each market's session) | 33,651 | -0.035 | +0.039 | -4.46 | 12,482 | -0.074 | +0.013 | -3.13 | 33.9 | -1.00 |
| B2 Asian-range breakout at London (FX, metals) | 20,025 | -0.032 | -0.001 | -2.65 | 6,453 | -0.033 | -0.000 | -1.97 | 41.6 | -0.27 |
| B3 Bollinger squeeze breakout (H1) | 2,990 | -0.096 | -0.015 | -1.42 | 1,055 | -0.142 | -0.027 | -2.27 | 32.3 | -1.00 |
| B4 previous-day high/low breakout | 23,981 | -0.083 | -0.024 | -8.62 | 8,300 | -0.069 | -0.001 | -1.84 | 35.7 | -1.00 |
Placebo (random minutes of the same windows, same side and stop, seeds 71-73): DEV net -0.03 to -0.15 R. 0 of 4 cells pass (negative in 2023, 2024 and 2025 in every cell).

## Leads (post hoc slices, not passes; 46 markets x 4 cells were looked at)
- **Equity indices, opening-range breakout (B1):** SP/NSDQ/DOW/DAX/NIKKEI/ASX net +0.035 R (DEV, 4,447 trades, t 1.59) and +0.022 R (VAL, 1,448, t 0.64); DAX +0.076/+0.065, NSDQ +0.086/+0.027, DOW +0.032/+0.039. The sign agrees with the published QQQ opening-range result (Zarattini et al. 2023), the size is about a tenth of it, and neither period is significant. Squeeze on indices (B3): +0.120 / +0.065 R on 463 / 151 trades, t 1.49 / -0.15.
- **USDJPY breaks out and keeps going:** positive in all four cells and both periods; pooled +0.117 R (DEV, 1,961 trades, t 1.70; 2022 +0.24, 2023 +0.00, 2024 +0.11) and +0.136 R (VAL, 639, t 1.35). The yen trend of 2022-2025 (rate divergence) is the obvious cause; the four cells overlap in time, so this is one lead, not four.
- How often a market is positive in both periods by chance: 5-6 of 46 per cell here, at or below what random signs with a cost drag give. Neither lead has earned the 2026 hold-out under the protocol (only a passing cell may open it).

Reading: breakouts on MT5 broker prices 2022-2025 are zero before costs (gross -0.024 to +0.039 R) and negative after, in every form tested here; the trend premium that breakouts harvest is too small at intraday horizons to pay the spread, except possibly in equity-index opening ranges and in USDJPY, where the evidence is weak (t below 2 in each period). Closed as a family.
