# Out-of-the-box round result (2026-10-12)

Pre-registration: PREREG_OUTSIDE_BOX.md. MT5 broker data, spread paid.

| Idea | Result | Verdict |
|---|---|---|
| **EC equity-curve start timing** | FT pool, fresh account started when the system's trailing 40-day P&L > 0 (ON) vs <= 0 (OFF): pass 22 bd **12.7% vs 6.1%** (x2.07), pass 44 bd **35.5% vs 17.8%** (x1.99), breach 0.0% vs 4.7% at 44 bd. MT5 broker 12-month pool: only 2 OFF start days, uninformative. OFF stretches: 18 episodes, 7 of at least 10 days (May-Aug 2022, Dec 2022-Jun 2023 = 126 days, Aug-Oct 2023, Feb-Mar 2024, Aug-Sep 2025). Today: ON (trailing 40-day P&L +12.5k). | supports the idea in FT (ratio >= 1.3), MT5 broker cannot confirm; mostly "2022-23 versus the rest", about 7 real OFF stretches: a hint, not proof |
| WB WTI / Brent spread reversion | 27 trades in 4.75 years; DEV 15 trades +51 bp (t 1.80); VAL 5 trades -32.5 bp; HOLD (looked at although not accepted) 7 trades +132 bp | fail (VAL negative, tiny samples) |
| IN NR7 breakout, gold | DEV 113 trades +3.8 bp (t 0.49); VAL 43 +21.5 bp (t 1.28) | fail |
| IN NR7 breakout, indices | DEV 188 +10.9 bp (t 1.58); VAL 72 +2.6 bp | fail (< +20 bp) |
| PH1 pre-holiday | DEV 30 events -26.2 bp; VAL 11 -13.4 bp | fail, negative |
| PH2 third-Friday opex | DEV 35 -7.7 bp; VAL 11 +19.3 bp | fail |

## Reading
- Nothing new in the markets again (WB, IN, PH), consistent with the other families.
- The one structural finding: the system's own recent P&L is informative about the pass rate of an account started now. For a NEW test the practical rule is "start only when the trailing 40 business days of the system are positive" (about 2x the pass rate in the 2022-26 history); the live account is already running and the system is ON.
