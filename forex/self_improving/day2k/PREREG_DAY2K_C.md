# PREREG DAY2K-C - the daily 1:1 / 2,000 USD trade over every MT5 broker market, not only FX (written 2026-10-14, the trader: "every day you have to pick a 1:1 setup risking 2000$")

Rounds A and B (`DAY2K_RESULT.md`, `DAY2K_B_RESULT.md`) found nothing among 28 FX pairs. the trader's rule is that a setup must be picked every day, so the candidate pool is widened to all 46 MT5 broker with M1 bid/ask bars: 28 FX, XAUUSD, XAGUSD, BRENT, WTI, SP, NSDQ, DOW, DAX, NIKKEI, ASX, BTCUSD, ETHUSD, LTCUSD, XRPUSD, SOLUSD, BNBUSD, BCHUSD, ADAUSD. Candidates per day: market x side (up to 92). Same trade object and outcome engine as round A: stop = target = k x ATR20, entry at the open of the bar T+60 s on the executable side, forced exit at the 21:55 bar open, tie in one bar = loss, no decision in server hours 23-0. A market-day needs bars at the exact entry and exit minutes and >= 600 bars on each of the 20 previous days (markets that are closed then drop out of that day's pool).

## Honest prior and the drift problem
Prior that a survivor exists: under 5%. The widened pool contains assets with a long-run drift in 2021-26 (gold +, crypto, indices): a fixed "always long" rule can show a positive mean R that is the market's trend, not a setup. Every table therefore carries the yardstick "long-only average over all markets" and "short-only average" of the same (T,k) next to each cell, and a survivor must beat the baseline (mean of all candidates) AND be positive in both halves of VAL. The 2025 gold/crypto run is regime, not evidence.

## Trials (28) and acceptance
- 24 rule cells exactly as round A (signals M5, M1, AM; continue/fade; T {10:05, 16:35}; k {0.4, 0.7}); the pair with the largest |score| over the whole universe is taken.
- 4 ML cells: walk-forward HistGradientBoosting ranker (round B settings: depth 3, 100 iterations, lr 0.06, min leaf 300, quarterly refit, expanding window, scored from 2022-12-01) over the PRICE features plus tick-volume ratio and an asset-class code (fx / metal / energy / index / crypto), T x k.
- Bonferroni for 28 trials, one-sided 5%: DEV' block-t >= 2.91 (blocks of 5 days) and mean R above the baseline of the same (T,k); VAL: mean R > 0, block-t >= 1.65, >= 200 days. Survivors are audited (by asset class, by market, by side, by year, ex-best-20-days, spread x2), then HOLD (2026-01-01..2026-09-30) is opened once.

## Gates before any cell is read
Truncation test (scores recomputed from bars before T for 40 random market-days incl. non-FX); positive control (oracle side, ML with the label leaked in: dev R > +0.3); placebo worlds (rule cells with noise scores, seeds 101-103; ML cells with labels permuted across days, seeds 111-113): at most 0 survivors in each world, else nothing is read.

## Reported next to the result regardless
Coverage per asset class; resolved share per (T,k); long-only and short-only mean R per asset class (DEV' and VAL); and what a daily pick would have cost in MT5 broker terms (rolling-start pass/breach of the best cell and of a random pick).

## Dry-run record (2026-10-14, before any cell P&L)
46 markets x 1,066 days built. Valid market-days 88-98% by class. Resolved share at k0.4 / k0.7: FX 72% / 30% (T10:05), metals 80% / 38%, energy 87% / 40%, indices 77% / 35%, crypto 68% / 32%. Truncation test 40/40. The only code change to round A's engine is a parameter (DEV_T, default 2.86, 2.91 here); round A/B results are unaffected.

## Amendment A1 (2026-10-14, before any cell P&L)
The first calibration run stopped with an error: the ML feature list inherited cs1/cs5 (FX currency strength) from round B, which are empty in this universe, and the booster cannot bin an empty column. They are removed from the ML feature list (it was already stated as price features + tick-volume ratio + class code). The rule cells' oracle control had already run and scored +0.35..+0.65 R. No cell, trial count, threshold or period changed.
