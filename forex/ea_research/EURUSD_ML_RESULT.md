# EURUSD-ML result (2026-10-14): walk-forward ridge and gradient boosting over 35 features
Pre-registration `PREREG_EURUSD_ML.md`, engine `eurusd_ml.py`, output `EURUSD_ML_OUTPUT.txt`. 8,948 slots (9 per weekday, 2022-03..2025-12), 4 h hold, real bid/ask, test windows half-years 2023-01..2025-12 trained on everything that ended before them. HOLD 2026 unopened.
## Verdict: 0 survivors, no model has any out-of-sample skill
| cell | DEV 2023-24 net bp (t) | VAL 2025 net bp (t) | out-of-sample rank IC |
|---|---|---|---|
| ridge c=1 | -1.15 (-2.62), n 1,923 | -0.99 (-1.31) | -0.034 |
| ridge c=2 | -1.67 (-2.98) | -1.45 (-1.16) | -0.034 |
| gbm c=1 | -0.61 (-1.47), n 2,066 | +0.03 (0.05) | +0.017 |
| gbm c=2 | -0.23 (-0.47) | +0.50 (0.51) | +0.017 |
- Placebo worlds 61-65 (training labels permuted within months): best DEV t -1.2 .. +1.0; the real best (-0.47) is inside that range. Long-only drift yardstick -0.50 bp per 4 h slot (EURUSD fell on average in the sample).
- Ridge has a NEGATIVE out-of-sample IC (-0.034): what it learns in one half-year reverses in the next; boosting's IC (+0.017) is too small to cover the ~0.9 bp round-trip cost, and its by-hour trade table is scattered (-1.6..+1.2 bp) with no pattern.
- Putting every feature family together does not create what no single family had: no EURUSD skill at the 4-hour horizon in 2023-25.
Nothing to multi_fx_ea. EURUSD stays without a profitable rule.
