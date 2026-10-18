# BRK50 result - 54 new breakout ideas, 0 pass; one lead worth an out-of-time check (I20, fading the day after a big day)

Run 2026-10-17 23:00 local (local clock, second PC). Pre-registration and brief `PREREG_BRK50.md` (registered 22:48; amendment 1
before any P&L, amendment 2 after the dry run before any P&L was looked at; frozen by sha256 at 23:00:39 with the trade cache,
`C:\work\scratch\brk50_freeze.txt`; not committed first because GitNexus cannot run on this second PC). Engine `brk50.py`, output
`BRK50_OUTPUT.txt`, table `BRK50_SUMMARY.csv`. 758,019 trades, 46 markets, 2022-01..2026-10-16, real MT5 broker bid/ask with zero-spread
minutes repaired. Dry run: truncation identical on EURUSD / XAUUSD / NSDQ / BTCUSD; hand checks correct. HOLD 2026 sealed for all.

## Verdict
**0 of 54 pass.** Not one idea reaches t > 1.65 in DEV 2022-24 (pure luck would give about 3 of 54); the mean DEV t is -2.49
(sd 2.67): as a group these breakouts lose to costs. 9 of 54 have a positive DEV mean; none clears the Bonferroni bar (t >= 3.12).

## All 54 ideas (net R a trade; DEV 2022-24 t; DEV years; VAL 2025)
| idea | DEV n | DEV R (t) | years | VAL R (t) |
|---|---|---|---|---|
| I01 PDH/PDL break | 16,238 | -0.039 (-3.1) | -0.04/-0.04/-0.04 | -0.046 (-2.2) |
| I02 PDH/PDL fade | 16,238 | -0.024 (-2.3) | -0.02/-0.03/-0.03 | -0.002 (-0.1) |
| I03 PDH/PDL 1-h close | 12,913 | -0.046 (-3.7) | -0.06/-0.04/-0.04 | -0.041 (-1.9) |
| I04 PDH/PDL with strong close | 5,220 | -0.052 (-2.6) | -0.06/-0.05/-0.04 | -0.078 (-2.2) |
| I05 prior-week H/L break | 4,610 | -0.027 (-0.6) | -0.08/-0.07/+0.07 | -0.182 (-2.6) |
| I06 prior-week H/L fade | 4,603 | -0.053 (-3.0) | -0.05/-0.02/-0.10 | -0.034 (-1.2) |
| I07 prior-month H/L break | 1,081 | -0.073 (-1.2) | -0.12/-0.12/+0.01 | +0.058 (0.4) |
| I08 prior-month H/L fade | 1,080 | -0.065 (-2.0) | -0.07/-0.01/-0.12 | -0.100 (-1.6) |
| I09 prior-quarter H/L break | 374 | -0.289 (-4.5) | -0.28/-0.38/-0.20 | +0.065 (0.4) |
| I10 inside-week break | 607 | +0.037 (0.7) | -0.00/+0.09/+0.02 | -0.103 (-1.0) |
| I11 floor pivot R1/S1 break | 17,482 | -0.031 (-2.2) | -0.01/-0.05/-0.04 | -0.025 (-1.0) |
| I12 floor pivot R1/S1 fade | 17,416 | -0.038 (-3.1) | -0.05/-0.03/-0.03 | -0.024 (-1.3) |
| I13 Camarilla H4/L4 break | 16,574 | -0.085 (-4.2) | -0.03/-0.12/-0.10 | -0.062 (-1.6) |
| I14 Camarilla H3/L3 fade | 19,735 | -0.041 (-2.9) | -0.08/-0.03/-0.01 | -0.019 (-0.8) |
| I15 weekly pivot break | 4,681 | -0.054 (-2.6) | -0.06/-0.08/-0.02 | -0.115 (-4.1) |
| I16 yesterday's body break | 13,081 | -0.042 (-2.6) | -0.02/-0.02/-0.09 | -0.038 (-1.3) |
| I17 3-day range break | 11,759 | -0.027 (-2.8) | -0.03/-0.04/-0.01 | -0.028 (-1.6) |
| I18 outside-day follow | 884 | -0.082 (-2.1) | +0.00/-0.13/-0.12 | -0.172 (-2.6) |
| I19 post-expansion break | 564 | -0.130 (-2.1) | -0.16/-0.04/-0.17 | -0.197 (-2.0) |
| **I20 post-expansion fade** | 564 | **+0.100 (1.6)** | **+0.06/+0.12/+0.12** | **+0.310 (1.6)** |
| I21 Crabel stretch | 28,012 | -0.084 (-3.7) | -0.07/-0.13/-0.05 | -0.113 (-3.4) |
| I22 morning expansion follow | 2,515 | -0.075 (-2.6) | -0.11/-0.06/-0.06 | -0.149 (-2.9) |
| I23 morning compression break | 1,531 | +0.007 (0.1) | +0.10/-0.07/+0.01 | +0.029 (0.4) |
| I24 half-day range break | 24,861 | -0.076 (-4.6) | -0.06/-0.08/-0.09 | -0.078 (-3.0) |
| I25 prior NY range in London | 11,768 | -0.014 (-0.9) | +0.02/-0.02/-0.04 | -0.031 (-1.2) |
| I26 triple compression | 1,499 | +0.043 (0.5) | +0.30/-0.18/+0.07 | -0.031 (-0.2) |
| I27 tight-Asia break | 7,776 | -0.050 (-1.6) | +0.06/-0.15/-0.04 | -0.064 (-1.3) |
| I28 TWAP 2-SD break | 29,272 | -0.133 (-4.8) | +0.01/-0.20/-0.21 | -0.201 (-4.6) |
| I29 TWAP 2-SD fade | 28,465 | -0.220 (-8.7) | -0.14/-0.20/-0.32 | -0.228 (-5.2) |
| I30 Frankfurt open | 12,833 | -0.102 (-3.4) | -0.07/-0.14/-0.10 | -0.135 (-2.6) |
| I31 NY FX open | 4,991 | -0.122 (-3.0) | -0.04/-0.17/-0.15 | -0.139 (-2.2) |
| I32 pre-08:30-data range | 6,914 | -0.048 (-1.3) | +0.05/-0.09/-0.11 | -0.071 (-1.2) |
| I33 COMEX gold open | 1,443 | -0.031 (-0.7) | +0.07/-0.05/-0.11 | -0.125 (-1.6) |
| I34 NYMEX oil open | 1,418 | -0.142 (-2.9) | -0.08/-0.17/-0.17 | -0.122 (-1.3) |
| I35 Tokyo open | 5,636 | -0.056 (-1.7) | -0.02/-0.02/-0.13 | -0.085 (-1.6) |
| I36 Sydney open | 6,917 | -0.138 (-4.3) | -0.22/-0.07/-0.13 | -0.127 (-2.6) |
| I37 London close / fix | 20,223 | -0.098 (-6.3) | -0.09/-0.12/-0.08 | -0.115 (-4.2) |
| I38 NY lunch range | 7,118 | +0.002 (0.1) | +0.00/+0.00/+0.00 | -0.091 (-3.5) |
| I39 risk-aligned yen crosses | 2,783 | +0.031 (0.5) | +0.15/-0.09/+0.03 | -0.032 (-0.3) |
| I40 risk-aligned indices | 1,181 | -0.032 (-0.5) | +0.06/-0.13/-0.06 | +0.089 (0.7) |
| I41 oil-aligned USDCAD | 415 | +0.064 (1.0) | -0.03/+0.23/-0.03 | -0.187 (-1.9) |
| I42 gold-silver confirmed | 887 | -0.029 (-0.4) | +0.17/-0.02/-0.24 | -0.072 (-0.6) |
| I43 quiet-London NY break | 3,145 | +0.017 (0.4) | +0.08/-0.01/-0.01 | -0.007 (-0.1) |
| I44 Monday break of Friday | 2,958 | -0.037 (-1.6) | +0.02/-0.07/-0.06 | +0.018 (0.5) |
| I45 Friday afternoon break | 5,110 | -0.107 (-2.8) | -0.10/-0.06/-0.16 | -0.098 (-1.5) |
| I46 re-break after failure | 21,979 | -0.039 (-1.6) | +0.03/-0.11/-0.04 | -0.092 (-2.4) |
| I47 large-box fade | 689 | +0.104 (1.1) | +0.27/-0.17/+0.07 | -0.173 (-1.2) |
| I48 Keltner H1 | 14,488 | -0.076 (-2.9) | -0.06/-0.06/-0.10 | -0.154 (-3.4) |
| I49 Bollinger H1 | 17,676 | -0.081 (-3.5) | -0.08/-0.07/-0.10 | -0.162 (-4.2) |
| I50 Bollinger re-entry fade | 25,304 | -0.102 (-7.7) | -0.09/-0.09/-0.13 | -0.096 (-4.0) |
| I51 Donchian H4 | 4,854 | -0.034 (-1.2) | -0.02/-0.08/+0.00 | -0.220 (-4.8) |
| I52 crypto Donchian H4 | 1,275 | -0.121 (-1.8) | -0.18/-0.31/+0.11 | -0.070 (-0.6) |
| I53 crypto UTC-open ORB | 6,002 | -0.460 (-14.7) | -0.51/-0.62/-0.31 | -0.179 (-2.9) |
| I54 crypto weekend range | 1,054 | -0.348 (-3.8) | -0.67/-0.37/-0.13 | -0.095 (-0.5) |

