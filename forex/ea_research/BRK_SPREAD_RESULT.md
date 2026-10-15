# BRK-SPREAD result (breakout day round 16, 2026-10-15 12:20): relative-spread breakouts lose (two legs = double the spread)
Pre-registration `PREREG_BRK_SPREAD.md`, engine `brk_spread.py` (truncation PASS; hand check NSDQ/SP 2024-06-03: short spread entered 17:04 server, +0.26 R, box 23 bp), rows `D:\finance\si_ledgers\BRK_SPREAD.parquet`.
| pair (net R) | DEV | VAL | 2026 | random control DEV / VAL / 2026 |
|---|---|---|---|---|
| NSDQ / SP | -0.073 | -0.151 | -0.110 | -0.073 / -0.274 / -0.115 |
| NSDQ / DOW | +0.002 | +0.033 | -0.181 | -0.039 / -0.023 / -0.028 |
| XAUUSD / XAGUSD | -0.389 | -0.365 | -0.203 | -0.516 / -0.330 / +0.081 |
| BRENT / WTI | -0.677 | -0.867 | -0.691 | -0.557 / -0.776 / -0.776 |
| ETHUSD / BTCUSD | -0.787 | -0.196 | -0.628 | -0.869 / -0.276 / -0.623 |
0 of 5 pass. Opening-range breakouts of a relative spread are no better than random entries in it, and paying four spreads per round trip on boxes of 11-48 bp makes them heavily negative (Brent/WTI, ETH/BTC, gold/silver).
