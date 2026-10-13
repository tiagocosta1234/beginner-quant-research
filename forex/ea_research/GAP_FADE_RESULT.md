# GF: opening-gap fade on SP / NSDQ / DOW (MT5 broker M1 bid/ask): result (2026-10-11)

Pre-registration `PREREG_GAP_FADE.md` (commit e500651), simulator `gap_fade.py`, output `GAP_FADE_OUTPUT.txt`. Hold-out NOT opened.

## Verdict: no variant passes; closed
| variant | DEV trades / days | per trade | daily t DEV | VAL per trade | VAL t |
|---|---|---|---|---|---|
| GF1 medium gaps (0.5-2 sigma), exit 15:55 | 1,050 / 477 | -5.24 bp (win 58%) | -1.58 | +1.52 | +0.77 |
| GF2 large gaps (> 2 sigma) | 112 / 56 | -4.81 bp | +0.08 | +21.96 | +0.73 |
| GF3 medium gaps, exit 11:00 | 1,050 / 477 | -4.57 bp | -1.82 | -2.61 | +0.01 |
## Reading
Gaps fill often (win 58%) but the days they do not fill lose more: the fade is negative in DEV (2022 worst). Nothing to port.
(Index CFDs trade almost 24 h, so the "gap" is the overnight move into the cash open, the same object as an SPY gap.)
