# CX: weekly cross-sectional crypto momentum / reversal (8 MT5 broker coins): result (2026-10-11)

Pre-registration `PREREG_CRYPTO_XS.md` (commit ee58bdc), simulator `crypto_xs.py`, output `CRYPTO_XS_OUTPUT.txt`. Hold-out NOT opened.
**Bug fixed before the valid run:** the first run computed a short's return as entry/exit - 1 instead of 1 - exit/entry. With crypto's
weekly swings that adds about var(r) (hundreds of bp) to every short, which made BOTH momentum and its mirror look positive gross. Void.

## Verdict (valid run): no variant passes; closed
| variant | DEV net bp/week | DEV gross | DEV t | VAL net | VAL gross |
|---|---|---|---|---|---|
| CX1 1-week momentum | -71.4 | +10.3 | -2.01 | -15.7 | +6.8 |
| CX2 1-week reversal | -91.4 | -10.3 | -2.49 | -29.3 | -6.8 |
| CX3 4-week momentum | -77.0 | +8.5 | -2.42 | -6.0 | +18.2 |
Gross is about zero (t 0.1-0.5); MT5 broker's crypto spreads (about 80 bp a week for 4 legs) make every version lose. No EA.

## Audit of the same short formula in earlier families (no conclusion changes)
entry/exit - 1 for shorts also appears in: crypto_weekend W2/W3 (weekend crypto, bias about +16 bp per short; W2/W3 were rejected anyway),
cot (weekly, bias about +1-3 bp per short; COT never passed), london_fix, gotobi GT3, event_macro V2, noise_area (intraday FX / index:
bias below 0.3 bp). All of these families are closed; the bias only flattered them, so no rejection is overturned. The combined-book
streams COT_P1 and W1 (long only) were already withdrawn with the clip erratum. New code uses 1 - exit/entry.
