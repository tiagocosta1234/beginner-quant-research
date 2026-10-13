# LF: reversal after the London 4pm fix (7 USD majors, MT5 broker M1 bid/ask): result (2026-10-11)

Pre-registration `PREREG_LONDON_FIX.md` (commit e20943e), simulator `london_fix.py`, output `LONDON_FIX_OUTPUT.txt`. Hold-out NOT opened.

## Verdict: all three variants negative in DEV and VAL; closed
| variant | DEV trades | per trade bp | daily t DEV | VAL per trade | daily t VAL |
|---|---|---|---|---|---|
| LF1 all days, exit 17:00 | 5,413 | -0.84 | -2.85 | -1.08 | -2.74 |
| LF2 move > 1 sigma, exit 17:00 | 1,550 | -1.65 | -2.37 | -1.96 | -3.01 |
| LF3 move > 1 sigma, exit 19:00 | 1,550 | -0.75 | -0.36 | -3.52 | -3.10 |
All 7 pairs negative (LF1 2022-25: -0.4 to -1.7 bp).
## Reading
On MT5 broker 2022-25 the pre-fix move does not reverse after the window; it continues slightly (gross about +0.7 to +1 bp in the move's
direction, which is about the round-trip cost, so the mirror trade would not pay either). The post-2015 fix reform (5-minute window)
probably removed the effect the papers measured on older data. No EA.
