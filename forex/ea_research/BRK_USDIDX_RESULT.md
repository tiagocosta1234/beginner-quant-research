# BRK-USDIDX result (breakout day round 23, 2026-10-15 12:52): a USD-index breakout is not a better signal than the pair's own breakout
Pre-registration `PREREG_BRK_USDIDX.md`, engine `brk_usdidx.py`, rows `data\si_ledgers\BRK_USDIDX.parquet`.
| cell (net R, hold to 17:00 London) | DEV | VAL | 2026 | random control | the pair's own session breakout (round 1) |
|---|---|---|---|---|---|
| X1 EURUSD in the USD index's breakout direction | +0.027 (t 0.26) | -0.038 | -0.109 | +0.085 / -0.095 / -0.268 | +0.075 / +0.067 / +0.004 |
| X2 USDJPY in the USD index's breakout direction | +0.110 (t 1.07) | +0.231 | +0.058 | -0.002 / +0.174 / -0.023 | +0.146 / +0.108 / +0.114 |
0 of 2 pass; the index signal is no better (EURUSD worse) than the pair's own box.

Descriptive follow-up (not a cell): markets whose round-1 session breakout (hold to close) is positive in DEV, VAL and 2026: 5 of 46 (USDJPY +0.146 / +0.108 / +0.114, GBPUSD +0.090 / +0.121 / +0.027, EURUSD +0.075 / +0.067 / +0.004, CADJPY, USDCHF), against 1.8 expected if the periods were independent coin flips with today's base rates (weak excess). The seven USD majors as a pre-definable group: +0.029 / -0.041 / -0.024 (no group effect); other FX crosses -0.055 / -0.099 / -0.036. USDJPY remains the single most consistent breakout market of the day (all breakout types in BRK and here), with t below 2 in every period.
