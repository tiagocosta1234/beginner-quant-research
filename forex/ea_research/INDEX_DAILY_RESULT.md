# One-trade-a-day rules on MT5 broker's US index CFDs: result (2026-10-09 ~09:04 local)

Pre-registration `PREREG_INDEX_DAILY.md`, simulator `index_daily.py`, trial ledger `LEDGER.csv`. Data: MT5 broker's own M1 bars, `NSDQ+` primary. The 2026 hold-out and the registered replication were NOT opened (neither primary passed DEV and VAL).

## Verdict: neither primary passes; round closed
| trial | DEV 2022-24 mean bp / trade | PF | daily t | VAL 2025 mean bp | PF | daily t |
|---|---|---|---|---|---|---|
| A1 PRIMARY overnight long 16:30 -> 09:30 NY | +1.35 (747 trades) | 1.05 | +0.41 | +4.84 (247) | 1.18 | +0.81 |
| A2 no Friday entries | +2.61 | 1.09 | +0.73 | +1.22 | 1.05 | +0.14 |
| A3 stop -1.0% | +0.71 | 1.02 | +0.87 | +5.12 | 1.19 | +1.98 |
| B1 PRIMARY opening-range breakout 30 min, stop opposite side, 1.5R | +4.54 (736) | 1.15 | +1.58 | +2.58 (246) | 1.10 | +0.53 |
| B2 target 1.0R | +4.08 | 1.15 | +1.58 | +2.13 | 1.09 | +0.52 |
| B3 15-minute range | +0.73 | 1.02 | +0.27 | +5.93 | 1.26 | +1.43 |
| B4 stop at mid-range | +0.07 | 1.00 | +0.04 | -0.10 | 1.00 | -0.03 |
| B5 longs only | +4.22 | 1.15 | +1.27 | +4.69 | 1.23 | +0.82 |
Registered bars: DEV daily t >= 2.24 (two primaries) and PF >= 1.10; VAL t >= 1.0 and PF >= 1.05. A1 misses DEV (t 0.41, PF 1.05) and VAL (t 0.81); B1 meets the DEV profit factor (1.15) but not DEV t (1.58) and not VAL t (0.53). Every variant except B4 is positive in both periods, none is significant.

## Post-hoc diagnostic (not a registered trial, not used for any decision; ledger rows DIAG-*)
Same rules, 2022-2025 pooled: B1 NSDQ +4.05 bp / trade (t +1.64), SP +1.91 (t +1.07), DOW +0.74 (t +0.45); A1 NSDQ +2.22 (t +0.79), SP +1.11 (t +0.51), DOW -0.75 (t -0.43). The round-trip cost model is about 1.9 points = 1.1 bp on `NSDQ+`, so the opening-range rule keeps about 4 of roughly 5 gross bp a trade. A consistent small positive tilt, never significant; the three indices are highly correlated, so they are not three independent confirmations.

## Reading
Both ideas have the right sign and survive costs now that they trade once a day (the previous round's 1.9 trades a night did not), but a daily t of 0.4-1.6 over four years cannot be told from zero, and an edge that small adds almost nothing to the pass speed of the gold pair. Not accepted, no EA, no hold-out. A third round on these markets would need a new, independent reason to expect an edge, registered before any run.
