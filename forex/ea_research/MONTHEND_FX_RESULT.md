# MONTHEND_FX_RESULT - month-end FX rebalancing into the London 16:00 fix (2026-10-15, local clock 15:19)
Pre-registration `PREREG_MONTHEND_FX.md` (commit 77b8c511; Amendment 1 before any P&L: M2's signal measured at its own entry time). Code `monthend_fx.py`. Rows `D:/finance/si_ledgers/MONTHEND_RUN.csv`.

## Verdict: 0 of 4 cells; closed. The Melvin-Prins month-end hedge flow is not in MT5 broker prices 2020-25.
| cell | OOT 2020-21 | DEV 2022-24 | VAL 2025 | DEV+VAL t (bar 2.40) |
|---|---|---|---|---|
| M1 basket, London 14:00 -> 16:00 fix, 7 USD pairs | -7.98 bp (t -1.84) | +0.77 | +1.03 | +0.31 |
| M2 basket, London 08:00 -> fix | -6.14 | -2.81 | +2.91 | -0.34 |
| M3 pair-specific (EURUSD/DAX, USDJPY/Nikkei, AUDUSD/ASX), 14:00 -> fix | -9.55 (t -2.20) | +2.48 | -0.63 | +0.82 |
| M4 post-fix reversal 16:00 -> 18:00 | +0.45 | +0.98 | -3.13 | -0.02 |
Monthly-cluster means in bp of price, net of MT5 broker's spread (the spread costs only 0.1-0.7 bp a trade here: the result is not a cost problem, the gross is about zero). The business-day-10 controls are as large as the month-end cells (e.g. M2 control DEV +12.5 bp, t 1.83): what is left is noise. The out-of-time years 2020-21 point the WRONG way for M1/M3 (USD bought into the fix after US outperformance), consistent with the flow having been arbitraged away after the 2013-15 fix scandal, the 2015 widening of the fix window to 5 minutes, and publication. HOLD 2026 not opened.
