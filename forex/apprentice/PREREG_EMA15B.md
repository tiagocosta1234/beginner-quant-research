# PREREG_EMA15B: EMA15 with the trader's minimum target of 2.5 points ($1,000 at 40 MGC), sized so a winner pays about $1,000

Written 23 Oct 2026 (local clock, time in the commit), after EMA15 failed and before any P&L of this variant.
the trader: "the target has to be minimum at the distance where the account makes 1000$ at 40 micros, doesnt mean you always have to get in with 40 micros".

## Change from PREREG_EMA15 (everything else identical: data, periods, signal, trends T50 / T80 / TPD / NONE, levels, fills, costs)
- **Minimum target distance: 2.5 points** (40 MGC x $10 a point x 2.5 = $1,000), replacing 0.5 x ATR14(15m).
  - Target = the nearest qualifying level at least 2.5 points from the entry. Stop 1:1 at the same distance.
- **Size:** MGC = floor(1000 / (10 x D)), at most 40, at least 1.
  - $ result = size x $10 x net points, with commission 0.15 points a round turn per MGC (about $1.50).
- **Honest caveat:** this is a second look at the same DEV data, chosen after seeing EMA15 fail. Selection risk is real. That is why the bar stays VAL + HOLD.

## Bars (same as EMA15)
- **DEV pick:** the best DEV mean R; it must be > 0, or the family fails.
- **VAL:** the picked trial's VAL mean R > 0 with one-sided t P <= 0.05, and above its no-trend version.
- **HOLD 2025:** one look, only after a VAL pass.
- Also reported: $ per trade, $ a year, the worst losing streak in $, and the trader's live bar of +0.5 R.
