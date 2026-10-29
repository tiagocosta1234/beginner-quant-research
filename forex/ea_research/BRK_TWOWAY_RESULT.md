# BRK_TWOWAY result - 22 confluences cannot tell a break from a bounce at the box edge (0 of 4 pass)

Run 2026-10-16 20:23 local (local clock, second PC); direction diagnostic 20:24-20:25. Pre-registration `PREREG_BRK_TWOWAY.md`
(registered 20:18; amendment 1 ~20:21 before any label or P&L was looked at; frozen by sha256 at 20:23:01 in
`data\scratch\brk_twoway_freeze.txt`, plus a post-run time-stamp correction recorded there). Engine `brk_twoway.py`, output
`BRK_TWOWAY_OUTPUT.txt`. 91,988 first-touch events, 38 non-crypto MT5 broker, 2022-01..2026-10-16; HOLD 2026 sealed.

## Base rates (symmetric bracket: stop and target one box width from the entry, exit at the session end)
| box | follow wins | always FOLLOW | always FADE |
|---|---|---|---|
| London, DEV 2022-24 | 45.1% | -0.070 R | -0.094 R |
| London, VAL 2025 | 44.5% | -0.083 R | -0.080 R |
| New York, DEV | 39.0% | -0.041 R | -0.084 R |
| New York, VAL | 39.8% | -0.044 R | -0.095 R |
Both directions lose: each pays the spread, and neither side wins more than half of the time.

## Trials
| trial | DEV trades | DEV net R (t) | follow leg win / R | fade leg win / R | placebos (3) | DEV years | AUC DEV / VAL | VAL net R (t) |
|---|---|---|---|---|---|---|---|---|
| London COUNT | 15,550 | -0.103 (-9.19) | 46.8% / -0.063 | 43.1% / -0.138 | -0.082 / -0.093 / -0.088 | -0.07 / -0.10 / -0.13 | 0.509 / 0.511 | -0.092 (-5.06) |
| London GBM | 11,114 | -0.111 (-8.96) | 47.7% / -0.046 | 40.4% / -0.188 | -0.111 / -0.110 / -0.100 | -0.04 / -0.15 / -0.14 | 0.522 / 0.523 | -0.105 (-5.11) |
| New York COUNT | 12,422 | -0.049 (-3.58) | 47.0% / -0.055 | 47.6% / -0.042 | -0.065 / -0.067 / -0.074 | -0.04 / -0.05 / -0.06 | 0.541 / 0.549 | -0.007 (-0.30) |
| New York GBM | 11,228 | -0.038 (-3.11) | 48.6% / -0.027 | 47.0% / -0.050 | -0.087 / -0.072 / -0.079 | -0.03 / -0.03 / -0.05 | 0.586 / 0.587 | -0.014 (-0.67) |
All four lose in DEV and VAL. London is no better than the shuffled-label placebo; New York beats its placebos by
0.02-0.05 R but stays negative.

## What the models actually predict (diagnostic, not a trial)
| | AUC for DIRECTION, given one side was hit | AUC for "a full box move happens before the session end" |
|---|---|---|
| London COUNT (DEV / VAL) | 0.508 / 0.512 | 0.536 / 0.483 |
| London GBM | 0.516 / 0.518 | 0.656 / 0.642 |
| New York COUNT | 0.507 / 0.523 | 0.635 / 0.620 |
| New York GBM | 0.519 / 0.528 | 0.770 / 0.771 |
- **Direction is a coin flip:** among the events where one side of the bracket was hit, the models separate "continued"
  from "bounced" with AUC 0.51-0.53. The predicted-break group continued 46-49% of the time against a 46% base; the
  predicted-bounce group bounced 38-48% against a 44-45% base.
- **What is predictable is the size of the move, not its side:** New York GBM predicts whether price travels a full box
  width before the close with AUC 0.77, steady in 2025; its top features are box/ATR and box/spread (permutation
  importance), i.e. small boxes relative to the day's range get resolved, big ones expire. The follow-win deciles
  (22% -> 47%) are this effect, not direction.
- Feature importance (GBM, AUC drop): London box/spread 0.037, box/ATR 0.015, then app5, delay, volreg, tr5, box_in_pd, tr20
  (each <= 0.009); New York box/ATR 0.074, box/spread 0.021, delay 0.013, class 0.012, then range_so_far, volreg, weekday, tr20.

## In the account's environment (standing rule; NSDQ + XAUUSD, $250 a trade, from 95,472, MT5 broker rules, DEV out-of-fold + VAL trades)
| trial | trades, R a trade | 22 Dec pass / breach | 30 Jun 2027 pass / breach |
|---|---|---|---|
| London COUNT | 986, -0.036 | 0.0% / 7% | 0.0% / 46% |
| London GBM | 680, -0.026 | 0.0% / 2% | 0.0% / 31% |
| New York COUNT | 803, -0.050 | 0.0% / 3% | 0.0% / 43% |
| New York GBM | 956, +0.005 | 0.0% / 2% | 0.0% / 24% |
No trial passes in any path; all drift toward the floor.

## Reading for the trader
More confluences do raise a "prediction rate", but of the wrong thing: they tell you better whether price will move far
(after a narrow box on an active day) and not whether the level breaks or holds. With the information on the chart at the
moment of the touch, break vs bounce is about 50/50 on MT5 broker 2022-26, and trading both ways pays the spread twice.

## Window
Two-way level classifier family: 4 of 40 variants; family closed.