## What it says
1. **New level types do not change the picture.** Prior-day / week / month / quarter highs and lows, floor and Camarilla pivots,
   bodies, 3-day ranges and TWAP bands lose on breaks and on fades alike (-0.02..-0.22 R). Direction information (trade minus
   its mirror) is within noise for almost all of them: the level carries no side.
2. **Exchange opens are as bad as the London / NY boxes** (Frankfurt, NY FX open, COMEX, NYMEX, Tokyo, Sydney, London fix:
   -0.03..-0.14 R). Narrow boxes in spreads drive the cost (Sydney 10, Frankfurt 13 spreads median width).
3. **Conditions and cross-asset alignment** (compression, quiet London, risk alignment via Nasdaq, oil for USDCAD, gold-silver)
   lift some ideas to about zero, never to a reliable profit; every one fails in at least one period.
4. **Bar-close channels (Keltner, Bollinger, Donchian H4) lose** after costs; crypto ideas lose most (spreads 15-70 bp).
5. **The one consistent idea is I20, fading the day after a big day:** when yesterday's range exceeded 1.8 ATR, fading the
   first touch of yesterday's high / low earned +0.06 / +0.12 / +0.12 R (2022 / 2023 / 2024) and +0.310 R in 2025, with
   direction information +0.21 R (t 1.8); its mirror (I19, following the break) loses in every year. It is still far below the
   bar (t 1.6 on 564 trades; n is small because big days are rare), and it was 1 of 54. It is the only candidate for one
   pre-registered out-of-time check (2020-21 HistData, on the main PC), with the 2026 hold-out still unopened.

