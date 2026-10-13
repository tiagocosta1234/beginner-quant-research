# Family SE result: three documented index anomalies (2026-10-12)

Pre-registration: PREREG_SEASONAL_EVENT.md. US indices (SP, NSDQ, DOW averaged), long only, ask in / bid out, MT5 broker M1 data.

| Trial | DEV 2022-24 | VAL 2025 | HOLD 2026 | Verdict |
|---|---|---|---|---|
| SE1 overnight (15:59 -> 09:30) | +1.30 bp/night, t 0.53 (747 nights) | +2.26, t 0.47 | not opened | fail: no premium after spread |
| SE2 turn of month | +64.8 bp/event, t 1.57 (36) | +26.3, t 0.35 (12) | not opened | fail: DEV t below 1.65 by 0.08 |
| SE3 pre-FOMC drift | +49.7 bp/event, t 3.13 (24) | +16.9, t 1.50 (8) | **-24.5 bp (6 events)** | **fail at the hold-out** |

## Verdict: no trial passes.
SE3 looked real in 2022-25 (t 3.1 in DEV, positive in VAL) and then reversed in 2026, exactly the "drift faded after 2015" prior; with 6 hold-out events the reversal is itself weak evidence, but the rule was fixed and the hold-out is the test. Not accepted. SE2 missed its bar narrowly; the bar is not moved. SE1 is nothing after the spread.
Even a pass would have been a few tens of bp per event on a handful of events a year, too small to speed up an MT5 broker pass. Calendar anomalies on indices are not the missing edge.
