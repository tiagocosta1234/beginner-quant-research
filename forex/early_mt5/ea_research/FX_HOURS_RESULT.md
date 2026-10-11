# RB: currencies weaken in their own working hours (MT5 broker M1 bid/ask): result (2026-10-11)

Pre-registration `PREREG_FX_HOURS.md` (commit eb0c7cf), simulator `fx_hours.py`, output `FX_HOURS_OUTPUT.txt`. Hold-out NOT opened.

## Verdict: nothing; closed
| variant | DEV bp/day | DEV t | VAL bp/day | VAL t |
|---|---|---|---|---|
| RB1 European hours, short EUR/GBP/CHF vs USD | -0.10 | -0.13 | -1.06 | -0.80 |
| RB2 US hours, long EUR/GBP/CHF vs USD | -0.52 | -0.52 | +0.16 | +0.10 |
| RB3 both windows | -0.58 | -0.48 | -0.93 | -0.46 |
| RB4 Tokyo hours, long USDJPY | +0.71 | +0.60 | -3.29 | -1.96 |
## Reading
The working-hours pattern of the 2000s papers is not in MT5 broker's 2022-25 quotes: every window is within noise of zero after about 0.5-1 bp of cost.
No EA.
