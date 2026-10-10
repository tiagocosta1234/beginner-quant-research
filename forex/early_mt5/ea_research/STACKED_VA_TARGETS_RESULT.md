# G-T: best target for the stacked-value-area entries: result (2026-10-10, local local clock)

Pre-registration `PREREG_STACKED_VA_TARGETS.md` (commit b573e4d, before any target statistic), script `stacked_va_targets.py`, output `STACKED_VA_TARGETS_OUTPUT.txt`, ledger family stacked_va_targets (14 rows). Hold-out NOT opened.

## Verdict: no target makes the entry profitable; the best in DEV (the opposite edge of the zone) is +0.04 R with t +0.48 and loses in 2025
| target (entries with the trend filter, G1) | DEV 2022-24: win, mean R, PF, t | VAL 2025: win, mean R |
|---|---|---|
| T1 1.0 R | 46.1%, -0.086, 0.83, -2.05 | 42.4%, -0.159 |
| T2 1.5 R | 40.0%, -0.045, 0.92, -0.89 | 37.1%, -0.122 |
| T3 2.0 R | 36.4%, -0.013, 0.98, -0.22 | 32.9%, -0.125 |
| T4 3.0 R | 31.7%, -0.007, 0.99, -0.11 | 29.4%, -0.124 |
| T5 POC "magnet" | 41.0%, -0.011, 0.98, -0.17 | 34.8%, -0.176 |
| **T6 opposite zone edge (best DEV)** | 30.6%, **+0.041**, 1.06, +0.48 | 31.0%, -0.066 |
| T7 previous day's extreme (video) | 30.4%, +0.020, 1.03, +0.25 | 28.4%, -0.117 |
Without the trend filter (G2) every target is negative in DEV and in 2025.

## Why
After entry, price reaches +1 R before the stop in only 42% of trades. A random entry with a symmetric stop and target would do so about 50% of the time before costs. The median move in our favour before the stop is 0.75 R, and 67% of trades end at the stop. The entry carries no directional information, so moving the target only trades win rate for payoff (46% at 1 R, 31% at 3 R) at the same negative mean. This is this repo's Round 153 lesson again: an exit cannot create an edge the entry lacks.
