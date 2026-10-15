# Pre-registration BRK-B20 (breakout day, round 20; written 2026-10-15 12:45 local (commit time), before any code or result)
Question: since 94% of breakouts return inside the box within an hour (BRK-ANATOMY), does demanding MORE of the breakout help? Same 46 markets, session 30-minute box, stop at the other side of the box, hold to the session close (round 1 execution and costs); orders until open + 3 h.
- **U1 / U2 / U3 buffered stop orders:** buy stop at box high + b x box, sell stop at box low - b x box, b = 0.10 / 0.25 / 0.50 (stop still at the box's other side, so R grows with the buffer).
- **U4 tested level:** plain stop orders, taken only if the broken box edge was touched at least 3 separate times inside the box (a touch = a minute whose bid high (low) is within 10% of the box height of the edge, separated by at least 5 minutes).
- **U5 double level:** plain stop orders, taken only if the broken box edge lies within 10% of the box height of the previous server day's high (for an up-break) / low (for a down-break).
Random-entry control per cell (same window, random side, same R). Gates (DEV 2022-24, VAL 2025, 2026 non-clean): DEV mean >= +0.05 R and t >= 2.58 (daily NW lag 1; Bonferroni 5); VAL mean > 0 and t >= 1.65; beats its control by >= 0.05 R in DEV and VAL.
Honest prior: about 5%.
