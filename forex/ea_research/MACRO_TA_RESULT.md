# M: slow fundamental bias + mechanical 15-minute pullback entries on 28 FX pairs (M1) and SP / NSDQ / DOW (M2): result (2026-10-09 18:50 local, 2026-10-09)

Pre-registration `PREREG_MACRO_TA.md`, simulator `macro_ta.py`, output `MACRO_TA_OUTPUT.txt`, public data in data\data_macro (FRED: policy / short rates of 8 currencies, VIX), ledger family macro_ta (trials 53 and 54, ledger 54). The 2026 hold-out was NOT opened.
## Verdict: BOTH fail acceptance 1 and 2; the fundamentals add no usable information at this horizon
| trial / period | with the bias | against (inverted) | no bias (TA only) |
|---|---|---|---|
| M1 FX DEV 2022-24 | -0.220 R, PF 0.70, t -13.0 (9,065 trades, 1/26 pairs > 0) | -0.218 R, PF 0.71 | -0.182 R, PF 0.75 |
| M1 FX VAL 2025 | -0.209 R, PF 0.72, t -7.4 (3,584) | -0.242 R, PF 0.68 | -0.178 R, PF 0.76 |
| M2 indices DEV | +0.015 R, PF 1.03, t +0.31 (811 trades) | -0.026 R, PF 0.95 | -0.005 R, PF 0.99 |
| M2 indices VAL | -0.072 R, PF 0.87, t -0.58 (240) | -0.137 R, PF 0.76 | -0.101 R, PF 0.82 |
## Reading
- FX: the carry-aligned bias is worth NOTHING at 15 minutes: with-bias (-0.22 R) equals against-bias (-0.22 R) in DEV and is 0.03 R better in VAL (not significant); the technical engine alone loses about 0.18 R a trade because FX spreads (1-3 pips) are 0.1-0.2 R of a 1.5 x ATR14(M15) stop and a 1:2 exit on a random walk wins 33% minus costs (27.7% observed). There is no gross edge to rescue.
- Indices: the VIX regime has the RIGHT SIGN (with-bias beats against-bias in DEV by +0.04 R and in VAL by +0.065 R, acceptance 3 would pass), but the levels are +0.015 R and -0.072 R (PF 1.03 / 0.87, t +0.31 / -0.58): far from acceptance 1 (mean > +0.05, PF >= 1.10, t >= 2.5).
- Honest scope: the fundamentals tested are SLOW state variables (policy rates, VIX) by design (no news trading). They can change the direction of a trade; they cannot change its timing at 15 minutes. Information at this horizon lives in releases and positioning changes (events, excluded) and in microstructure.
