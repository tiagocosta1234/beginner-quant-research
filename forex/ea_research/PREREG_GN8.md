# PREREG GN8 - dealer-gamma regime (VIX) and the New York opening-range breakout, Nasdaq and S&P (4 trials)

Registered 2026-10-18 14:27 local (local clock, second PC PC-2), before any P&L of these trials was computed.
the trader: "push it and keep testing the remaining 17" (variants of this research window; GN1-GN7 used 23 of 40).

## Why this test (new information and a mechanism)
- Breakout information on MT5 broker was strong in 2022 (indices +0.149 R over random entries) and gone afterwards (BREAKOUT_KNOWLEDGE
  fact 4). 2022 was a high-VIX year (median 25.5; VIX >= 20 on 91% of days); 2023-24 were calm (VIX >= 20 on 17% / 10%).
- Mechanism (Baltussen, Da, Lammers and Martens 2021, "Hedging demand and market intraday momentum"; Barbon and Buraschi 2020,
  "Gamma fragility"): options dealers who are net SHORT gamma hedge by trading with the move, so moves extend and breakouts
  follow through; dealers who are net LONG gamma trade against the move, so moves fade and breakouts return into the range.
  Dealer gamma is not observable here; the usual proxy for the stress (short-gamma) regime is an elevated VIX.
- Not tested before in this repo: breakout rounds conditioned on each market's own ATR rank (BRK-VOLREG V3: indices +0.049 /
  +0.030 / -0.025 R) and on post-options-expiry days (BRK-CAL C2: worse); the VIX was used only on the gold pair's daily P&L
  (VOL_REGIME_RESULT.md).
- Data: Yahoo daily VIX (`futures/data/daily/^VIX_yahoo_daily.csv`, close, 1990 .. 2026-09-21). The regime of day d
  is the VIX close of the last trading day before d (known before the 09:30 open). **Stress day: VIX(d-1) >= 20; calm day:
  VIX(d-1) < 20.** The level 20 is fixed now (the long-run mean of the VIX and the common regime line). Rejected before any P&L:
  the front-curve ratio VIX9D / VIX (it flips with scheduled events: inverted on 28% of days in calm 2023, median spell 2 days)
  and VIX >= VIX3M (3% of days in 2022-24, too few trades).

## Base rule: the New York 30-minute opening-range breakout
- Box: bid high / low of the 09:30-09:59 New York minutes (at least 24 of the 30 minutes present); W = high - low.
- Window: 10:00-11:59 New York (at least 90 of its 120 minutes present), first touch only.
- **FOLLOW:** buy stop at the box high (fills when the ask reaches it; at the minute's ask open if already beyond), sell stop at
  the box low (bid); first fill wins; both in one minute = no trade. Stop at the other side of the box; no target; exit at the
  15:55 New York minute (close of 15:54; bid for longs, ask for shorts).
- **FADE:** sell limit at the box high (fills when the bid reaches it; at the bid open if beyond), buy limit at the box low
  (fills when the ask reaches it); first touch wins; both in one minute = no trade. Stop one box width beyond the touched edge
  (high + W / low - W), target the other edge of the box (low / high); exit at 15:55 if neither is hit.
- R = |entry - stop|. Costs: the MT5 broker bid/ask in the bars. Engine `brk_patterns.walk` (the stop counts on the fill minute, the
  target from the next minute).

## Trials (4)
- **V1** NSDQ FOLLOW on stress days. **V2** SP FOLLOW on stress days.
- **V3** NSDQ FADE on calm days. **V4** SP FADE on calm days.
- Descriptive only (no decision): DOW for all four; every rule on the opposite regime; FOLLOW and FADE by VIX band.

## Controls
- Unconditional random entries on the same eligible days (5 a day: random minute in the 10:00-11:59 window, random side, stop
  W away; the fade control also has the W target), the GN2+ standard. Information = trial mean - control mean (independent
  standard errors, `gn2.info`).
- Regime contrast: the same rule on the opposite regime's days.

## Periods
- DEV: MT5 broker 2022-01-03 .. 2024-12-31. VAL: MT5 broker 2025.
- OOT: CME futures (Databento NQ / ES 1-minute) 2020-01-02 .. 2021-12-31, with the MT5 broker cost model of GN5 / GN6 (bid = trade
  price, ask = trade + the MT5 broker median spread in the 09:30-15:55 window), roll Mondays excluded.
- HOLD: MT5 broker 2026-01-02 .. 2026-09-22 (the VIX file ends on 2026-09-21); opened once, only for a trial that passes DEV, VAL and OOT.

## Acceptance (all required)
- DEV: n >= 80; mean net R > 0 with day-clustered t >= 2.24 (Bonferroni, 4 one-sided trials); information > 0 with t >= 1.65;
  mean above the same rule on the opposite regime; positive in at least 2 of the years with >= 10 trades (every such year
  positive if there are fewer than 2).
- VAL: mean > 0 with t >= 1.65, and information > 0.
- OOT: mean > 0 with t >= 1.65.
- HOLD: mean > 0 with t >= 1.65.
- Account environment: replay from 95,472 (MT5 broker rules, 5-day block bootstrap of 2022-25 days) at $250 / $500 a trade, and the
  combined book (FOLLOW on stress days + FADE on calm days, both markets) at $150 a trade; usable only if P(pass) > P(breach)
  by 30 Jun 2027.

## Live note
MT5 broker's MT5 has no VIX. An EA would need a daily VIX file (like ManualNews.csv); by hand, the trader reads the previous VIX close before
09:30 New York (14:30 local).

## Dry run (no P&L)
Counts by period and regime, median box in spreads, the MT5 broker window spread (futures cost model), port check 2022-24 (MT5 broker against
futures on common days: same side >= 80%, R correlation >= 0.6), truncation test (data and VIX cut on 2023-06-30 12:00 New York:
identical trades before the cut), hand check of 2 trades.

## Honest prior
About 8% for each FOLLOW trial and 6% for each FADE trial. In DEV the regime cut is close to "2022 against 2023-24", so DEV mostly
re-measures 2022; the stress days of 2025, the 2020-21 futures and the 2026 hold-out decide.

## Running count
GN1-GN7 23 + GN8 4 = 27 of 40 variants in this research window.
