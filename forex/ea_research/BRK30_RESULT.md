# BRK30 result - 30 untouched breakout ideas on the 38 MT5 broker: 0 pass, most lose the spread

Run 2026-10-18 evening (local clock, second PC PC-2). Pre-registration `PREREG_BRK30.md` (registered 17:42; SHA-256
e8eb1b710bf0163ebb71d581eb700ad61d334eebb23085c8318ec19f385245c5 in `C:\work\scratch\brk30_prereg.sha256` before any P&L; no commits
on 18 Oct at the trader's request), engine `brk30.py` (BRK50's `Mkt`), dry run `BRK30_DRYRUN.txt` (truncation identical on EURUSD,
XAUUSD, NSDQ), output `BRK30_OUTPUT.txt`, table `BRK30_SUMMARY.csv`, 30 ledger rows. 220,731 trades, 2022-01 .. 2026-10.
Bars per idea: DEV 2022-24 n >= 150, mean > 0 with t >= 2.94 (Bonferroni for 30), >= 2 of 3 years positive, information over the
mirror t >= 2.0; VAL 2025 t >= 1.65; the 2026 hold-out only for passers.

## Verdict: 0 of 30; hold-out sealed
- DEV t-values: mean **-1.62**, SD 1.80; only 4 of 30 positive; none above t 1.65 (1.5 expected by luck alone). This batch is
  clearly worse than chance, not just empty: the retail indicator signals pay the spread on MT5 broker and add nothing.
- The worst are the busiest: Bill Williams fractal + Alligator H1 -0.135 R (t -6.5, 18,198 trades), KAMA cross H1 -0.101 (t -5.3),
  regression-channel break H1 -0.113 (t -4.1), MACD signal cross H1 -0.107 (t -4.1), EMA 9/21 cross H1 -0.065 (t -2.7),
  low-chop Donchian H1 -0.073 (t -2.2): stops of about 25 spreads on H1 bars cost about 0.04 R a trade before any information.
- Patterns: double tops / bottoms H1 -0.057 (t -2.6), H4 -0.027; triple -0.060; broadening -0.002; morning / evening star -0.17
  (77 trades). Ichimoku: kumo break H4 -0.054, D1 +0.005, TK cross H4 -0.035. Aroon -0.038, ADX birth -0.032, CCI D1 -0.019 /
  H4 -0.062, golden cross -0.29 (148 trades). Elder triple screen -0.140 (t -2.6). Morning-range afternoon fade -0.024 (t -2.7).

## The few positives (all fail)
| idea | DEV 2022-24 | years | VAL 2025 | reading |
|---|---|---|---|---|
| K26 USDJPY London box in the direction of the 10-year yield's last change | +0.137 R (t 1.25), n 464 | +0.22 / +0.00 / +0.20 | +0.128 (t 0.84) | about what the unfiltered USDJPY London breakout earns (+0.146 / +0.108): the rate filter adds nothing |
| K29 outside-week follow | +0.094 (t 1.15), n 266 | +0.06 / +0.17 / +0.06 | -0.138 | gone in 2025 |
| K25 VIX spike -> safe-haven London boxes | +0.086 (t 0.70), n 412 | -0.10 / +0.19 / +0.19 | +0.082 | noise-sized; gold side negative |
| K07 Ichimoku kumo break D1 | +0.005 (t 0.08), n 615 | +0.07 / +0.00 / -0.04 | -0.177 | zero |

## Account view (2022-25 trades, from 95,472, MT5 broker rules)
None of the five best passes at any date (universe at $50 a trade or Nasdaq + gold at $250); K25 at $250: 0.1% pass / 20% breach
by June 2027.

## Reading
After BRK50 (54), BRK50B (50), GN1-GN13 (40) and now BRK30 (30), the untested breakout ideas that can be written as fixed rules
on MT5 broker's price data are used up. Whatever information these signals carry is smaller than MT5 broker's spread at the bar sizes where they
trade often, and the slower ones (daily / weekly) carry about none.
