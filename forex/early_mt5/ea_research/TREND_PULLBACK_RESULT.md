# Trend-pullback rule H1 on five MT5 broker: result (2026-10-09 ~10:55 local, local clock)

Pre-registration `PREREG_TREND_PULLBACK.md` (10:35, before any run), simulator `trend_pullback.py`, full output `TREND_PULLBACK_OUTPUT.txt`, ledger family `trend_pullback` (38 of 40 registered trials). Hold-out 2026 NOT opened.

## Verdict: H1 fails acceptance 1 and 2; the effect is neither strong on gold nor general
| market | DEV 2022-24: trades / mean bp / PF / daily t | VAL 2025: trades / mean bp / PF / daily t | pooled 2022-25: mean bp / PF / t |
|---|---|---|---|
| GOLD (primary) | 993 / +0.7 / 1.03 / +0.32 | 324 / +6.8 / 1.22 / +1.37 | +2.1 / 1.08 / +1.09 |
| NSDQ | 1,003 / -0.4 / 0.99 / -0.13 | 344 / -4.9 / 0.86 / -1.06 | -1.6 / 0.96 / -0.56 |
| SP | 1,020 / -2.4 / 0.92 / -0.95 | 342 / -2.1 / 0.92 / -0.52 | -2.3 / 0.92 / -1.08 |
| BTC | 1,266 / -4.6 / 0.94 / -0.74 | 517 / -17.2 / 0.75 / -2.39 | -8.2 / 0.89 / -1.70 |
| ETH | 1,651 / -47.9 / 0.56 / -7.23 | 516 / -29.7 / 0.75 / -2.22 | -43.4 / 0.61 / -7.27 |
Registered bars: gold DEV PF >= 1.10 and t >= 2.0 (got 1.03 and +0.32); replication positive on >= 3 of 4 other markets (got 0 of 4, all four negative pooled).
## Reading
A plain rule built from the three facts of the 5-minute EA's profile (trade with the 4-hour move and the 24-hour average, enter on a counter-bar of 0.5 ATR, 2 ATR stop, 3 ATR chandelier, 24-hour limit) earns almost nothing on gold (PF 1.08 pooled, positive only in 2025) and loses on every other trending market. The 5-minute EA's own edge is therefore not "buy the dip in a trend" in general: it is something about gold, or about details of that EA (multi-position stacking, its exit) that a plain rule does not capture. No second leg and no new EA from this family.
