# Pre-registration BRK-META (breakout day, round 5; written 2026-10-15 11:49 local (commit time), before any code or result)
Question: can a model trained only on PAST breakouts pick which new breakouts to take (meta-labeling)? Events = round 1's 54,006 session stop-order breakouts on 46 markets; label = the hold-to-close result X4 (net R).

## Features (all known at the fill)
class (one-hot), side, local hour of the fill, minutes from the box end to the fill, box / ATR14, relative breakout-minute tick volume, relative box tick volume, ATR rank (250 d), NR4, trend alignment (side x sign(prev close - SMA20)), distance to the previous 20-day high and low in ATR, previous-day return x side / ATR, overnight move (box start mid - previous close) x side / ATR, weekday, the market's mean X4 over its previous 20 events, breadth = share of markets that already broke the same way earlier the same server day.

## Walk-forward (expanding, yearly)
Train on every event before year Y, predict year Y: train 2022 -> predict 2023; 2022-23 -> 2024; 2022-24 -> 2025; 2022-25 -> 2026 (non-clean look). DEV = the 2023-24 predictions, VAL = 2025.
Rule: take an event if its prediction is above the 80th percentile of the model's predictions on its own training set (top fifth, causal). Exit X4.
Cells (2): M1 gradient-boosted trees (xgboost, regression on X4, depth 3, 300 trees, learning rate 0.05, subsample 0.8); M2 ridge-like linear regression on standardized features (baseline).

## Gates
1. DEV mean >= +0.05 R and t >= 2.24 (daily portfolio, NW lag 1; Bonferroni 2). 2. VAL mean > 0 and t >= 1.65. 3. Placebo: the same pipeline with the training labels shuffled within each training year (3 worlds); the real DEV mean must exceed every placebo's DEV mean. 4. Beats the unfiltered base in DEV and VAL by >= 0.05 R.
## Honest prior
About 5%: every single feature tested in rounds 1-4 is weak; trees can combine them but also overfit; earlier ML on bars here found nothing.
Amendment A1 (before any P&L): breadth is divided by the 46 markets, not by the day's total number of breakouts (the draft denominator used events after the fill).
