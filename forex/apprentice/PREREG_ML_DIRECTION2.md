# PREREG_ML_DIRECTION2: ML direction with a pure direction label (symmetric bracket)

Written Mon 26 Oct 2026 ~10:5x local (local clock), BEFORE any label or result of this test was computed. the trader: "test more", after PREREG_ML_DIRECTION
showed that its label (the better of two trades with different stops) let the model learn a cost artefact (picks the winner 50.5% on the days where exactly one side wins).

## What changes
- **Trade and label:** entry at the 08:15 London close (same as before), a SYMMETRIC bracket of X = k x prior daily ATR14 on both sides, stop first on a tie, flat at 16:00.
  Long and short are exact mirrors before costs, so the label is pure direction: y = 1 if +X is hit before -X; if neither is hit by 16:00, y = 1 if the 16:00 price is above the entry.
- **Three bracket sizes:** k = 0.15, 0.25 (PRIMARY), 0.50. One trade every day, side = LONG if P(long) >= 0.5.
- **Features:** the same 81 columns already built by PREREG_ML_DIRECTION (`edge_lab/ml_direction_features.parquet`, all known at 08:15), unchanged.
- **Models:** the same M1 (pooled gradient boosting, Platt-calibrated on the last training year) as PRIMARY and M3 (XGBoost) as secondary, same walk-forward (test years 2021-2026, fit only on earlier years), same Amendment-1 handling of all-missing columns.
- **Costs:** the same micro costs in points (MGC 0.32, MNQ 1.1, MES 0.74, SI 0.0112, MYM 4.4), net R = gross - cost / X.

## Bar (M1 at k = 0.25; alpha 0.01 for 3 sizes x 2 models used as one family, as before)
Mean net R > 0 AND random-side P <= 0.01 AND AUC 95% day-bootstrap interval above 0.50 AND mean net R > 0 in at least 4 of the 6 years. Reported for every size and model, plus the calibration table, the hit rate, and the "confident days only" (P >= 0.55 or <= 0.45) slice as information (no bar: the rule is one trade every day).

## Honest prior
The first model's direction hit rate was 50.5%. Expected: AUC about 0.50-0.52, no pass.
