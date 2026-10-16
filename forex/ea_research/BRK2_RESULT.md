# BRK2 result - Asian-range breakout and relative box tick-volume filter: 0 of 4 pass

Run 2026-10-16 ~16:20 local, pre-registration `PREREG_BRK2.md` (commit 7bd9596f), script `brk2.py`, output `BRK2_OUTPUT.txt`.
38 non-crypto MT5 broker, 1:1 breakout (SL other side, TP 1 box), real bid/ask, t clustered by day. HOLD not opened.

| Trial | DEV 2022-24 net (t) | gross | VAL 2025 net | Verdict |
|---|---|---|---|---|
| A  Asian range 01-07 local | -0.035 (-3.5), n 26,677 | +0.001 | -0.025 | FAIL |
| A_RV  Asian, box volume >= 1.5x | -0.079 (-2.9), n 2,426 | -0.053 | -0.044 | FAIL |
| L_RV  London 30m, volume >= 1.5x | -0.075 (-2.4), n 2,805 | -0.022 | +0.010 | FAIL |
| N_RV  NY 30m, volume >= 1.5x | -0.011 (-0.4), n 2,719 | +0.045 | -0.060 | FAIL |
| yardstick London 30m | -0.049 (-4.7) | +0.023 | -0.076 | - |
| yardstick NY 30m | -0.035 (-3.4) | +0.023 | -0.040 | - |

Reading: the Asian range has no gross edge at all (+0.001R); high-volume boxes are worse than ordinary ones in DEV
(breakouts after an already busy box fail more often). Every session breakout loses 0.03-0.05R per trade after the
real MT5 broker spread. Opening-range breakouts (London, NY, Asia; filters for volatility, news, trend, volume; 46 markets) are
closed for this account. Window: about 22 of 40 variants.
