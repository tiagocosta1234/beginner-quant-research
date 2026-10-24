# PREREG_G24: the 1:1 trade "every way" (24 mechanical variants), GC futures 2020-2025

Written 24 Oct 2026 ~23:1x local clock, before any outcome. the trader: "backtest the 1:1 in every way possible". After F2PROXY (FAIL).
## Grid (2 x 2 x 3 x 2 = 24 variants, all 1:1)
- **Slot:** LDN entry 08:00 open; NY entry 14:30 open (local clock).
- **Trend:** "1h" = 1h close vs EMA20 with the EMA rising/falling over 4 bars; "both" = 1h AND daily (prev 21:59 close vs 20-day mean) agree.
- **Stop:** "range" = beyond the lowest low / highest high since 00:00 (LDN) or since 08:00 (NY), +/- 1.0; "atr" = 1.5 x ATR14 of 1h bars; "swing" = beyond the last 1h fractal swing (2 bars each side) before entry, +/- 1.0.
- **Level:** "off" = no level condition; "on" = a mechanical clean level: entry within 0.5 x ATR14(1h) on the right side of one of {prev-day high, prev-day low, Asia high, Asia low} (+ London high/low for NY), i.e. long just above a level, short just below.
Exit: stop, 1R target, or 21:00 close. Stop checked first inside a bar. Cost 0.4 pts. Skip if risk < 5 or > 80 pts.
## Data and periods
Databento GC 1m, weekdays, bad days dropped (< 900 bars 00:00-21:00 or a minute jump > 8). DEV 2020-2022, VAL 2023-2024 (judged), HOLD 2025 (one look, passers only). 2026 never used.
## Bar (VAL, one look, Bonferroni for 24)
PASS = VAL mean R > 0 with one-sided t P <= 0.05/24 = 0.0021, AND DEV mean R > 0, AND >= 60 VAL trades. Everything else is reported, not judged.
## Honest prior
Every mechanical 08:00 test here has failed (BIAS8, EMA15, DIR8, F2PROXY). Expect 0 passes; the useful read is which knobs move the mean.
