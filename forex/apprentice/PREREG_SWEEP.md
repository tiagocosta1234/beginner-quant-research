# PREREG_SWEEP: sweep-and-reclaim reversal at key levels, 1:1, GC futures 2020-2025

Written 24 Oct 2026 ~23:4x local clock, before any outcome. Source: our replay losses (5, 8, 9, 11, 12, 16 Jun 2026: stops swept just past a key low/high, then price reversed). the trader: "lets extend until midnight".
## Rule
- Levels (known before 08:00): prev-day high/low (08:00-21:59 of the previous weekday) = PD; Asia high/low (00:00-07:59 today) = AS.
- Scan 15-minute bars from 08:00 to 16:30 local. Long signal: a bar's LOW goes below a support level (PD low or AS low, per variant) AND the bar CLOSES back above that level. Short signal: a bar's HIGH goes above a resistance level AND it CLOSES back below.
- Enter at the next 15m bar open. Stop = the sweep bar's low - 1.0 (long) / high + 1.0 (short). Target 1R. Exit by 21:00 close otherwise. Stop checked first inside a bar. Cost 0.4 pts. Skip if risk < 3 or > 60. One trade per day: the first signal.
## Variants (4)
levels {PD, PD+AS} x trend {none, daily-aligned (prev 21:59 close vs 20-day mean: longs only if up, shorts only if down)}.
## Periods / bar
DEV 2020-22, VAL 2023-24 (judged), HOLD 2025 (passers only). Bonferroni 4: PASS = VAL mean R > 0 with one-sided P <= 0.0125, DEV mean R > 0, VAL n >= 60. 2026 never used.
## Honest prior
~15-20%: sweeps are a known retail idea; many fail at costs. The trend-aligned variant is the one we expect most from.
