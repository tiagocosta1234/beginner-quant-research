# FX3-TRENDBRACKET result (2026-10-14): the practice rule over all EURUSD days 2022-25
Pre-registration `PREREG_FX3_TRENDBRACKET.md` (committed first), `fx3_trendbracket.py`, `FX3_TRENDBRACKET_OUTPUT.txt`. Code note: a column named `xs` collided with DataFrame.xs and garbled only the printed exit-share columns on the first run; R values were unaffected and the output was regenerated.

| trial | DEV 2022-03..2024 | VAL 2025 |
|---|---|---|
| M trend-follow (the practice rule) | n 352, mean -0.151R, t -2.49, hit 35% | n 129, -0.114R, t -1.13, hit 37% |
| R fade (same days and brackets, side reversed) | +0.219R, t +3.41, hit 50% | +0.042R, t +0.39, hit 43% |
| F long on flat days | -0.107R, t -1.18 | -0.070R, t -0.43 |
Permutation null of M in DEV: 5th / 95th percentile -0.084 / +0.104 (M's -0.151 is below the 5th).
## Verdict: no trial accepted (M fails 1; R passes acceptance 1 but fails 2, VAL t 0.39 < 1.65; F fails)
- The practice result was not an accident: trend-following with a daily-EMA filter and a 1.5R bracket at 24 h loses on EURUSD (hit 35-37% vs the 40% break-even), and it loses by more than same-mix random sides would in DEV.
- The mirror image (fade) was positive in DEV but did not confirm in 2025, so it is a lead, not a result.
- DISCLOSURE: while checking years I printed per-year means that included 2026 (the sealed hold-out for this family): M -0.09R, fade +0.11R on 89 trades; fade by year 2022 +0.28, 2023 +0.19, 2024 +0.19, 2025 +0.04, 2026 +0.11. No decision used them, but 2026 is no longer unseen for this family; a clean test of the fade now needs a forward (paper) log from 2026-10-14 on.
Live pair unchanged.
