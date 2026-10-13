# Pre-registration: best exit target for the stacked-value-area entries (family G-T, 14 trials)

Written 2026-10-10 (time = the commit adding this file), BEFORE any target statistic. the trader: "(original wording omitted)". Entries exactly as `PREREG_STACKED_VA.md` (G1 with the trend filter, G2 without), stop unchanged (2 bp beyond the signal bar), same costs and end-of-day exit (22:55 server).

## Targets (7, fixed now)
T1 1.0 R; T2 1.5 R; T3 2.0 R; T4 3.0 R; T5 the zone's "magnet": the mean of the three previous POCs (the video's point-of-control idea); T6 the opposite edge of the stacked zone; T7 the previous day's extreme (the video's rule, already tested: G1 +0.026 R / G2 -0.030 R in DEV).
A target that is not beyond the entry in the trade's direction (T5/T6 on the wrong side) makes the trade a skip for that target. A minute that touches both the stop and the target counts as the stop.

## Selection and acceptance (Bonferroni over 7 targets x 2 entry sets = 14)
DEV 2022-24: choose the target with the highest mean R per entry set. It is accepted only if its DEV t >= 2.7, mean R > 0, >= 200 trades, and VAL 2025 mean R > 0; then the 2026 hold-out is opened once (mean R > 0). All 14 rows are reported.
Also reported (descriptive): the distribution of maximum favourable excursion before the stop in R, which shows how far these entries tend to run.

## Honest prior
About 7%. This repo's own lesson (Round 153): exits cannot create an edge the entry lacks, and an exit chosen in-sample decays out of sample. With a 30% hit rate on 4 R the entries are close to random; a nearer target will raise the win rate (that is mechanical) without making the mean positive unless there is real short-term reversion after the rejection bar.
