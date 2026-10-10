# I1: first-30-minute move predicts the last 30 minutes on NSDQ / SP / DOW (MT5 broker M1 bars): result (2026-10-09 16:04 local, 2026-10-09)

Pre-registration `PREREG_INDEX_INTRADAY_MOM.md`, simulator `index_intraday_mom.py`, output `INDEX_INTRADAY_MOM_OUTPUT.txt`, ledger family index_intraday_mom (ledger 49 of 51). The 2026 hold-out was NOT opened.
## Verdict: FAILS acceptance 1 and 2; no edge, not even before costs; idea closed
| period | trades | net bp/trade | mid-to-mid gross | PF | daily t | per index (net bp) |
|---|---|---|---|---|---|---|
| DEV 2022-24 | 2,229 | -1.90 | -0.95 | 0.82 | -2.08 | DOW -2.13, NSDQ -2.10, SP -1.46 |
| VAL 2025 | 735 | -1.31 | -0.29 | 0.86 | -0.88 | DOW -1.78, NSDQ -1.29, SP -0.87 |
| 2022-25 pooled | 2,964 | -1.75 | -0.79 | 0.83 | -2.25 | all three negative |
## Reading
The documented effect (first half hour predicts the last half hour) does not show up in MT5 broker's CFD prices for 2022-2025: the mid-to-mid gross is slightly NEGATIVE in both periods and on all three indices (the sign is the opposite of the literature, small and not significant), so costs (about 1 bp round trip) only make it worse. Nothing to port or size.
