# BRK26 result - 26 more new breakout concepts (named indicators and price-action patterns): 0 pass

Run 2026-10-18 evening (local clock, second PC PC-2). Pre-registration `PREREG_BRK26.md` (registered 19:18; SHA-256
b1b44afb8127ef52b620e7fd7475ae63985471e676150e6817a13a0dbe9c8586 in `data\scratch\brk26_prereg.sha256` before any P&L; no commits
on 18 Oct), engine `brk26.py` (BRK30's machinery), dry run `BRK26_DRYRUN.txt` (truncation identical on EURUSD, XAUUSD, NSDQ),
output `BRK26_OUTPUT.txt`, table `BRK26_SUMMARY.csv`, 26 ledger rows. 214,174 trades on the 38 non-crypto markets.
Bars: DEV 2022-24 n >= 150, t >= 2.89 (Bonferroni for 26), >= 2 of 3 years positive, information t >= 2.0; VAL 2025 t >= 1.65.

## Verdict: 0 of 26; hold-out sealed
- DEV t-values: mean -1.69, SD 2.36; 7 of 26 positive; 2 above t 1.65 (1.3 expected by luck); none above 2.89.
- The busy H1 signals lose the spread as in BRK30: TEMA cross -0.119 R (t -8.0, 22,629 trades), Williams %R burst -0.111 (t -4.2),
  StochRSI burst -0.094 (t -4.5), TRIX signal -0.100 (t -3.5), CMO -0.060, Al Brooks High 2 -0.143 (t -5.2). H4: Hull turn -0.113,
  Schaff -0.097, Fisher -0.086, Vortex -0.068, regression-slope turn -0.065, three-bar reversal -0.058, marubozu -0.071, Chaikin
  volatility -0.113; about zero: TRIX zero +/-0.02, Ultimate Oscillator +0.002, kumo twist +0.003, Balance of Power +0.021, Elder
  Ray -0.018, Awesome Oscillator -0.051, RVI -0.011.

## The positives (all fail)
| idea | DEV 2022-24 | years | VAL 2025 | why it fails |
|---|---|---|---|---|
| P09 KST signal cross D1 | +0.102 R (t 2.51), n 1,230, info t 2.29 | +0.15 / +0.07 / +0.10 | -0.132 (t -2.29) | DEV t below 2.89; reversed in 2025 |
| P23 inside-outside-inside D1 | +0.256 (t 2.29) | +0.07 / +0.57 / +0.14 | -0.018 | n 83 below 150; flat in 2025 |
| P07 Mass Index bulge H4 | +0.146 (t 1.23), n 331 | -0.02 / -0.19 / +0.53 | -0.388 (t -3.4) | one good year, then reversed |

## Account view (2022-25, from 95,472, MT5 broker rules, $50 a trade on the universe)
Nothing passes at any date (P09: 0.0% pass / 1% breach by June 2027).

## Goal tally (the trader's /goal "at least 100 more")
BRK100 79 new concepts + 21 out-of-sample market extensions, BRK26 26 new concepts: **126 tests, 105 of them new concepts, 0 passes.**
