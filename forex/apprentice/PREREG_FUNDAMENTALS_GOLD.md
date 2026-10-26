# PREREG_FUNDAMENTALS_GOLD: does a fundamental (macro) bias improve the London first-15m indicator on gold?

Written Mon 26 Oct 2026 ~09:4x local (local clock), BEFORE any result of this test was computed. the trader: "we need to add fundamentals to our trading".

## Trades
The frozen indicator (`LONDON_FIRST15_1TO1.pine` = Edge Lab 5 D1, buffer 0.5, floor 0.03 ATR, 1:1, 1m exits, stop first, flat 16:00, micro costs) on GC (Databento 1-minute), 2019-09 to 2026-09, every day with data. Each day also has its mirror trade (same entry, stop and target distances, other side, net of costs), so any side can be scored.

## Fundamental biases for gold (all known at the PRIOR day's close, nothing from the trade day)
- **F1 Real yields:** US 10-year TIPS yield (FRED DFII10). Change over the last 5 published values up to the day before: falling = LONG gold, rising = SHORT, unchanged = none. (Gold's classic driver: lower real yields lower the cost of holding gold.)
- **F2 Dollar:** euro futures (6E, Yahoo daily) as the inverse dollar. Prior close above its 20-day average = weak dollar = LONG gold; below = SHORT.
- **F3 Both:** F1 and F2 agree = that side; disagree = none.
- **F4 Event days (2022-2026 only, the calendar starts in 2022):** skip days in `data_macro/event_calendar.csv` (US high-impact releases and FOMC), trade the rest with the indicator's side.

## Two ways to use F1-F3
- **Filter:** take the indicator's trade only when its side equals the bias (no bias = no trade).
- **Override:** trade the bias side every day it has one (the candle only sets the stop and target).

## Bar (one run, one look; 7 tests: F1-F3 x filter / override + F4; alpha 0.05 / 7 = 0.007)
"Fundamentals help" for a test iff: mean net R of its trades > 0 AND random P <= 0.007 AND mean > 0 in at least 5 of the 7 years 2020-2026 (F4: 3 of 5 years 2022-2026) AND n >= 300.
- Random P, filter and F4: 20,000 draws of the same number of days at random (same side as the indicator); P = share with mean >= observed.
- Random P, override: 20,000 draws flipping each day's side by coin; P = share with mean >= observed.
- Also reported (no bar): the indicator alone, each year, and 2026 alone.

## Honest prior
Daily macro drivers move gold over days and weeks; a 15-minute London candle trade held to 16:00 at 1:1 may barely feel them. The earlier VIX / rates / copper conditions on breakouts did not hold up out of time (BREAKOUT_KNOWLEDGE 13e/13j). Expected: no pass. A pass means a forward test, not a purchase.
