# Pre-registration: combine every tested strategy with a fixed selection rule and per-strategy risk limits (family X, one procedure)

Written 2026-10-10 (time = the commit adding this file), BEFORE the combination is computed. the trader: "combine all strategies that are smooth through the whole data timeline and filter risk for each one of them" -> "(original wording omitted)".

## Universe (every daily P&L stream already built, winners AND losers)
The two legs of the gold pair at x1.2 (ManualSDB, XAUUSD 5 minute; MT5 broker trades scaled to MT5 broker prices, no guard), the 272 factory variants (`factory.py`), the 480 overnight-grid variants (`overnight_grid.py`, rebuilt through 2026-09), crypto weekend long W1, turn-of-month M1/M2, COT P1/P2, pre-FOMC V1. All on one weekday calendar 2022-01-03 .. 2026-09-30, days without a position = 0.

## Fixed procedure
1. Selection on DEV 2022-24 only: a stream enters if its DEV daily t >= 2.0 and its DEV mean > 0.
2. Risk filter per stream: scaled so its DEV daily sd = 300 USD (inverse volatility); its daily loss is floored at -500 USD (a per-strategy daily stop, an optimistic approximation since the intraday path is not modelled).
3. Portfolio = sum of the selected streams, then one scalar so the DEV daily sd of the sum = 800 USD (about the pair's at x1.2).
4. Evaluation, nothing changed after step 3: VAL 2025 and 2026 (Jan-Sep): mean USD/day, daily Sharpe, max drawdown; and P(pass the MT5 broker test within 15 / 36 / 52 business days) by a stationary block bootstrap of that period's portfolio days (guard -2,000, counted cap 2,000, breach -2,500 or floor 92,000).
5. The same evaluation for the gold pair alone, scaled to the same DEV sd, as the yardstick.

## Honest prior
About 80% that the rule selects (almost) only the pair's two legs and the portfolio looks like the pair; about 10% that it finds a useful diversifier. Caveat written now: the pair's SDB leg was itself tuned on 2021-26 gold, so its DEV statistics are not clean out-of-sample.
