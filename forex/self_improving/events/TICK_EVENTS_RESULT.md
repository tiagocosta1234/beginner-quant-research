# Consensus surprises at tick resolution: result (2026-10-13)

Pre-registration: PREREG_TICK_EVENTS.md (with Amendment 1, the clock error). Code: tick_event_lab.py. Ledgers D:\finance\si_ledgers\TICKEVENTS_real.csv / _placebo.csv. Ticks to 2026-08-15 only (sealed afterwards). 103 strong events in the tick era, 77 USD (41 tier-1).

## The error found on the way
The first run treated the MT5 tick epoch as UTC; it is the SERVER clock (Athens, naive; proof: the daily spread peak at tick-epoch hour 0, as in the server-clock M1 files). It compared UTC release times with server-clock ticks, 3 hours off: it was invalid and was discarded before any reading. The HF family had the same bug (server hour, weekday, event features): fixed in hf_data.py, lesson L13 added to the SDS, rebuild and rerun in progress.

## Pre-registered tests (USD pool, delay 10 / 30 s x hold 60 / 300 s, Bonferroni 0.0125)
Placebo calendar: 0 of 4 (p 0.57-0.80). Real: **0 of 4**: net -1.37 / -2.17 / -1.08 / -1.64 bp against random-direction means of -1.07 / -1.03 / -0.84 / -0.81 bp, p 0.70 / 0.93 / 0.70 / 0.89.

## Profile (descriptive): where the surprise is absorbed
Mean move of the mid price in the surprise direction against the quote 1 s before the release, and the mean spread (bp):
| seconds | -60 | -10 | -1 | +1 | +2 | +5 | +10 | +30 | +60 | +300 | +900 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| all strong USD (77): move | +0.56 | +0.26 | 0.00 | +0.93 | +1.73 | +2.24 | +2.59 | +2.45 | +2.46 | +1.30 | +1.68 |
| spread | 0.69 | 1.00 | 2.40 | 2.88 | 2.80 | 1.86 | 1.38 | 0.89 | 0.81 | 0.74 | 0.99 |
| tier-1 USD (41): move | +0.67 | +0.42 | 0.00 | +1.47 | +2.95 | +3.68 | +4.23 | +4.27 | +4.59 | +2.29 | +2.65 |
| spread | 0.70 | 1.21 | 3.41 | 4.12 | 4.14 | 2.58 | 1.75 | 0.98 | 0.86 | 0.75 | 1.11 |
The information is real (+2.5 bp on average, +4.6 bp on tier-1) and is absorbed within about 10 seconds, while the spread is 3-5 times normal; the move then stops, and partly reverses between 60 s and 300 s. What an EA that sees the calendar value 10 s late can still harvest is zero (the tests above). Entering at +1 s on tier-1 events would harvest about +3.1 bp of mid move for about 2.5 bp of half-spreads: a break-even race at one second that no MT5 calendar feed can win (the lag of the calendar value in the terminal is unknown and was not measurable from history).

## Verdict
Closed: no consensus-surprise follow-through is available at a speed an EA can use. One exploratory observation, NOT tested and NOT a candidate: the partial reversal between 60 s and 300 s (tier-1: +4.59 to +2.29 bp, i.e. a fade of about 2.3 bp gross for about 0.8 bp of cost) would need a fresh pre-registered test on events after 2026-08-15, which are sealed; they can only be collected forward.

## Post-release reversal: registered forward test and exploratory measure (2026-10-14; PREREG_REVERSAL.md, reversal_lab.py)
Exploratory only (the profile was seen before registering), window 2025-10-01..2026-08-15, fade = enter against the surprise at +60 s, exit +300 s: tier-1 USD n 41, mean net +1.50 bp, t +1.68, win 59%; all strong USD n 77, +0.36 bp, t +0.65; shorter holds (120 s) and earlier entry (+30 s) are about zero. The real test (events >= 2026-08-16, n >= 25, mean net > +0.5 bp, t >= 2, beats the +7-day placebo by t >= 1.65) waits for a read-only re-export of the calendar and ticks (expected December 2026).
