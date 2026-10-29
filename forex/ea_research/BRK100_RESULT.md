# BRK100 result - 100 more untested breakout tests on 46 MT5 broker: 0 pass

Run 2026-10-18 evening (local clock, second PC PC-2). Pre-registration `PREREG_BRK100.md` (registered 18:45; SHA-256
9246a54c207b6c28914f9ba1b0971e5244d7b7f5662d06cb06a24ea719078de5 in `data\scratch\brk100_prereg.sha256` before any P&L; no commits
on 18 Oct at the trader's request), engine `brk100.py`, dry run `BRK100_DRYRUN.txt` (truncation identical on EURUSD, XAUUSD, NSDQ,
BTCUSD), output `BRK100_OUTPUT.txt`, table `BRK100_SUMMARY.csv`, 100 ledger rows. 647,585 trades, 2022-01 .. 2026-10.
The 100 = 79 new concepts (L001-L079) + 21 out-of-sample market extensions of today's NSDQ / XAUUSD-only ideas (L080-L100).
Bars: DEV 2022-24 n >= 100, mean > 0 with t >= 3.29 (Bonferroni for 100), >= 2 of 3 years positive, information over the mirror
t >= 2.0; VAL 2025 t >= 1.65; the 2026 hold-out only for passers.

## Verdict: 0 of 100; hold-out sealed
- DEV t-values: mean **-3.16**, SD 4.91; 19 of 100 positive; 2 above t 1.65 (5 expected by luck); none near 3.29.
- By group (mean net R a trade in 2022-24; best t; positive ideas): crypto -0.45 R (best t -2.7, 0 of 12: MT5 broker crypto spreads leave
  boxes of 2-10 spreads); FX -0.06 (best 1.84, 5 of 17); indices +0.02 (best 1.82, 8 of 13); commodities -0.14 (0.53, 1 of 10);
  structure -0.07 (0 of 6); named systems -0.07 (0 of 15: pivot reversal -0.11, consecutive bars -0.10, momentum stops -0.12,
  Renko -0.10, Ross hook -0.13, Hikkake -0.19, ACD -0.05, smash day -0.01, 80-20 -0.07); information / events -0.08 (2 of 6);
  market extensions -0.05 (3 of 21).

## The few positives (all fail)
| test | DEV 2022-24 | years | VAL 2025 | reading |
|---|---|---|---|---|
| L025 carry side (JPY crosses long-only, London box) | +0.112 R (t 1.84), n 2,880 | +0.07 / +0.03 / +0.22 | +0.030 | the yen-carry drift of 2022-24, not breakout information |
| L035 VIX backwardation -> US index NY box | +0.575 (t 1.82), n 49 | (2 years) | -0.335 | below n 100; reversed in 2025 |
| L017 FOMC post-statement box on the USD majors | +0.315 (t 1.11), n 127 | -0.12 / +0.45 / +0.54 | **+1.113 (t 2.67)** | about 6 FOMC days a year traded on 7 correlated pairs: a handful of independent events; no DEV evidence |
| L023 China-morning box (AUD / NZD) | +0.046 (t 1.11), n 2,673 | +0.06 / +0.16 / -0.09 | -0.027 | information t 2.07, net about zero |
| L082 J36 (Nikkei direction) on SP / DOW | +0.066 (t 1.09), n 815 | +0.09 / +0.02 / +0.09 | -0.016 | the J36 Nasdaq shape travels weakly, not tradeably |

## What the out-of-sample extensions say about today's leads
Today's best NSDQ / XAUUSD ideas do not carry over to the other markets: J01 (PDH / PDL held through Europe, broken in New York) on
the 36 other markets -0.024 R (t -1.6); the Holy Grail -0.200 (t -7.4); H1 inside bars -0.110; own-London-direction NY box -0.150;
the bond-trend filter on DOW / DAX / NIKKEI / ASX 0.000. The Nasdaq near-misses were Nasdaq's 2022-25 drift, not mechanisms.

## Account view (2022-25 trades, from 95,472, MT5 broker rules)
None of the five best passes at any date; L025 at $50 a trade on its universe: 1.2% pass / 12% breach by 30 Jun 2027.

## Reading
Fixings, option cuts, exchange opens, release days, auctions, cross-asset leads for FX, crypto sessions and the classic named
systems (Williams, Raschke, Fisher, Dalton, Ross, Hikkake, Renko, Point and Figure, TradingView's built-ins) all land at or below
minus the spread on MT5 broker prices. This is the fourth batch today (after BRK50B 50 and BRK30 30) and the most negative.
