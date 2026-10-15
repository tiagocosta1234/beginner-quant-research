# Pre-registration BRK-L2NY (breakout day, round 36; written 2026-10-15 14:43 local, local clock, before any code or result)
Question: does the London MORNING range, broken during the New York session, carry more information than the 30-minute opening boxes (the range is wider, so the spread is a smaller share of R)?
For every market (46) and day: box = bid high / low of 08:00-12:00 London; one-cancels-other stop orders (buy at ask >= high, sell at bid <= low) live 12:00-16:00 London; first fill wins; hold to 20:00 London (capped 22:55 server); R >= 2 spreads; no entry in server hours 23 / 0. Engine with the fill-minute rule (`brk_hours.hold_fill`).
- **N1:** stop at the other side of the box (R = full box).
- **N2:** stop at the box middle (R = half box).
Random-entry control (random minute 12:00-16:00, random side, same R and exit). Gates (DEV 2022-24, VAL 2025, 2026 non-clean): DEV mean >= +0.05 R and t >= 2.24 (daily NW lag 1; Bonferroni 2); VAL mean > 0 and t >= 1.65; beats its control by >= 0.05 R in DEV and VAL. Reminder: the M1 engine is ~0.03 R a trade optimistic vs real ticks (TICK_GAP_RESULT).
Honest prior: about 5%.
