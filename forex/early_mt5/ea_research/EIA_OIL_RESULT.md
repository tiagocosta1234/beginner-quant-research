# OE: WTI around the EIA inventory report (MT5 broker M1 bid/ask): result (2026-10-11)

Pre-registration `PREREG_EIA_OIL.md`, simulator `eia_oil.py`, output `EIA_OIL_OUTPUT.txt`. Hold-out NOT opened. 212 release weeks with all minutes quoted.

## Verdict: no variant passes; closed
| variant | DEV events | DEV mean | DEV t | VAL mean | VAL t |
|---|---|---|---|---|---|
| OE1 momentum after the first 15 min | 82 | -8.9 bp | -0.61 | -39.4 bp | -2.06 |
| OE2 reversal of the first 15 min | 82 | -2.1 bp | -0.14 | +27.8 bp | +1.45 |
| OE3 long 09:00 -> release | 155 | -14.9 bp | -2.05 | -13.6 bp | -1.70 |
## Reading
No usable reaction pattern. OE3 is negative in every year 2022-25 (oil tends to slip into the number), which hints at the mirror (short
09:00 -> release), but that is a new hypothesis, about 15 bp gross against about 5 bp of cost per trip on one event a week: even if real it
would add a few USD a week at MT5 broker's sizes. Noted as a lead only.
