# PREREG GN9 - late-day continuation on big-move days (leveraged-ETF rebalancing and dealer hedging), Nasdaq, S&P and gold (3 trials)

Registered 2026-10-18 14:34 local (local clock, second PC PC-2), before any P&L of these trials was computed.
the trader: "push it and keep testing the remaining 17". GN1-GN8 used 27 of the 40 variants of this research window.

## Why this test (a flow mechanism not tested here)
- Leveraged and inverse ETFs (TQQQ, SQQQ, UPRO, SPXU, ...) must rebalance near the close by AUM x L(L-1) x (the day's return):
  they buy on up days and sell on down days, more on big days. Options dealers who are short gamma hedge the same way.
  Baltussen, Da, Lammers and Martens (2021, JFE) show that the return from the previous close to 30 minutes before the close
  ("rest of day", ROD) predicts the last half hour in 60+ futures markets, most strongly on large-move days.
- Tested here before: Gao et al.'s FIRST-half-hour signal on all days (BRK-IMOM: gross about zero on MT5 broker indices 2022-26), the
  noise-area breakout (NA: Nasdaq passed 2022-24, failed the 2026 hold-out). Never tested: the ROD signal, restricted to the
  big-move days where the rebalancing flow is concentrated.

## Rule (every input known at the decision minute)
- Reference close: indices the 15:59 New York minute (16:00 is MT5 broker's rollover start); gold the 13:29 New York minute (COMEX
  settlement). Decision minute: indices 15:29, gold 12:59 (close).
- ROD = mid(decision close) / mid(reference close of the previous session) - 1.
- **Big-move day: |ROD| >= the 75th percentile of |ROD| on the previous 250 eligible days** (at least 60 earlier values;
  expanding window until 250).
- Entry at the next minute's open (15:30 / 13:00) in the direction of ROD (ask for a buy, bid for a sell). Exit at the close of
  the 15:58 / 13:28 minute (bid for longs, ask for shorts).
- Protective stop 2 S from the entry, S = mean absolute mid move from the decision close to the exit close over the previous 14
  eligible days; **R = 2 S**. Engine `brk_patterns.walk` (stop counted on the fill minute).
- Eligible day: the decision, entry and exit minutes and the previous session's reference minute are present.

## Trials (3)
- **L1** NSDQ. **L2** SP. **L3** XAUUSD (COMEX last half hour; weaker prior: gold leveraged ETFs are small, the hedging channel
  is the COMEX options book).
- Descriptive (no decision): DOW; every trial on the other (not big) days; long-only on the same days; by |ROD| quartile.

## Controls
- Random direction on the same days (5 draws: same entry minute, stop distance and exit). Information = trial mean - control mean
  (`gn2.info`).
- The same rule on the other days (the mechanism predicts a larger effect on big days).

## Periods
- DEV: MT5 broker 2022-01-03 .. 2024-12-31. VAL: MT5 broker 2025.
- OOT: CME futures 2020-01-02 .. 2021-12-31 (Databento NQ / ES / GC 1-minute) with the MT5 broker cost model of GN5 / GN6 (bid = trade
  price, ask = trade + the MT5 broker median spread in the 15:30-15:58 / 13:00-13:28 window); NQ / ES roll Mondays excluded; GC days with
  a contract switch or flip minute excluded (`gn6.bad_minutes`). The first 60 eligible days of each source are warm-up.
- HOLD: MT5 broker 2026-01-02 .. 2026-10-16; opened once, only for a trial that passes DEV, VAL and OOT.

## Acceptance (all required)
- DEV: n >= 80; mean net R > 0 with day-clustered t >= 2.13 (Bonferroni, 3 one-sided trials); information > 0 with t >= 1.65;
  mean above the same rule on the other days; positive in at least 2 of the 3 years.
- VAL: mean > 0 with t >= 1.65, and information > 0. OOT: mean > 0 with t >= 1.65. HOLD: mean > 0 with t >= 1.65.
- Account environment: replay from 95,472 (MT5 broker rules, 5-day block bootstrap of 2022-25 days) at $250 / $500 a trade (R = 2 S);
  usable only if P(pass) > P(breach) by 30 Jun 2027.

## Dry run (no P&L)
Counts by period, share of big days, median S in spreads (cost check), port check 2022-24 (MT5 broker against futures: same side >= 80%,
R correlation >= 0.6), truncation test (data cut on 2023-06-30 at 12:00 New York: identical trades before the cut), hand check of
2 trades.

## Honest prior
About 6% for L1 and L2, 3% for L3. Against: Gao's version is gross zero here, and since 2022 zero-day options may have made dealers
net long gamma intraday (damping). For: the flow is mechanical, grew with leveraged-ETF assets, and big days concentrate it.

## Running count
GN1-GN8 27 + GN9 3 = 30 of 40 variants in this research window.
