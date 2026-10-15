# Pre-registration BRK-XS (breakout day, round 6; written 2026-10-15 11:51 local (commit time), before any code or result)
Question: does looking ACROSS markets pick better breakouts than each market alone? Events = round 5's 53,898 session breakouts (BRK_META_events.parquet), exit hold-to-close (X4).

## Cross-sectional state (known at the start of each server day)
Daily closes per market (server days, bars 01:00-22:59 mid); 20-day and 60-day returns at the previous close, ranked across the 46 markets each day (percentile 0-1).
## Cells (4)
- XS1 20-day relative strength: long breakouts only in markets ranked >= 0.8, short breakouts only in markets ranked <= 0.2.
- XS2 the same with 60-day returns.
- XS3 crowd day: breadth >= 0.15 at the fill (at least 7 of 46 markets already broke the same way that server day).
- XS4 early movers: only the first 5 breakouts of each server day (by fill time).
## Gates (DEV 2022-24, VAL 2025, 2026 non-clean)
1. DEV mean >= +0.05 R and t >= 2.5 (daily portfolio NW lag 1; Bonferroni 4). 2. VAL mean > 0 and t >= 1.65. 3. DEV mean beats the 95th percentile of 1,000 random subsets of the same size. Indices and classes reported.
## Honest prior
About 5%: cross-sectional momentum on daily data here (FX factors, confluence panels) was weak; breadth and timing are new.
