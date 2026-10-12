# Why XAU5 at 500 USD per trade "makes 7,639 a month" but passes only about 17% in 22 days (2026-10-12)

MT5 broker 12-month pool (real ticks), XAU5 sized so the median losing trade is 500 USD (about 0.17 lot), 236 start days.

| | No guard, no news flat (the 7,639/month table) | With the 1,500 guard + CPI news flat |
|---|---|---|
| Net, 12 months | +91,673 | +63,515 |
| Mean per month | 7,639 | 5,293 |
| Months >= 8,000 | 6 of 12 | 4 of 12 |
| Days with a floating loss <= -2,500 (hard breach) | **36**, the first on 2025-10-17 | 0 (worst day -2,497) |
| Counted profit with the 2,000/day cap | 46,227 of 91,673 (50%) | **26,323 of 63,515 (41%)** |
| Start on each day, pass within 22 days | 19% (but **79% breach first**) | 17% (breach 3%) |

1. The 7,639 figure had no daily stop: it breaches the 2,500 daily loss limit on 36 days, the first two weeks in, so the account would not have survived to collect it.
2. With the guard the average falls to 5,293 a month (4 of 12 months reach 8,000).
3. MT5 broker counts at most 2,000 of profit a day: only 26,323 of the 63,515 would count, about 2,200 a month counted, against the 8,000 target. Big days are wasted above the cap.
