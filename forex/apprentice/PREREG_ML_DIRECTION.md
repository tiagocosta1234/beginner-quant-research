# PREREG_ML_DIRECTION: a machine-learning P(long) for the one London-open trade a day

Written Mon 26 Oct 2026 ~10:3x local (local clock), BEFORE any model was fitted or any result computed. the trader: "every london opening will have exactly one trade, no more no less, the direction should be calculated through machine learning with technical analysis and fundamentals, explore every single corner ... the result should look like: 63% long 37% short".

## The trade (fixed)
- Every trading day, every market, exactly one trade. Decision and entry at the close of the 08:00-08:15 London candle (08:15).
- Geometry = the frozen indicator's for the chosen side: stop beyond the candle's far end + 0.5 x candle range (floor 0.03 x prior ATR14), target 1R, stop first on a tie, flat at 16:00 London; micro costs (MGC 0.32, MNQ 1.1, MES 0.74, MYM 4.4 points round trip).
- Side = LONG if the model's P(long) >= 0.5, else SHORT. The printed output per day is "P(long)% long / (1 - P)% short".

## Markets and data
MGC, MNQ, MES, MSI-proxy SI (Databento GC / NQ / ES / SI 1m, 2019-06 to 2026-09-25) and MYM (MT5 broker US30 1m mid, 2022-01 to 2026-10-16). One pooled model with a market id (and per-market models as a secondary).

## Label
y = 1 if that day's LONG trade (long geometry) has higher net R than the SHORT trade (short geometry), else 0. Trade R of both sides is stored, so any side choice is scored exactly.

## Features (everything known at 08:15 London; daily series use the last value dated BEFORE the trade date)
- **Opening candle:** return, range / ATR, close location in the range, body / range, upper and lower wick / range, volume vs 20-day median.
- **Pre-open intraday:** returns 00:00-07:00 (Asia), 07:00-08:00, prior 16:00 to 08:00; Asia high / low swept by 08:15; 1m EMA12 distance and slope at 08:15; 15m EMA12 bias (the A+ rule) and its two parts; 1h EMA12 side; RSI14 on 15m and 1h; realized volatility of the last 60 minutes / ATR; distance to the prior-day high, low and close in ATR.
- **Daily technicals:** prior-day return and close location, 5 / 20-day returns, close vs SMA 20 / 50 / 200, ATR14 / price, daily RSI14, day of week, month.
- **Cross-asset:** the other markets' returns 00:00-08:15 today (GC, NQ, ES, SI); prior-day and 5-day returns of euro (6E), crude (CL), copper (HG), 10-year note (ZN), silver, S&P, Nasdaq, Dow.
- **Fundamentals:** 10-year real yield (DFII10) level and 5-day change; 10-year and 2-year yields, 2s10s spread and changes; broad dollar index (DTWEXBGS) 5 / 20-day change; VIX, VIX / VIX3M term ratio, VIX 5-day change; GVZ (gold vol), VXN, OVX, SKEW; US event day (CPI, FOMC, NFP...) from 2022; CFTC COT non-commercial net position (z-score over 52 weeks, 1-week change) for the market, lagged to its Friday release.
Missing values stay missing (tree models handle them; the logistic model fills with the training median plus a missing flag).

## Models and walk-forward (strictly out of sample)
- For each test year Y in 2021-2026: fit on all days before 1 Jan Y, predict every day of Y. Nothing from Y or later touches the fit, the scaling, the feature medians or the calibration.
- **M1 (PRIMARY): pooled gradient boosting** (sklearn HistGradientBoostingClassifier, max_depth 3, learning_rate 0.03, 300 iterations, min_samples_leaf 50, l2 1.0), probabilities Platt-calibrated on the last training year (fit on the years before it).
- M2: pooled L2 logistic regression (C 0.1) on standardized features. M3: pooled XGBoost (depth 3, eta 0.03, 300 rounds, subsample 0.8). M4: per-market gradient boosting. All secondary.
- Baselines: the indicator (candle colour), always long, coin flip.

## Measures and bar (2021-2026 out-of-sample predictions only)
- Probability skill: log loss vs the training base rate, AUC with a 95% bootstrap interval (by day), calibration table (P buckets vs realized long-win rate).
- Trading: mean net R of the model's side every day, by market and year, against the indicator's candle side on the same days; random-side P (20,000 coin flips to each trade's other side).
- **"The model works" iff M1:** mean net R > 0 AND mean net R > the candle baseline AND random-side P <= 0.01 (four models) AND AUC 95% interval above 0.50 AND mean net R > 0 in at least 4 of the 6 years 2021-2026.

## Honest prior
Every single-rule direction tested so far was a coin flip after costs; features that each carry ~nothing rarely add up to much at a 15-minute horizon. Expected: AUC about 0.50-0.52 and no pass, in which case the daily "63% / 37%" numbers would be noise and should not drive real trades. If it passes: a live feature pipeline and a forward test, not a purchase.

## Amendment 1 (26 Oct 2026 ~10:4x, after the first run crashed in the first model fit; no prediction or result existed)
The first run built the features (81 columns, 8,442 market-days, saved to `ml_direction_features.parquet`) and then crashed: features that start late (event calendar from 2022, COT from 2020) are entirely missing in early training windows, which sklearn's binning cannot take. Fix: every fit drops the columns that are entirely missing in its own training data (and predicts on the same columns). The rerun reuses the saved features. No model, feature, parameter or bar changed.
