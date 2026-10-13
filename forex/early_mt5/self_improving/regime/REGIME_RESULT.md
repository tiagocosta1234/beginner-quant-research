# Regime layer on the installed system: result (2026-10-13)

Pre-registration: PREREG_REGIME.md. Code: regime_lab.py. Ledger: D:\finance\si_ledgers\REG_real.csv. 2026 never loaded.

## Setup
The installed system (pair x1.5 + ManualDip x0.75, guard 1,500, CPI news-flat; FT 2022-26 pool, days to 2025-12-31) at size factors f in {0, 0.5, 1.0, 1.5}; a policy = if (1-2 daily regime conditions) then f_on else f_off; 25 daily features known before the day (macro regime with a 2-business-day lag, scheduled event flags, gold state from XAUUSD 15-minute bars of previous days, the system's own trailing P&L, weekday). Scored by replaying the MT5 broker Pro 100K rules (pass70) from every start day: P(pass by 44 bd) - 3 x P(breach). Windows A 2022-01..2023-06 (search), B 2023-07..2024-12, VAL 2025.
Baseline (f = 1.0, the installed system): P(pass by 44 bd) A 0.3% (breach 4.7%), B 16.8% (0.0%), VAL 44.7% (0.0%). The installed system depends heavily on the year.

## Calibration: PASSED
Five placebo worlds (seeds 41-45): 0 survivors at B and VAL, 100,000 policies each. Caveat: in world 41 the B z reached 6.1 and only the floors stopped it.

## Real run: 100,000 policies
- Stage A: 200 promoted (delta pass > 0 and delta breach <= 0 on A; best delta score +0.26).
- Stage B: 200 tested; median delta pass -16.8 points; 8 positive, 5 with delta pass >= +2 points (all with no extra breach); best +6.7 points (if the previous day's P&L is in the upper three quarters and the previous gold day's range is below its median: factor 0.5, otherwise 1.5; p = 0.015). Benjamini-Hochberg needs p <= 2.5e-4 for the best of 200: **0 survivors**. (The z of 10^15 in the log is a numerical artefact of a policy whose null does not vary.)
- Stage VAL: nothing to look at.

## Verdict
No macro, event, gold-state or own-performance regime layer improves the installed system's P(pass by 44 bd) beyond what chance gives among 100,000 policies; most policies hurt (median -16.8 points in B). The installed system stays as it is. The only hint (the previous-day P&L plus quiet gold range) has p = 0.015 in 200 tests and is not pursued; it resembles the 'performance throttle' of IMPROVE_ROUND, which was a free safety, not a gain.
