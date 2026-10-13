# FXS result: intraday session scan over the 28 MT5 broker FX pairs (2026-10-12)

Pre-registration: PREREG_FX_SESSIONS.md. 8 variants (ASIA_BRK, ASIA_FADE, LON_MOM, LON_REV, NY_MOM, NY_REV, PDHL, H4RSI2) x 28 pairs = 224 tests, 224 with at least 100 DEV trades, real bid/ask with the pair's real-tick median spread as a floor in all years.

## Verdict: 0 survivors, and the daily-FX negative result is confirmed intraday.
- Nominal winners: only 3 tests with one-sided p < 0.05 in DEV against about 11 expected by luck (fewer than chance: no hidden signal); 59 of 224 positive in DEV; Benjamini-Hochberg q 0.10 passes 0.
- Best by DEV t: EURAUD LON_MOM +1.9 bp (t 2.4, VAL -3.5 bp), GBPAUD ASIA_BRK +2.2 bp (t 1.9, VAL -2.6 bp), GBPJPY PDHL +3.8 bp (t 1.7, VAL -0.4 bp); none holds in VAL.
- Pooled over the 28 pairs (bp per trade, DEV / VAL / HOLD): ASIA_BRK -0.3 / -1.0 / -0.1; ASIA_FADE -1.5 / -0.5 / -1.2; LON_MOM -0.4 / -1.3 / -0.2; LON_REV -1.5 / -0.4 / -1.3; NY_MOM -1.2 / -2.1 / +0.4; NY_REV -0.6 / +0.5 / -1.9; PDHL -0.1 / -1.3 / -0.2; H4RSI2 -0.7 / -0.3 / -0.8. Every variant, and its mirror image, is at or below zero after the spread: the spread eats what little there is, in both directions.
- Together with the daily scan (12 variants x 28 pairs, 0 survivors) and the earlier FX families, MT5 broker's FX pairs show no setup that survives costs in any session structure tried.
