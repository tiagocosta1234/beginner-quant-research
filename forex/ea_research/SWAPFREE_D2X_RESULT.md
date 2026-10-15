# SWAPFREE_D2X_RESULT - a wider swap-free book does not beat D2 (2026-10-15, local clock 15:26)
Pre-registration `PREREG_SWAPFREE_D2X.md` (commit f766225f). Code `swapfree_d2x.py`, output `D2X_OUTPUT.txt`, rows `D:/finance/si_ledgers/D2X_RUN.csv`. HOLD not opened (no variant passed).

## Verdict: 0 of 3; D2 stays the candidate
| variant | OOT 2020-21 (MT5 broker D1) | DEV 2022-24 | VAL 2025 | DEV+VAL t (bar 2.13) | Sharpe DEV / VAL (must beat REF) |
|---|---|---|---|---|---|
| REF_D2 (same setup, not a trial) | +37.6 (Sharpe 1.02) | +29.1 | +81.8 | 2.47 | 0.91 / 1.98 |
| X1 + BTC, ETH | +83.9 (1.83) | +33.5 | +72.8 | 2.35 | 0.94 / **1.70 (lower)** |
| X2 + silver, DOW, ASX | +43.4 (1.18) | +14.5 | +81.3 | **1.99** | 0.47 / 2.32 |
| X3 all ten | +74.1 (1.81) | +18.7 | +75.2 | **2.02** | 0.59 / 2.08 |
USD a day per 100k gross, net of MT5 broker's spread.
- Crypto helped in the 2020-21 boom (BTC +11.6k, ETH +13.8k per 100k in OOT) and 2022-24 (BTC +6.0k), nothing in 2025 (+0.5k), with a worse worst day (-5.9k). Silver and ASX lost in 2022-24. More correlated markets did not add diversification.
- Side result: D2 itself, re-run with a second out-of-time source (MT5 broker D1 bars instead of HistData M1, DAX included), is positive again in 2020-21 (+37.6 a day, Sharpe 1.02, t 1.44 on about 14 months of trading).
