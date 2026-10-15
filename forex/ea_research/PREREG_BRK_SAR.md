# Pre-registration BRK-SAR (breakout day, round 18; written 2026-10-15 12:28 local (commit time), before any code or result)
Same session boxes and first breakouts as round 1 (46 markets, stop at the other side of the box, hold to the close).
- **SAR stop-and-reverse:** when the first breakout's stop (the other side of the box) is hit before the time exit, open the opposite position at that same moment (fill = the stop's fill price on the other side of the quote: ask for a new long, bid for a new short), stop at the first breakout's side of the box, hold to the session close. The second leg alone is the cell (the first leg is round 1's X4).
- **STREAK:** the round-1 breakout (X4) taken only when the same market's previous session breakout made money (X4 > 0) - a short-memory regime by market.
Random-entry control for SAR (a random minute after the first stop-out, random side, same R). Gates (DEV 2022-24, VAL 2025, 2026 non-clean): DEV mean >= +0.05 R and t >= 2.24 (daily NW lag 1; Bonferroni 2); VAL mean > 0 and t >= 1.65; SAR beats its control and STREAK beats the unconditional breakout by >= 0.05 R in DEV and VAL.
Honest prior: about 5%.
