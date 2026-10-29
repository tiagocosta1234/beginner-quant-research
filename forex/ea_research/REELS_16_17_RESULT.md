# REELS_16_17 result - the reels' patterns partly replicate, the edges do not (0 of 4 pass)

Run 2026-10-17 23:42 local (local clock, second PC). Pre-registration `PREREG_REELS_16_17.md` (registered ~23:41; its header first said 23:45, a guess,
corrected after the run; frozen by sha256 at 23:42:32 in
`data\scratch\reels_16_17_freeze.txt`). Engine `reels_16_17.py`, output `REELS_16_17_OUTPUT.txt`. MT5 broker NSDQ M1 bid/ask
2022-01..2026-10-16 (zero-spread minutes repaired); HOLD 2026 sealed (no trial passed DEV). Reel 15 (Zenith) has no rules and
is not testable (`reels/15_zenith_nq_prop_81pct_no_rules/NOTAS.md`).

## Verdict (NSDQ, net R a trade)
| trial | DEV 2022-24: n, R (t), win, PF | DEV years | VAL 2025: n, R (t), win, PF |
|---|---|---|---|
| R16-T1 buy the 5-min close outside the box | 728, +0.067 (2.09), 55%, 1.18 | +0.09 / +0.07 / +0.04 | 236, +0.024 (0.44), 53%, 1.06 |
| R16-T2 wait for the retest of the edge | 632, +0.060 (1.77), 50%, 1.17 | +0.10 / +0.05 / +0.03 | 205, +0.019 (0.32), 48%, 1.05 |
| R17-EMA first 5-min candle vs EMA12, EMA trail | 773, +0.078 (1.09), 30%, 1.17 | +0.15 / +0.01 / +0.08 | 257, -0.018 (-0.22), 30%, 0.96 |
| R17-SWING same signal, 3-candle trail | 773, +0.076 (1.07), 33%, 1.14 | +0.12 / +0.02 / +0.09 | 257, -0.085 (-0.98), 30%, 0.84 |
None reaches the pre-registered t >= 2.5 in DEV; all fade toward zero or below in 2025.

## Reel 16's claims, checked (NSDQ 2022-25, points at one contract)
| the reel says | here |
|---|---|
| trader 1 ($3,760) makes about twice trader 2 ($1,780) | T1 +5,099 pts, T2 +4,466 pts: T1 ahead, by less |
| trader 2 sits out more than half of the days | 13% (127 of 964): our limit stays live until 16:00 NY; the reel's likely expired sooner (not stated) |
| on the days both trade, the retest wins (~2x) | yes, and more: T1 -8,108 pts (-0.068 R a trade) vs T2 +4,466 (+0.050 R) |
| the no-retest days carry trader 1 ($2,840, 3x the retest days) | yes: +13,207 pts on 127 days (+0.875 R a trade) |
The reel's STRUCTURE replicates (the retest gives a better price, the runaway days it misses are where the breakout's money is),
but neither trader has a reliable edge after MT5 broker costs: +0.02..+0.07 R a trade, below the bar and near zero in 2025. Same reading
as BRK_CONFIRM / BRK_RETEST.

## Reel 17's claims, checked (NSDQ 2022-25)
| the reel says (NAS100 M5, 2019-26) | here (2022-25) |
|---|---|
| 1,448 trades, 57% win rate, profit factor 1.29 | 1,030 trades, win 30-33%, PF 1.07-1.12, +0.04..+0.05 R a trade |
| +982% total return, max drawdown 19.7% | not comparable (compounding and risk per trade not shown); 2022 is the only strong year |
The trail is not shown exactly (two readings tested); neither gets near a 57% win rate (the opening-candle stop is ~37 points,
and a trailing stop exits most trades early). "After hundreds of backtests we finally found one" is a best-of-hundreds pick.

## Descriptive: same rules on SP and DOW (2022-25, R / win / PF)
SP: R16-T1 +0.015 / 51% / 1.04, R16-T2 -0.008 / 45% / 0.98, R17-EMA -0.076 / 25% / 0.84, R17-SWING -0.102 / 29% / 0.82.
DOW: R16-T1 +0.024 / 52% / 1.06, R16-T2 +0.012 / 47% / 1.03, R17-EMA -0.047 / 27% / 0.90, R17-SWING -0.070 / 31% / 0.87.
Weaker on the other US indices than on NSDQ: the NSDQ numbers are not a general index effect.

## In the account's environment (NSDQ, $250 a trade, 2022-25 trades, from 95,472, MT5 broker rules; pass% / breach%)
| trial | trades, R | 22 Dec | 31 Mar 2027 | 30 Jun 2027 |
|---|---|---|---|---|
| R16-T1 | 964, +0.056 | 0.0 / 0 | 0.0 / 2 | 0.0 / 4 |
| R16-T2 | 837, +0.050 | 0.0 / 0 | 0.0 / 3 | 0.0 / 5 |
| R17-EMA | 1,030, +0.054 | 0.0 / 12 | 0.2 / 35 | 1.2 / 45 |
| R17-SWING | 1,030, +0.036 | 0.0 / 17 | 0.3 / 41 | 1.5 / 51 |
The reel-16 rules are too small to pass (about 240 trades a year x 0.056 R x $250 = ~$3,400 a year against $12,528 needed) and
too small to breach; reel 17's wide intraday swings breach 30-40 times more often than they pass.
