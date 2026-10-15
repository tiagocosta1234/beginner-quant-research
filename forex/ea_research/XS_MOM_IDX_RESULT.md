# XS_MOM_IDX_RESULT - cross-country index momentum, market-neutral (2026-10-15, local clock 15:43)
Pre-registration `PREREG_XS_MOM_IDX.md` (commit ba97ec00). Code `xs_mom_idx.py`, output `XS_MOM_IDX_OUTPUT.txt`, rows `D:/finance/si_ledgers/XS_MOM_IDX_RUN.csv`. HOLD not opened.

## Verdict: 0 of 2; closed
| cell | OOT (MT5 broker D1) | DEV 2022-24 | VAL 2025 | DEV+VAL t (bar 1.96) |
|---|---|---|---|---|
| C1 12-1 month, long top 2 / short bottom 2 of six indices | +10.5 / day (from 2021, Sharpe 0.55) | -10.1 (Sharpe -0.47) | -16.7 (-0.92) | -1.16 |
| C2 3 months | +1.6 (Sharpe 0.07) | -13.1 (-0.63) | -2.4 (-0.13) | -1.03 |
USD a day per 100k gross, net of MT5 broker's spread. Daily correlation with D2 +0.13..+0.16. Country leadership among the six MT5 broker indices reversed more often than it persisted in 2022-25 (Nikkei / DAX / Nasdaq leadership changes); with three US indices out of six the cross-section is too thin to diversify. No market-neutral leg here.
