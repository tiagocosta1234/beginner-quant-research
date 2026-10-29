# BRK-PYRAMID result (breakout day round 29, 2026-10-15 13:55, local clock): adding to winning breakouts makes them worse
Pre-registration PREREG_BRK_PYRAMID.md, engine brk_pyramid.py (truncation PASS), rows data/si_ledgers/BRK_PYRAMID.parquet. 54,006 session breakouts on 46 markets; 45% reach +1R before the stop (25.7% one add, 19.7% two adds).
| cell (net R per trade, in first-R units) | DEV | VAL | 2026 | random entries, same rules DEV / VAL / 2026 |
|---|---|---|---|---|
| P0 one unit, hold to the close | -0.032 (t -3.5) | -0.076 | -0.037 | -0.074 / -0.102 / -0.128 |
| P1 add one unit at +1R, stop to breakeven | -0.054 (t -3.8) | -0.115 | -0.105 | -0.113 / -0.165 / -0.174 |
| P2 add at +1R and +2R, stop trails 1R behind | -0.062 (t -3.0) | -0.125 | -0.148 | -0.136 / -0.192 / -0.164 |
0 of 2 pass. Pyramiding raises the 95th percentile (+3.5R -> +4.9R) but lowers the mean by 0.02-0.11 R: moves that reach +1R reverse to the raised stop more often than they run, and every add pays the spread again. Breakouts beat random entries by about the same margin with or without adds (+0.04..+0.07 R), so the adds carry no extra information.
By class (P1, DEV / VAL / 2026): index +0.063 / +0.060 / -0.058 (P0 +0.049 / +0.057 / -0.038), FX -0.044 / -0.136 / -0.075, metals -0.133 / -0.190 / +0.106, energy and crypto worse.
Single markets, post hoc: NSDQ P0 +0.141 / +0.077 / -0.088, P2 +0.216 / +0.081 / -0.147; XAUUSD P0 -0.036 / +0.040 / +0.273; USDJPY P0 +0.146 / +0.108 / +0.114 and P2 +0.172 / +0.230 / +0.191 (again the most consistent market of the day, t below 2).
Reading for the trader: adding lots on a breakout that is already in profit does not create a better system on MT5 broker; it turns a small loss into a bigger one, except on the one or two markets where the plain breakout already looked positive.
