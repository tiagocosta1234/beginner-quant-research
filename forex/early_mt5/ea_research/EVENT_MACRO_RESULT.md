# V: scheduled US macro events (pre-FOMC drift; release-day continuation): result (2026-10-10, local local clock)

Pre-registration `PREREG_EVENT_MACRO.md` (commit 2782714, before any P&L; public calendar `EVENT_CALENDAR_2022_2026.csv` from federalreserve.gov and the BLS archives), simulator `event_macro.py`, outputs `EVENT_MACRO_OUTPUT.txt`, `EVENT_MACRO_PLACEBO_OUTPUT.txt`, `EVENT_MACRO_HOLDOUT_OUTPUT.txt`, ledger family event_macro (two trials).

## Verdict: both trials closed. V1 passed development and FAILED its one look at the 2026 hold-out; V2 failed development
| trial | DEV 2022-24 | VAL 2025 | HOLD-OUT 2026 (one look) |
|---|---|---|---|
| V1 pre-FOMC drift: long SP/NSDQ/DOW from 14:02 ET of the day before to 13:55 ET on the statement day | 24 events, +46.7 bp/event, t +2.99, 75% wins | 8 events, +17.1 bp, 75% wins | 6 events, **-27.6 bp/event**, t -1.28, 2 of 6 positive -> fails acceptance 3 |
| V2 follow the 08:30-08:45 ET move on NFP/CPI days (gold, EURUSD, USDJPY, NSDQ) to 11:30 ET | 72 events, -6.1 bp, t -1.14 | 22 events, +6.6 bp | not opened |

## Reading
- V1 looked like the first development pass of the week, and the placebo explained it before the hold-out did. The same 24-hour window on the other 917 business days of 2022-25 averages +3.3 bp. The FOMC windows average +39.3 bp (difference t +2.82; 2.5% of random 32-day draws do as well), but the gap is almost all 2022 (+99.7 bp, t +3.25, the bear-market relief rallies into FOMC days). In 2023, 2024 and 2025 the gap is +10 to +24 bp a year (t about 0.7 each). In 2026 it turned negative (-27.6 bp). The documented pre-FOMC drift (1994-2011) is not a reliable effect in the 2023-26 regime.
- V2: no continuation after the first 15 minutes of an 08:30 release, NFP worse than CPI (-7.9 vs +1.7 bp per event over 2022-25).
- For the trader's goal: even a confirmed V1 could not have helped this month. It trades eight times a year (one window in October, 27-28 Oct), and at MT5 broker's 1%-risk-per-idea size it is worth a few hundred USD per event, against the 7,900 still needed.
