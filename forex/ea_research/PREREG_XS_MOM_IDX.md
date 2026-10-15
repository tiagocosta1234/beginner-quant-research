# PREREG_XS_MOM_IDX - cross-country index momentum, market-neutral (written 2026-10-15, before any P&L; commit time = registration time)

## Idea
Country equity-index momentum (Asness, Moskowitz & Pedersen 2013, "Value and momentum everywhere"): indices that out-performed over the past 3-12 months keep out-performing for a while. Long the strongest, short the weakest: market-neutral, so it would be a leg uncorrelated with the D2 drift book. Swap-free terms remove the financing of both legs. Not tested here before (BRK_XS tested intraday relative strength of breakouts, TREND_PORT tested time-series trend).

## Rules (fixed now)
- Universe: SP, NSDQ, DOW, DAX, NIKKEI, ASX (MT5 broker M1; P&L in USD with EURUSD / USDJPY / AUDUSD).
- Weekly decision Monday 18:00 server (as D2). Signal: local-currency return from the close 252 (C1) or 63 (C2) trading days ago to the close 5 days ago (skip the last week), each scaled by its 60-day volatility. Long the top 2, short the bottom 2, each leg 1/4 of gross, inverse-vol scaled within the leg so each position has equal ex-ante risk; re-trade only names that change or move > 25% from target.
- Execution: buys at the ask, sells at the bid of the 18:00 bar; positions marked at the bid (longs) / ask (shorts) at 22:55 server.
- Cells: C1 (12-1 month), C2 (3 months minus last week). 2 trials, Bonferroni over 2.

## Periods
DEV 2022-24, VAL 2025 (MT5 broker). OOT on MT5 broker D1 2020-21: with the 252-day window C1 can only trade from about January 2021 (no pre-2020 data); C2 from about April 2020. HOLD 2026 one look for a passer.

## Acceptance (all required)
1. DEV+VAL daily t >= 1.96 (one-sided 2.5%: 5% over 2).
2. Mean > 0 in DEV, VAL and OOT.
3. HOLD mean > 0; correlation with D2 reported.

## Honest prior
Country momentum has a gross Sharpe near 0.3-0.5 in the long studies, six highly correlated indices make a thin cross-section (US three of six), and four years is little. Prior about 10%.
