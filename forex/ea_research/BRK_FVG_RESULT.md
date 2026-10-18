# BRK_FVG result - an unmitigated FVG between entry and stop helps the breakout a little, not enough (0 of 4 pass)

Run 2026-10-16 20:33 local (local clock, second PC). Pre-registration `PREREG_BRK_FVG.md` (registered 20:28, no amendments; frozen by
sha256 at 20:33:12 in `C:\work\scratch\brk_fvg_freeze.txt`, not committed first: GitNexus cannot run on this second PC). Engine
`brk_fvg.py`, output `BRK_FVG_OUTPUT.txt`. Same 91,988 first-touch events and trades as BRK_TWOWAY (symmetric one-box bracket,
real bid/ask, 38 non-crypto markets). HOLD 2026 sealed. Dry run: truncation identical on 3 markets; hand checks correct.

## Verdict
| trial | DEV n | DEV net R (t) | DEV win | same leg without the FVG | difference (t) | DEV years | VAL with / without |
|---|---|---|---|---|---|---|---|
| London FOLLOW + FVG inside the box | 8,127 | -0.043 (-2.40) | 47.8% | -0.081 (46.0%) | +0.037 (+2.90) | -0.03 / -0.03 / -0.07 | -0.052 / -0.095 |
| London FADE + FVG beyond the box | 5,457 | -0.076 (-3.77) | 46.1% | -0.098 (45.1%) | +0.022 (+1.49) | -0.04 / -0.10 / -0.09 | -0.081 / -0.080 |
| New York FOLLOW + FVG inside the box | 7,748 | -0.019 (-1.18) | 49.1% | -0.049 (47.5%) | +0.030 (+2.51) | -0.02 / -0.05 / +0.01 | +0.013 / -0.066 |
| New York FADE + FVG beyond the box | 6,413 | -0.071 (-4.08) | 46.3% | -0.087 (45.5%) | +0.016 (+1.25) | -0.07 / -0.06 / -0.09 | -0.118 / -0.089 |
No trial has a positive DEV mean, so none passes. The confluence is present on 17-32% of events; on about half of the days
with a gap in the breakout zone, every gap there had already been filled before the touch ("unmitigated" bites).

## What it says
- **For breakouts the FVG is a real, if small, improvement:** with an unmitigated FVG in the break direction inside the box,
  the follow trade is 0.03-0.04 R better in 2022-24 (t 2.5-2.9, both sessions) and 0.04-0.08 R better in 2025, with a
  1.5-2 point higher win rate. A likely reading: an untouched gap inside the box marks an impulsive move through the box that
  has not retraced, i.e. momentum into the level. It lifts the breakout from clearly negative to about zero (New York 2025
  +0.013), not to a profit.
- **For bounces it does nothing reliable:** a gap beyond the box in the fade direction improves the fade by 0.02 R in DEV
  (t 1.2-1.5) and not at all or negatively in 2025.
- By class (2022-25): with the FVG, New York index breakouts +0.034 R and metals +0.014 R (without: -0.014 / -0.079); FX and
  energy stay negative. These are subsets seen after the fact.

## In the account's environment (standing rule; NSDQ + XAUUSD, $250 a trade, 2022-25 trades, from 95,472, MT5 broker rules)
| trial | trades, R a trade | 22 Dec pass / breach | 30 Jun 2027 pass / breach |
|---|---|---|---|
| London FOLLOW + FVG | 662, -0.059 | 0.0% / 3% | 0.0% / 41% |
| London FADE + FVG | 521, +0.005 | 0.0% / 1% | 0.0% / 18% |
| New York FOLLOW + FVG | 739, +0.057 | 0.0% / 0% | 0.0% / 5% |
| New York FADE + FVG | 519, -0.057 | 0.0% / 0% | 0.0% / 26% |
Even the best (New York breakouts with the FVG on Nasdaq and gold, +0.057 R a trade, chosen after the fact) has 0% chance to
pass by mid-2027: about 180 trades a year at +0.057 R x $250 is roughly +$2,600 a year against a $12,528 target.

## Window
FVG-confluence family: 4 of 40 variants; closed for these rules (no tuning after the result). The follow-side effect could be
pre-registered once as an out-of-time check (2020-21, a different data source) if the trader wants to pursue it.
