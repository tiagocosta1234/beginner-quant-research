# PREREG_WALKFORWARD_RECENCY: does "trade what has been working lately" improve the London first-15m indicator?

Written Mon 26 Oct 2026 ~09:3x local (local clock), BEFORE any result of this test was computed. the trader: "edges dont last forever ... from time to time we have to adapt", then "run the walk-forward test of trade what's been working lately".

## Trades (fixed, not tuned)
- The frozen indicator `LONDON_FIRST15_1TO1.pine` = Edge Lab 5 variant D1 (follow the candle) with stop buffer 0.5 x range, risk floor 0.03 x prior ATR14, 1:1, exits on 1-minute bars, stop first on a tie, flat 16:00 London, same costs as Edge Lab 5 (1 tick per side + USD 1.20 per micro).
- Markets with 1-minute history here: GC, NQ, ES, SI (Databento, 2019-06-19 to 2026-09-25). No Dow (YM) data exists here.
- **Disclosure:** this opens Edge Lab 5's sealed 2024-2026 hold-out for this indicator. Edge Lab 5 had no finalist, so the hold-out was never going to be used for it; it is used here once, for this question only.

## Rules tested (walk-forward: on day t only results of days before t are used)
- **R20 / R40 / R60:** trade a market on day t only if the sum of ITS OWN net R over its previous 20 / 40 / 60 trading days (all days, traded or not, as the always-on indicator would have scored them) is above 0. Otherwise skip that market that day.
- **Baseline:** always trade (the indicator as it is).
- The first 60 days of each market are dropped for all rules, so every rule and the baseline are scored on the same days.

## Measures (one run, one look)
- For each rule: trades taken, mean net R of taken trades, the same for the baseline, and by calendar year.
- P = random-filter test: 20,000 draws; in each, for every market, the same NUMBER of days is switched on but at random days; P = share of draws whose mean taken R >= the rule's. This asks whether the recency rule picks better days than chance.
- **"Adaptation works" iff** for a rule: mean taken R net > 0 AND P <= 0.0167 (0.05 / 3 rules) AND mean taken R > 0 in at least 5 of the 7 years 2020-2026.
- Also reported (no bar): each market alone; a 2026-only line.

## Honest prior
Performance persistence in trading-rule returns is weak in the published evidence, and the base rule loses about 0.06 to 0.17 R a trade on 2019-2023, so a filter must find days the base rule gets right while the rest lose. Expected: no pass. A pass would justify a forward test of the filtered rule, not a purchase.