## In the account's environment (standing rule; the 5 best by DEV t; MT5 broker rules from 95,472)
| idea | sample | trades 2022-25, R a trade | 22 Dec pass / breach | 30 Jun 2027 pass / breach |
|---|---|---|---|---|
| I20 post-expansion fade | NSDQ + XAUUSD, $250 | 57, +0.309 | 0.0% / 0% | 0.0% / 0% |
| I20 | 38 markets, $50, <= 5 a day | 644, +0.078 | 0.0% / 0% | 0.0% / 0% |
| I47 large-box fade | NSDQ + XAUUSD, $250 | 16, +1.145 | 0.0% / 0% | 0.0% / 0% |
| I47 | 38 markets, $50 | 704, +0.107 | 0.0% / 0% | 0.0% / 0% |
| I41 oil-aligned USDCAD | USDCAD, $50 | 536, +0.007 | 0.0% / 0% | 0.0% / 0% |
| I10 inside-week break | NSDQ + XAUUSD, $250 | 37, +0.073 | 0.0% / 0% | 0.0% / 0% |
| I10 | 38 markets, $50 | 630, +0.032 | 0.0% / 0% | 0.0% / 0% |
| I39 risk-aligned yen crosses | 6 markets, $50 | 3,459, +0.001 | 0.0% / 3% | 0.1% / 32% |
Even the best ideas trade too rarely, at too small an edge, to move the account: I20 at $50 a trade on all markets is about
160 trades a year x 0.078 R x $50 = ~$620 a year against the $12,528 still needed.

## Window
BRK50 family: 54 fixed rules in one window (the trader's goal; above the usual 40); closed. Only I20 may be carried forward, as one
pre-registered out-of-time test with no change to its rule.
