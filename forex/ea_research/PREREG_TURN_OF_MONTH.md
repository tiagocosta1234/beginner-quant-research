# Pre-registration: turn-of-the-month effect on MT5 broker index CFDs (family M, two trials)

Written 2026-10-10 (time = the commit adding this file), BEFORE any statistic. the trader: "(original wording omitted)" (test the turn of the month from the QuantifiedStrategies article; documented by Ariel 1987, Lakonishok and Smidt 1988, McConnell and Xu 2008: most of the US equity return falls on the last trading day and the first three of the next month).

## Rules
Markets: SP, NSDQ, DOW (America/New_York, "close" = 15:55) and DAX (Europe/Berlin, close = 17:25), equal notional; MT5 broker M1 bid/ask; buy at the ask, sell at the bid, +0.1 bp per side. Trading days of a market = weekdays with a quote at its close minute; day -1 = the last trading day of a month, +1 = the first of the next.
M1 (classic window, days -1 .. +3): buy at the close of day -2, sell at the close of day +3.
M2 (wider window, days -4 .. +3): buy at the close of day -5, sell at the close of day +3.
One trade per market per month; event P&L = mean over the markets with both quotes, in bp.
Diagnostic (not a trial): mean daily close-to-close return on window days vs all other days (placebo), per market.
Periods: DEV 2022-01 .. 2024-12 (36 months), VAL 2025 (12), HOLD-OUT 2026-01 .. 2026-09 (9, one look).

## Acceptance (Bonferroni, two trials)
1. DEV mean > 0 and t (over months) >= 2.24. 2. VAL mean > 0. 3. HOLD-OUT mean > 0.
Goal relevance: about 5 days a month in the market; at 1% risk per idea the contribution per month is reported.

## Honest prior
About 15% (strong historical record, weaker since 2000 in several studies; only 36 DEV months, so only a large effect passes).
