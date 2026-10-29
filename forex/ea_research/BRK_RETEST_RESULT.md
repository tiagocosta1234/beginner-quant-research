# BRK-RETEST result (breakout day round 2, 2026-10-15 11:42): retests and failed breakouts are worse than the plain stop order
Pre-registration `PREREG_BRK_RETEST.md`, engine `brk_retest.py` (one fix after the first dry-run, before any P&L: stops of zero distance (bid = ask) are skipped; a speed fix computed the mid closes once), rows `data\si_ledgers\BRK_RETEST.parquet`. Truncation PASS; hand check NSDQ 2024-06-12: R1 retest-limit long filled 17:44 server, R2 confirmed long 17:50, both stopped (-1 R).

| cell (net R per trade) | DEV | VAL | 2026 | random control DEV / VAL | indices DEV / VAL / 2026 |
|---|---|---|---|---|---|
| R1 retest limit, hold to close | -0.076 (t -3.8) | -0.185 | -0.094 | -0.132 / -0.165 | +0.057 / -0.009 / -0.046 |
| R1 retest limit, target 2R | -0.111 | -0.151 | -0.112 | -0.132 / -0.157 | -0.016 / -0.050 / -0.020 |
| R2 retest + M5 close back beyond, hold | -0.101 | -0.170 | -0.116 | -0.124 / -0.160 | +0.044 / -0.106 / -0.042 |
| R2 ..., target 2R | -0.137 | -0.153 | -0.114 | -0.136 / -0.161 | -0.023 / -0.070 / -0.006 |
| R3 failed breakout reversal, hold | -0.091 | -0.105 | -0.101 | -0.113 / -0.122 | -0.008 / -0.123 / -0.042 |
| R3 ..., target 2R | -0.093 | -0.107 | -0.107 | -0.101 / -0.129 | -0.009 / -0.128 / -0.056 |
0 of 6 pass; every cell negative in every period. Round 1's stop order with the same hold-to-close exit was -0.032 / -0.076 / -0.037.

What it teaches: waiting for the retest selects the WEAKER breakouts (strong ones never come back to the level), and the tighter stop (box middle or the retest low) raises the cost share, so the retest entry is worse than the stop order by 0.04-0.11 R. A failed breakout (close back through the box middle) does not reverse reliably either: R3 is no better than random entries with the same stop.
