# PRESAMPLE3 result (breakout day round 35, 2026-10-15 14:25, local clock): JPY crosses at the London open do not pass at today's spreads
Pre-registration `PREREG_PRESAMPLE3.md` (before download), engine `presample3.py`, rows `D:/finance/si_ledgers/PRESAMPLE3.parquet`. Identical L1 rule, HistData 2020-01-02 .. 2021-11-30, ask = bid + MT5 broker's CURRENT (Oct 2025 - Oct 2026) median 08:00-17:00 London spread. One look.
| cross | today's MT5 broker spread | trades | mean net R | t | 2020 / 2021 | random |
|---|---|---|---|---|---|---|
| EURJPY | 0.007 | 492 | +0.114 | +1.16 | +0.199 / +0.021 | +0.012 |
| GBPJPY | 0.012 | 493 | +0.079 | +0.83 | +0.031 / +0.132 | +0.086 |
| AUDJPY | 0.007 | 488 | +0.031 | +0.37 | +0.079 / -0.021 | -0.136 |
| NZDJPY | 0.007 | 489 | +0.122 | +1.16 | +0.063 / +0.188 | -0.073 |
| CHFJPY | 0.010 | 493 | +0.003 | +0.03 | +0.000 / +0.006 | -0.172 |
| **J1 the five pooled (daily)** | | 495 days | **+0.069** | **+1.18** | +0.074 / +0.063 | |
J1 FAILS (t 1.18 < 1.96; both years positive). Context at today's spreads: USDJPY +0.204 (t 1.64), CADJPY +0.100 (t 0.94, it was +0.257 at the 2022 spread); all seven yen pairs together +0.092 R a day-trade (daily t 1.66).
Reading: every yen pair is at or above zero at the London open in 2020-21, which fits a small common yen effect, but after today's MT5 broker spreads it is +0.0..+0.2 R a trade and not significant out of time. USDJPY remains the strongest single case (cheapest spread relative to its box).
