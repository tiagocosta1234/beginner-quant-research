# Pre-registration BRK-COST (breakout day, round 10; written 2026-10-15 11:59 local (commit time), before reading these cells)
Clue from BRK-ANATOMY: the breakout's information is a few hundredths of R while a spread costs 0.04-0.22 R; indices look best mainly because their boxes are wide relative to the spread. Test a COST filter instead of a pattern filter on the same ~54,000 session breakouts (rows `BRK_ANATOMY.parquet`, exit hold-to-close = close_R).
Cells (2): K1 = box at least 25 median spreads wide (spread <= ~0.04 R); K2 = box at least 40 spreads wide. The box width in spreads is known at the box end (causal).
Gates: 1. DEV 2022-24 mean >= +0.03 R and t >= 2.24 (daily portfolio NW lag 1; Bonferroni 2). 2. VAL 2025 mean > 0 and t >= 1.65. 3. The breakout beats its own random entries (same filter) by >= 0.03 R in DEV and VAL. 2026 reported (non-clean). Classes reported (if it is only indices again, it is not a new finding).
Honest prior: about 10%.
