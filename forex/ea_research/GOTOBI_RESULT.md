# GT: USDJPY into / after the Tokyo fix (MT5 broker M1 bid/ask): result (2026-10-11)

Pre-registration `PREREG_GOTOBI.md` (commit 6c7cf33), simulator `gotobi.py`, output `GOTOBI_OUTPUT.txt`. Hold-out NOT opened.

## Verdict: no variant passes; closed
| variant | DEV trades | DEV mean bp | DEV t | VAL mean bp | VAL t |
|---|---|---|---|---|---|
| GT1 long 08:00-09:54 JST, every weekday | 777 | +0.57 | +0.95 | -0.91 | -0.81 |
| GT2 same, gotobi days | 214 | +1.23 | +1.00 | -0.76 | -0.44 |
| GT3 short 09:56-11:00 JST, gotobi days | 214 | +1.42 | +1.44 | +0.84 | +0.56 |

## Reading
The documented sign shows up (rise into the fix, fall after it on gotobi days) but at 1-1.5 bp per trade with t about 1, and GT1/GT2 turn
negative in 2025. Even if real, 1 bp on about 6 trades a month adds nothing to the pass speed. No EA.
