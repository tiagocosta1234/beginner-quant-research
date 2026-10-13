# MT5 economic-calendar surprises: result (2026-10-13)

Pre-registration: PREREG_EVENTS.md. Code: event_lab.py; data exported read-only with ExportCalendar.mq5 (D:\finance\data_macro\mt5_calendar.csv, 68,353 rows, 2021-12..2026-08, times in UTC). Ledgers: D:\finance\si_ledgers\EVENTS_real.csv, EVENTS_placebo.csv. 2026 never used.

## What was tested
Real consensus surprises (MT5's actual vs forecast, sign by MetaQuotes' impact flag, scaled by the causal standard deviation of previous surprises of the same event), strong ones only (|S| >= 1: 437 events, 328 in 2022-24, 109 in 2025), traded as follow-the-surprise on the mapped currency pairs / gold with real M1 bid and ask, entry 1 or 5 minutes after the release, hold 5 / 15 / 60 minutes. 3 pools x 3 horizons x 2 delays = 18 tests, block sign-flip permutation, Bonferroni p < 0.0028, then one look at 2025.

## Result
- Placebo calendar (event times +7 days): 0 of 18 (best p 0.018).
- Real calendar: **0 of 18 pass DEV**. Best p 0.0078 (all strong USD events, 5-minute delay, 15-minute hold, net +1.68 bp).
- Tier-1 US events (NFP, unemployment, earnings, CPI, retail sales, GDP, jobless claims, PMIs, FOMC; 115 strong events) are positive net in every DEV test (+1.35 to +3.90 bp, p 0.009-0.14) but none reaches the Bonferroni bar, and in 2025 the same tests are negative (-1.3 to -3.6 bp, 44 events). The non-USD pool is negative throughout.
- The random-direction mean is -0.3 bp: the cost of the spread at these horizons is small, so the question is only whether the surprise direction carries information after a one-minute delay; here it carries a little in 2022-24 and nothing in 2025.

## Verdict
No consensus-surprise follow-through strategy survives the pre-registered test. The tier-1 US pattern (+2-4 bp per event net, 2022-24) is a possible weak effect that did not hold in 2025 and is below detectability with 115 events; it is NOT a candidate. The installed system stays.

## Open
More events need more years (the calendar file starts 2021-12); entries within the first minute need real ticks (available only from 2025-10, 2026-08-16 onwards sealed for the HF family), where the reaction is largest; tick_volume (exported to D:\finance\ticks_vol, 46 symbols) has not been used as a feature yet.
