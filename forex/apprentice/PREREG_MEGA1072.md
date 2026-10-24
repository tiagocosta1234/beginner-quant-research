# PREREG_MEGA1072: every style of trading, 1,072 mechanical variants on GC futures 2020-2025

Written 25 Oct 2026 (local clock = file time), before any outcome. the trader: "try absolutely every style of trading. one thousand models".

## Data / periods
Databento GC 1m -> 15m bars (local clock). Weekdays from 2020-01-01; a day is dropped if its 00:00-21:00 has < 900 minute bars or any minute |close change| > 8 (repo standard). DEV 2020-2022, VAL 2023-2024 (judged), HOLD 2025 (opened ONLY for variants that pass VAL, once). 2026 is never used.

## 13 styles (134 entry rules), in the LDN window (entries 08:00-11:45) and/or the NY window (14:30-17:30); one trade per day per variant (first signal); entry at the next 15m bar open
1. EMA cross (fast {8,12,20} x slow {26,50}) x window = 12
2. Opening-range break / fade (N {15,30,60} min) x {BRK,FADE} x window = 12
3. Previous-day high/low: break (close beyond) / sweep-fade, x window = 4
4. Asia (00:00-07:59) high/low: break / sweep-fade, x window = 4
5. Overnight-gap follow / fade (threshold {0.5, 1.0} x 1h ATR) x window = 8
6. RSI14 extremes {30/70, 25/75, 20/80} x {fade, follow-cross} x window = 12
7. Bollinger(20, k {2.0, 2.5}) x {fade, break} x window = 8
8. Donchian N {20, 40} x {break, fade} x window = 8
9. 4-hour momentum follow / fade (threshold {0, 0.5 x 1h ATR}) x window = 8
10. Fixed-time seasonality: enter long or short at each hour 00:00..20:00 (21 x 2) = 42
11. Session-mean deviation (k {1.0, 1.5} x 1h ATR) x {fade, follow} x window = 8
12. Daily-trend pullback to the 15m EMA {20, 50} x window = 4
13. NR7 bar breakout follow / fade x window = 4

## Exits (8 per entry rule: 134 x 8 = 1,072 variants)
Stop = m x ATR14 of 1h bars (last completed hour), m {0.75, 1.0, 1.5, 2.0}; target = R x risk, R {1, 2}; else exit at the 21:00 bar close. Stop checked before target inside a bar. Skip if risk < 3 or > 80 points. Cost 0.4 points per trade.

## Bar (Bonferroni for 1,072 variants)
PASS = VAL mean R > 0 with one-sided t P <= 0.05/1072 (= 4.7e-5) AND DEV mean R > 0 AND VAL n >= 100. Passers get one HOLD-2025 look: HOLD mean R > 0 with one-sided P <= 0.05.

## Reported (no bar)
Number of variants with VAL t >= 2 (about 2.3% = about 24 expected by luck alone); top 15 by VAL t with their DEV numbers; the best variant per style.

## Honest prior
Under 2% that anything passes. Expect a handful of variants with VAL t >= 2 that are noise.
