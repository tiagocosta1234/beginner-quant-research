# Family I (2026-10-09 21:49 local): gold 30-minute opening-range breakout at the London and New York opens, 1% risk, frequent - both fail (ledger 60 -> 62)

Pre-registration `PREREG_ORB_GOLD.md` (21:48, before any run), runner `orb_gold.py`, output `ORB_GOLD_OUTPUT.txt`, ledger rows `orb_gold` (I1, I2). Inspired by the Comet search (Perplexity, Google, fxabsolute.com research, algotrader.ch), see the pre-registration for what was found.

| trial | DEV 2022-24 | VAL 2025 | 2026 (not opened as a hold-out) | verdict |
|---|---|---|---|---|
| I1 London 08:00 box | 770 trades, +0.007 R, PF 1.02, daily t +0.20 | 256, +0.086 R, PF 1.22, t +1.48 | -0.089 R | fails (DEV) |
| I2 New York 09:30 box | 755 trades, +0.052 R, PF 1.14, daily t +1.64 | 253, -0.030 R, PF 0.93, t -0.54 | -0.067 R | fails (VAL negative, DEV t < 2.5) |
Frequency: about 42 trades a month with both sessions (about 2 a day), 1% risk each. Cost share of R only 3-7% at MT5 broker costs (it was 5-20% in the outside study), so costs are not what kills these; the gross edge is about zero: pooled mean +0.03 R, i.e. +0.03% per trade at 1% risk, roughly +0.6% a month. Per year the sign flips (I1: +0.07, +0.02, -0.08, +0.09, -0.09; I2: +0.14, 0.00, +0.01, -0.03, -0.07), a typical noise pattern. Correlation with the live pair: +0.04 and -0.04.
The descriptive 56% "continuation to 1R" of the outside page does not turn into an edge once the 31% unresolved paths, the stop at the opposite side and the costs are modelled: the realised win rate is 50-53% at +1 R / -1 R.

## What the Comet search says about "frequent, 1% risk, super profitable"
- Independent test (fxabsolute.com, 2026-08-29): 20 popular gold strategies, 39,947 trades, 1% risk: 0 significant after correction, 13 below random entries, best -3.8% vs +142% buy and hold; cost as a share of R explains most of the ranking (-0.86), M5 scalps start 16% of R behind. This agrees with our 62 registered trials.
- What would be needed for the trader's target (8% in about a month): about +0.3 R net per trade at 3+ trades a day. The best documented structure in public data is +0.05 to +0.1 R before costs; the best we measured is the live pair (SDB about +0.2 R per trade at 3 trades a MONTH, in-sample).
- The one structural fact in our favour is gold's volatility regime: the M15 ATR went from 2.1 USD (2023) to 5.6 (2025) and 11.3 (2026), which shrinks cost per R (MT5 broker median spread 0.21 USD, no commission). That helps any frequent gold rule, but it is also why results move with the regime, and nothing here makes the gross edge positive.
