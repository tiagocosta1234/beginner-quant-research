# PRESAMPLE2 result (breakout day round 34, 2026-10-15 14:23, local clock): the other four markets do NOT confirm; CADJPY comes close
Pre-registration `PREREG_PRESAMPLE2.md` (before download), engine `presample2.py` (the identical L1 rule), rows `data/si_ledgers/PRESAMPLE2.parquet`. HistData 1-minute bid 2020-01-02 .. 2021-11-30, ask = bid + MT5 broker's 2022 median session spread. One look.
| cell | trades | mean net R | t | 2020 / 2021 | random | verdict |
|---|---|---|---|---|---|---|
| P1 GBPUSD | 495 | +0.037 | +0.41 | +0.095 / -0.026 | +0.140 | FAIL |
| P2 EURUSD | 492 | +0.040 | +0.46 | +0.007 / +0.076 | +0.011 | FAIL |
| P3 CADJPY | 492 | **+0.257** | **+2.09** | +0.368 / +0.134 | +0.008 | FAIL (t below the 2.33 Bonferroni bar) |
| P4 USDCHF | 493 | -0.034 | -0.35 | +0.103 / -0.184 | -0.026 | FAIL |
| P5 the four pooled (daily) | 495 days | +0.072 | +1.31 | +0.141 / -0.003 | | FAIL |
Context: the five-pair book with USDJPY +0.110 R a day-trade (daily t 1.99); daily correlations are low (USDJPY-CADJPY +0.26, EURUSD-USDCHF +0.41, others -0.02..+0.24).
Reading: the London-open breakout does not hold out of time on the dollar majors (GBPUSD, EURUSD, USDCHF about zero). What survives is the YEN side: USDJPY passed (+0.260, t 2.07) and CADJPY nearly did (+0.257, t 2.09). A "JPY at the London open" hypothesis is post hoc and would need its own pre-registered test (other JPY crosses, other years).

**Cost check (both PRESAMPLE rounds, diagnostic):** MT5 broker's USDJPY spread in 08:00-17:00 London was about 0.1 pip in 2021-23 (0.001) and 0.6-0.7 pip since 2024 (0.0065-0.0069 mean). The pre-registered tests used the 2022 spread. At today's spread the 2020-21 USDJPY result is +0.204 R (t 1.64) at 0.006 and +0.199 (t 1.61) at 0.0074 (both years still positive); at 0.010 it is +0.133 (t 1.10). The MT5 broker years 2024-26 already carry today's spreads and stay positive (+0.185 / +0.108 / +0.114). So the USDJPY edge after today's costs is about +0.1..+0.2 R a trade, and the out-of-time evidence at today's costs is suggestive (t 1.6), not significant.
