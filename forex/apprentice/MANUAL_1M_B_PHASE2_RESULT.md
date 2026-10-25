# MANUAL_1M_B phase 2 result: FAIL (scored 25 Oct 2026, local clock)

Rules and gate were frozen and hashed before the test (`MANUAL_1M_B.md`, `MANUAL_1M_B.sha256`, Amendment 1 = window from 16 Jun 2025). Data: FX Replay export, `MANUAL_1M_B_PHASE2_TRADES.csv` (37 closed trades, 17 Jun - 12 Aug 2025; Notion has 38 rows, B43-B80, the last one of 13 Aug 2025 is not in the export, probably still open).

## Gate
Mean R >= +0.30 after costs (about 24 wins of 40). NOT MET, and not close.

## Numbers (R as FX Replay reports it, costs = 0.11 R a trade)
- All 37 closed: 13 W / 20 L / 4 breakeven (R = 0), mean -0.06 R, after costs -0.17 R, standard error 0.19. Longest losing streak 3. One-sided P that a true mean of -0.11 R gives this result or better: 0.62 (no sign of an edge).
- In the frozen 08:00-09:20 window only (35 trades): 13 W / 18 L / 4 BE, mean -0.01 R, after costs -0.12 R.
- Short of 40: 37 closed (38 logged). Protocol notes: two trades entered after 09:20 (11 Jul 09:39, 5 Aug 09:45); four trades ended at exactly 0 R (7 Jul, 25 Jul, 1 Aug, 4 Aug), which suggests a stop moved to breakeven, against "stop not moved afterwards".
- Long 24: mean +0.03 R. Short 13: mean -0.23 R.

## Pre-declared descriptive split (Amendment 1), NOT a bar
- 08:00-08:15 entries: n=19, 9 W / 7 L / 3 BE, mean +0.29 R (after costs +0.18 R).
- 08:15 and later: n=18, 4 W / 13 L / 1 BE, mean -0.43 R.
- Phase 1 showed the same shape in 2023 (08:00-08:15: +0.40 R, n=19; later: -0.15 R, n=22). Two separate samples, same direction. Pooled early window: 38 trades, about +0.34 R before costs (about +0.23 after), standard error about 0.19: suggestive, not proven (the slice was picked after phase 1, and several slices were looked at).

## Verdict and what follows
- Phase 2 FAILS. Per the frozen plan: no purchase, no re-tuning on these days (16 Jun - 12 Aug 2025 are now seen).
- The only follow-up the data supports is a NEW pre-registered test (phase 3) of one narrower rule, "08:00-08:15 entries only", on fresh days, with its own gate. Nothing is bought before it passes.
