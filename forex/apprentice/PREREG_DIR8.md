# PREREG_DIR8: what is known at 08:00 that tells a gold morning's direction, BOTH sides

Written 23 Oct 2026 (local clock, time in the commit), before any feature was computed against an outcome.
the trader: "we cant only rely on longs, you have to know when its time to short too" / "set it up twin".

## Why
- The blind 08:00 bias (BIAS8) is 32/60, below always-long (34/60).
  - The up-rate on my long days (59%) equals the up-rate on my short days (57%): no selection skill on either side.
- Here a fixed, simple model reads only pre-08:00 data and is judged on days it never saw. The question is whether it calls shorts as well as longs.

## Honest prior
- Single features usually predict a few hours of gold direction at about 51-53%. A pass here is unlikely; about 10-15%.
- Power: VAL has about 480 days. One-sided P <= 0.05 against 50% needs about 54%; against always-long it needs more.

## Data (the trader's scope rule: 2020 onward only)
- Databento 1-minute GC (target and gold features), SI and ES (cross-market features), local clock.
- **DEV:** 2020-01-01 .. 2022-12-31 (fit). **VAL:** 2023-01-01 .. 2024-12-31 (judge). **HOLD:** 2025-01-01 .. 2025-12-31, one look after a VAL pass. 2026 is never loaded.
- Days: weekdays playable under `bias8.day_data`: full 07:00-16:59 bars, the previous weekday's 08:00-21:59 exists, no GC minute-to-minute jump above $8 from 00:00 to 16:59.
  - The day is skipped if SI or ES has no 00:00-07:59 bars, or an overnight move above 5% (roll).

## Target
- y = 1 if the GC 11:59 close > the 08:00 open, else 0.

## Features (all from bars before 08:00; S = ATR14 of 15-minute GC bars ending 07:59, as in bias8)
1. `on`: overnight GC move (07:59 close - 00:00 open) / S
2. `l30`: last 30 minutes (07:59 close - 07:30 open) / S
3. `pd`: previous day (21:59 close - 08:00 open) / S
4. `asia_loc`: where the 07:59 close sits in the 00:00-07:59 range, -0.5 .. +0.5
5. `pd_loc`: where it sits in the previous day's 08:00-21:59 range, -0.5 .. +0.5
6. `trend20`: (07:59 close / mean of the last 20 daily 21:59 closes - 1) / the 20-day std of daily % changes
7. `si_on`: SI overnight % move (07:59 close / 00:00 open - 1)
8. `es_on`: ES overnight % move
9. `vol`: log(S / median S of the previous 20 days)
- Each feature is winsorised at its DEV 1st / 99th percentile and standardised with DEV mean / std.

## Model (fixed, no tuning)
- Logistic regression (scikit-learn, L2, C = 1.0), fit once on DEV.
- Call = long if p > 0.5, else short. Forced every day.

## Trade measure
- Hold 08:00 -> 12:00: R = side x (11:59 close - 08:00 open) / S, minus 2 ticks of slippage and 0.15 commission (in S units).
- Secondary bracket (no bar): stop 2 S, target 3 S, 12:00 exit, desk fills (`bias8.sim`).

## Bars, all on VAL (one look)
- **(a)** hit rate > always-long's hit rate on the same days, AND one-sided binomial P <= 0.05 against 50%;
- **(b) shorts work:** short-call hit rate > 50% AND short-call mean R > 0;
- **(c)** overall mean R > 0, one-sided t P <= 0.05.
- **PASS = (a) and (b) and (c).** Then HOLD 2025: mean R > 0 and short-call mean R > 0 confirm.

## Reported, no bar
- DEV in-sample (inflated by the fit);
- each single feature's VAL hit rate (sign rule fitted on DEV);
- the coefficients;
- long-call vs short-call results;
- a top-half-confidence subset (|p - 0.5| above the DEV median);
- the bracket; the trader's +0.5 R bar.

## Rules
- No change after the first VAL number. `--dry-run` prints counts, feature ranges and a truncation causality test, and no outcome.
- Results go to `DIR8_RESULT.md` and the ledger, pass or fail.

## Amendment 1 (before any VAL number was shown)
- The first `--run` crashed at the bracket line before printing anything: pandas renames a leading-underscore column inside `itertuples`. The column `_x` was renamed `xf`. No logic changed. Re-hashed.
