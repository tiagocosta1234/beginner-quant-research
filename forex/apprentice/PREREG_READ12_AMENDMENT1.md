# PREREG_READ12 Amendment 1: the naive 08:00 rule as a second hypothesis

Written 26 Oct 2026 ~00:3x local (local clock), after training day R040, BEFORE READ12 is frozen and BEFORE the test pool is drawn (`state_r12x` empty).

## Why
- Training (40 days, Feb-May 2026): read12 34 trades, mean R +0.109, excess +0.129 (P 0.20); naive 08:00 30-minute trend with the same 1:1 bracket, 40 trades, 25 W, mean R +0.226, excess +0.259 (P 0.044); always-long -0.081.
- In 2026 the bracket is 5-30 points, so costs are small in R: the realised win / loss ratio is about 0.95-0.98:1, against 0.73-0.76:1 in 2019-2025. This is a mechanical reason a rule that failed on older years could differ now.
- The same naive rule FAILED on READ11's sealed 2019 / 2024 / 2025 days (P 0.35). That result stands; this tests it only on 2026.

## Change
- **H2 (mechanical):** the `naive_trend30` line already scored (side = sign of 08:00 close - 07:30 close, signal 08:00, `bracket11` 1:1 at X), on every test day.
- **Bar for each of H1 (read12) and H2:** excess >= +0.10, sign-flip **P <= 0.015**, mean R > 0, mean R > always-long, n >= 30. (0.015 replaces 0.03 for H1: two shots.)
- `read12.py` prints a PRIMARY line for each.
