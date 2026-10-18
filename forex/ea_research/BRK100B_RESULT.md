# BRK100B result - 100 ideas on information the breakout tests never used (MT5 broker spread, CME volume, cross-market states) plus untested named systems: 0 pass

Run 2026-10-18 22:14 (local clock, second PC PC-2). Pre-registration `PREREG_BRK100B.md` (registered 21:39; SHA-256
f569d817e62a2bb355252df7db17dc80cf6b4233218d1b0d370722df7514a1b6 recorded 21:47:48 in `C:\work\scratch\brk100b_prereg.sha256` after
a time-stamp correction, before any code ran; no commits on 18 Oct), engine `brk100b.py` (BRK50 / BRK100 machinery, lesson-(a) entries),
dry run `BRK100B_DRYRUN.txt` (truncation identical on EURUSD, XAUUSD and NSDQ for trades AND helper states; 12 hand checks), output
`BRK100B_OUTPUT.txt`, table `BRK100B_SUMMARY.csv`, 100 ledger rows. 483,673 trades on the 38 non-crypto markets.
Bars: DEV 2022-24 n >= 100, day-clustered t >= 3.29 (Bonferroni for 100), >= 2 of 3 years positive, information t >= 2.0; VAL 2025
t >= 1.65.

## Verdict: 0 of 100; the 2026 hold-out stays sealed
- DEV t-values: mean -1.20, SD 1.84; 27 of 100 positive; 3 above t 1.65 (5 expected by luck); none above 3.29; no DEV + VAL passer.

| group | tests | DEV t mean | positive | t > 1.65 | mean R |
|---|---|---|---|---|---|
| A MT5 broker spread as information (MT5-native) | 14 | -1.54 | 3 | 0 | -0.06 |
| B + G CME volume (research) | 34 | -0.31 | 16 | 3 | -0.04 |
| C cross-market states (MT5-native) | 8 | -0.79 | 1 | 0 | -0.08 |
| D + E untested named systems / statistical filters (price only) | 37 | -2.24 | 2 | 0 | -0.06 |
| F VIX (research) | 4 | +0.72 | 4 | 0 | +0.08 |
| H US holidays | 3 | -0.48 | 1 | 0 | -0.04 |

## The closest (all fail)
| idea | DEV 2022-24 | years | VAL 2025 | why it fails |
|---|---|---|---|---|
| M100 CME relative-volume leader (NSDQ vs SP NB) | +0.171 R (t 2.91), n 626, info t 3.94 | +0.23 / +0.12 / +0.16 | -0.034 (t -0.37) | DEV t below 3.29; flat in 2025 |
| M044 VPCI H4 (CME4) | +0.156 (t 1.69), n 397 | +0.10 / +0.14 / +0.22 | +0.156 (t 1.02) | t far below the bar; 4 markets |
| M032 Negative Volume Index (CME4, 83% long) | +0.063 (t 1.69) | -0.02 / +0.14 / +0.04 | +0.039 (t 0.68) | mostly long = index / gold drift |
| M016 VWAP trend hold (CME4) | +0.105 (t 1.65) | +0.19 / +0.07 / +0.06 | +0.053 (t 0.51) | t below the bar |
| M037 Ease of Movement H4 (CME4) | +0.133 (t 1.46) | +0.11 / +0.15 / +0.14 | +0.312 (t 2.06) | DEV t 1.46; n 424 |
| M091 realised vol above VIX -> NB follow | +0.089 (t 1.45) | +0.13 / +0.11 / +0.02 | -0.111 | reversed in 2025 |

## What the new information said
- **MT5 broker spread (A):** a spread shock is a news minute; following it (-0.058 R, t -2.2) or fading it (-0.043) both lose. Calm or stressed
  session boxes, thin breaks and deep breaks are no better than the plain box (-0.05 .. -0.14 R). MT5 broker's FX spreads are nearly constant
  (the daily FX-wide spread ratio is exactly 1.0 on most days), so the FX-wide stress / calm states fire on about 40 days, mostly in
  2024 and none in 2026. Spread is a cost on MT5 broker, not a signal.
- **CME volume (B + G):** the least bad group, but its count is what chance gives: 16 of 34 positive, 3 above t 1.65 (about 1.7
  expected). The CME VWAP family (reclaim, 2-sigma break / fade, pullback, yesterday's VWAP) is flat to negative; volume climaxes,
  absorption blocks and signed-volume skew carry nothing; the volume oscillators on H4 (EOM, VPCI) are positive in every DEV year but
  small and on 4 markets only. The best, M100 (take the NB breakout of whichever index has the busier opening half hour), has real
  direction information in 2022-24 (t 3.94 over its mirror) and none in 2025.
- **Cross-market (C):** the strongest-vs-weakest currency pair (-0.133 R), strength-consistent pairs, global index breadth, the
  dollar filter for metals, triangle-consistent crosses and correlation breaks all fail; gold in euros +0.053 (t 0.75).
- **Untested named systems (D, D2, E):** DEV t mean -2.24, as BRK26 / BRK30 found. The busy H1 signals lose the spread: QQE -0.090
  (t -4.1), TSI -0.091 (t -4.3), Laguerre RSI -0.100 (t -5.8), centre of gravity -0.069 (t -4.4), inverse Fisher RSI -0.094 (t -4.4),
  Hurst trend -0.107 (t -4.2), Kalman slope -0.091 (t -3.8), Range Filter -0.078 (t -3.2). H4 Ehlers filters -0.05 .. -0.14 R; Dual
  Thrust -0.042 (t -3.0), R-Breaker trend -0.074, R-Breaker reversal -0.014; Coppock +0.021 (t 0.86) the only one above zero.
- **VIX (F):** all four positive but small and unstable (M089's 2022 mean of +5.2 R is a single trade); the realised-above-implied
  follow reversed in 2025.
- **US holidays (H):** fading FX London boxes on US holidays -0.235 R (thin, wide-spread days: 7-spread stops).

## Account view (2022-25, from 95,472, MT5 broker rules)
M100, M032, M044, M016, M037: 0.0% pass by 22 Dec 2026 and 0.0-0.1% by 30 Jun 2027 at $50 a trade (universe) or $250 (NSDQ +
XAUUSD), breach 0-7%. Nothing is usable.

## Tally
18 Oct: GN1-GN13 40 + BRK50B 50 + BRK30 30 + BRK100 100 + BRK26 26 + BRK100B 100 = **346 pre-registered tests, 0 passes**. The new
information available on the second PC (MT5 broker spread, CME volume, cross-market states, VIX files, holidays) does not change the picture;
what remains untested is information only the main PC holds (MT5 calendar forecasts, MT5 broker tick volume and ticks). Next: BRK100C
(registered 21:59, `PREREG_BRK100C.md`), the trader's "another 100 ideas".
