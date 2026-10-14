# PREREG DAY2K-H - will the rest of the day be bullish or bearish? (written 2026-10-14, the trader: "i just know its possible... lets focus on trying to guess if a day will be bullish or bearish")

The cleanest form of the question, stripped of stops and targets: at a decision time T, is the mid price at the 21:55 server bar open above or below the mid price at the T+60 s bar open? Sign prediction carries more information per day than a 1:1 stop/target outcome (which adds noise on top of the direction), so if direction is predictable at all, it shows here first.

## Targets and universe (fixed)
Decision times T in {10:05, 16:35} server. y = 1 if mid(21:55 bar open) > mid(T+60 bar open) else 0 (same day, mid prices, spread ignored for the accuracy statistic; a signed-return-in-ATR statistic is reported next to it). (a) GOLD model: XAUUSD+ only, one row per day. (b) POOLED model: every market with median spread/ATR20 <= 2% (about 34 of the 46 MT5 broker), one row per market-day, one model per T.

## Features (causal at T; same code as rounds B-E)
Own price structure (m1, m5, m20, am = move since 01:05, pdh, pdl, apos, rr, arng, spr, tvr, dow, and the asset-class code for the pooled model); cross-market morning moves since 01:05 normalised by ATR (SP, NSDQ, DOW, DAX, NIKKEI, BTCUSD, WTI, XAGUSD, EURUSD, GBPUSD, USDJPY, AUDUSD, USDCHF) and the USD strength index of the 7 USD pairs; for gold also the lagged rates and gold-vol macro block, calendar surprise already published and upcoming importance-3 USD events, flow calendar.

## Models, yardsticks and trials (8)
Models: L2 logistic regression (standardised, C = 0.1) and HistGradientBoostingClassifier (depth 2, 100 iterations, lr 0.05, min leaf 60); walk-forward, quarterly refit, expanding window, scored from 2022-12-01 (DEV' 2022-12..2024-12, VAL 2025; HOLD 2026 sealed). Trials: {gold, pooled} x T x {logistic, boosting} = 8. Yardsticks reported (not trials): always-up, yesterday's direction, 20-day trend direction, morning-move continuation, morning-move fade.
Bonferroni for 8, one-sided 5%: DEV' hit rate beats 50% with block-t (5-day blocks, per-day mean of correct - 0.5) >= 2.50 AND beats the best yardstick's DEV' hit rate; VAL: hit rate > 50% with block-t >= 1.65 and beats always-up. Also reported: AUC, and the mean signed return of following the prediction in ATR units.

## Gates
Positive control: the label leaked as a feature must give hit rate > 95%. Placebo worlds: labels permuted across days (seeds 161-163) must give 0 survivors. Truncation: random rows' features recomputed from bars before T equal the matrix (rounds B/C code, tested).

## Honest prior
Published daily-direction accuracy for liquid markets is about 50-53% out of sample; the literature's reliable pockets are momentum at multi-week horizons and intraday momentum on index ETFs (the last half hour follows the first). P(survivor) before looking: under 10%. A hit rate of 55% would be +0.1 R and a 70% win rate is out of the question; the result will say how far from 50% direction can be pushed.

## Dry-run record (2026-10-14, before any model result)
Pooled model: 34 markets, 35,061 / 35,038 rows with a target (T10:05 / T16:35); gold 1,005 rows each. Up-rate of the rest of the day: gold 49.2% / 48.7%, pooled 49.9% / 49.8% (no built-in bias). Truncation test of the cross-market morning moves: 30/30 identical. No trial, threshold or period changed.
