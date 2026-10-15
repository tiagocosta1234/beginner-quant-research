# PREREG_SWAPFREE_D2X - does a wider swap-free book beat D2? (written 2026-10-15, before any P&L; commit time is the registration time)

## Question
D2 (PREREG_SWAPFREE_DRIFT: inverse-vol long book of SP, NSDQ, DAX, NIKKEI, XAUUSD with a 200-day trend filter, weekly) passed every edge bar with Sharpe about 1.2. The markets whose financing is most expensive on a normal CFD account are crypto (often 10-20% a year); MT5 broker's swap-free terms remove it. Does adding crypto, or more equity / metal markets, raise the Sharpe?

## Variants (3 trials, Bonferroni over 3)
- X1 D2 + BTCUSD + ETHUSD (7 markets).
- X2 D2 + XAGUSD + DOW + ASX (8 markets; ASX P&L converted with AUDUSD).
- X3 D2 + all five (10 markets).
Every rule as D2 (60-day inverse-vol weights, 200-day SMA filter per market, weekly Monday 18:00 server decision, 25% no-trade band, buys at the ask, marks at the bid, day low = conservative sum of each market's worst bid). Crypto weekend moves are booked on Monday (the engine marks weekdays; weekend lows are not seen: stated).

## Data and periods
- MT5 broker M1 bid/ask for DEV 2022-01-03..2024-12-31, VAL 2025, HOLD 2026-01-01..2026-10-02 (one look, only for a variant that passes).
- OOT 2020-01..2021-11 on MT5 broker D1 bars (another broker's MT5 data; the whole OOT book, D2's markets included, uses MT5 broker D1 so the variants and the D2 reference are comparable): fill at the Monday daily close plus MT5 broker's median 18:00 spread of 2022-24 (a data-resolution proxy for the decision time; D2's sensitivity showed 16:00 / 18:00 / 20:00 decisions are equivalent), mark = daily close, day low = daily low. Trading starts once 200 daily closes exist inside 2020 (about October 2020): no pre-2020 data.
- Signals for the MT5 broker periods: MT5 broker D1 closes from 2020-01 ratio-spliced to MT5 broker marks at 2021-12-01 (signals only).
- Reference (not a trial): D2 rerun on exactly this setup.

## Acceptance (all required)
1. DEV+VAL daily t >= 2.13 (one-sided 5% / 3).
2. Mean > 0 in DEV, VAL and OOT.
3. Annualised Sharpe higher than the D2 reference on the same setup in BOTH DEV and VAL (else the wider book is not better and D2 stays the candidate).
4. HOLD mean > 0 (one look).
5. Reported: worst day low per 100k gross, max drawdown, correlation with the gold pair, and the account table as in SWAPFREE_DRIFT.

## Honest prior
Crypto had a -65% year (2022) inside DEV; the 200-day filter should have been out for most of it, but crypto also whipsaws around the average. More correlated equity markets add little diversification. Prior that a variant passes 1-4: about 25%.
