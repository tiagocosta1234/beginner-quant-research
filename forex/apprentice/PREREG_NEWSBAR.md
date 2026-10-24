# PREREG_NEWSBAR: trade the US 08:30 ET release candle, 1:1, GC futures 2020-2025
Written 24 Oct 2026 (local clock, file time), before any outcome. Source: June 2026 replay (5 Jun jobs, 10 Jun CPI, 9 Jun / 4 Jun spikes gave 100-pt moves).
## Event (data-defined, causal)
The 15m bar starting 13:30 local (or 12:30 when US/EU DST differ) is an EVENT if its range >= 2.5 x the mean range of the previous 20 15m bars. The first such bar of the day (12:30 checked before 13:30) counts. Known when the bar closes.
## Trade (enter at the next 15m open)
- Direction: CONT = the event bar's direction (close vs open); FADE = the opposite.
- Stop: FULL = beyond the event bar's far extreme +/- 1.0; HALF = beyond the event bar's midpoint +/- 1.0 (for CONT; for FADE, beyond the bar's near extreme +/- 1.0 is FULL and the midpoint is HALF mirrored).
- Target 1R; else exit at 21:00 close. Stop checked first. Cost 0.4. Skip if risk < 3 or > 80.
## Variants (4): {CONT, FADE} x {FULL, HALF}. Periods DEV 2020-22, VAL 2023-24 (judged), HOLD 2025 (passers only).
## Bar: VAL mean R > 0 with one-sided P <= 0.0125 (Bonferroni 4), DEV mean R > 0, VAL n >= 40.
## Honest prior ~10-15%.
## Amendment 1 (after the dry run, before any outcome)
- FADE/HALF is degenerate: the fade entry sits near the event bar's close, so the bar midpoint is on the wrong side of entry for most events (5 DEV trades). Dropped. 3 variants judged; Bonferroni kept at 4 (conservative).
- Bad-data filter: a day is dropped if any minute-to-minute |close change| > 32 (not 8 as in other tests), because news minutes legitimately jump > 8.
