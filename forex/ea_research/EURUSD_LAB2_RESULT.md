# EURUSD-LAB2 result (2026-10-14): calendar timing, cross-pair relative, tick-volume surge, pivots (36 cells)
Pre-registration `PREREG_EURUSD_LAB2.md` (amendment A1 before any P&L: X and V activation thresholds), engine `eurusd_lab2.py`, output `EURUSD_LAB2_OUTPUT.txt`. HOLD 2026 unread.
## Verdict: 0 survivors; family closed
- Placebo ceiling over the 36 cells (500 permutations, DEV): median 2.35, 95th percentile 3.25 (bar for acceptance 3.4). Best real DEV t: +1.84 (V-10-3 fade, +4.1 bp). Nothing close.
- C (calendar timing, 12 cells): net -4..+3 bp, |t| < 1.6 in DEV; continuation after high-impact USD/EUR releases is slightly negative (-1..-2 bp), fade slightly positive and neither is significant.
- X (cross-pair relative EURUSD vs GBP/AUD/NZD): no signal (|t| <= 1.5 in DEV); the 16:05 / 6 h cell flips sign between DEV (+2.9 fade) and VAL (-8.3).
- P (prior-day pivots, resistance/support/pivot): |t| <= 1.4 in DEV; flips sign in 2025 for the R1/S1 cells.
- V (tick-volume surge at 10:05 with a same-direction move): the only coherent pattern, FADE the surge: V-10-3 fade is positive in every calendar year (+5.3 / +4.7 / +2.3 / +5.9 bp; DEV t +1.84, VAL t +1.21 on 37 trades) and V-10-6 fade has the same sign (+2.35 DEV, +3.14 VAL). It misses the DEV bar (t 3.4, mean > 1 bp is met), is based on 123 + 37 entries, and a surge of volume with a price move at the London morning may simply be a stop-run reversal; a lead, not an edge. Opening the sealed 2026 data for it is not allowed (it did not pass development); the clean test is a forward log from 2026-10-14 (tick volume is an MT5-native feed).
No EA, nothing goes to multi_fx_ea. EURUSD stays open.
