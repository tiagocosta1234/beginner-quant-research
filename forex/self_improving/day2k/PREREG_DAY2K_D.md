# PREREG DAY2K-D - gold only, long OR short, one 1:1 / 2,000 USD trade a day (written 2026-10-14, the trader: "you should also be able to short gold")

Round C found that the only positive daily 1:1 number was "always long gold" (2021-24 about 0 R, 2025 +0.09..+0.12 R), i.e. the gold trend. This round asks whether the DIRECTION of the daily gold trade can be chosen better than "always long". Same trade object and outcome matrix as rounds A-C (XAUUSD+ M1 bid/ask; stop = target = k x ATR20; entry at the open of the bar T+60 s on the executable side; forced exit 21:55; tie = loss), taken from the round-C caches (XAUUSD column), so no new price code.

## Honest prior
Daily direction rules on gold (ORB, Donchian, range fade, trend pullback, USD-proxy and real-yield filters) all failed in earlier families; the confirmed gold EAs are trend followers. P(survivor) under 5%. A "survivor" that is mostly long in 2025 is the trend, which is why the long-only yardstick is part of the bar.

## Trials (28)
- 24 rule cells: signal {M5, M1, AM} x {continue, fade} x T {10:05, 16:35} x k {0.4, 0.7} on gold only: side = sign of the score (continue) or the opposite (fade). A day with a zero or missing score is skipped.
- 4 ML cells: walk-forward HistGradientBoosting (depth 3, 100 iterations, lr 0.06, min leaf 100 because only 2 candidates a day exist, L2 1.0), quarterly refit, expanding window, scored from 2022-12-01; features m1 m5 m20 am pdh pdl apos rr arng spr tvr dow plus the MT5-calendar USD surprise already published today (sign flipped: a USD-positive surprise is gold-negative) and the number of importance-3 USD events in the next 4 hours; the side with the higher predicted R is taken. T x k.

## Acceptance (all required)
DEV (rules 2021-12..2024; ML 2022-12..2024): mean R > 0, block-t >= 2.91 (Bonferroni 28, one-sided 5%), mean R above the baseline (mean of long and short) AND above the always-long yardstick of the same (T,k). VAL 2025: mean R > 0, block-t >= 1.65, >= 200 days, above the always-long yardstick. Survivors: audit (by side, year, month, ex-best-20-days, spread x2), MT5 broker rolling starts, then HOLD 2026-01-01..2026-09-30 (ML: ..08-14) once.

## Gates
Oracle side (rules) and label leak (ML) must score > +0.3 R; placebo worlds (rules: noise scores, seeds 121-123; ML: labels permuted across days, seeds 131-133) must give 0 survivors each. Truncation was tested for these scores and features in rounds A-C; the USD calendar features use the round-B code (tested).

## Dry-run record (2026-10-14, before any cell P&L)
1,066 days, 1,005 valid gold days at each T; feature coverage 96-100%. The USD calendar surprise is non-zero on 0% of days at 10:05 (US releases come at 15:30 server) and 51% at 16:35; importance-3 USD events ahead on 48% of days at 16:35. A descriptive "short share" column was removed from the code before any run (it could miscount days when both sides lose); no trial or bar changed.
