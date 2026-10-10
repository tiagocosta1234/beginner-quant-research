# F2m: fade the NR7 breakout on the 28 FX pairs: result (2026-10-09 afternoon, local)

Pre-registration `PREREG_FX_NR7_FADE.md`, simulator `fx_nr7.py` (--fade_trials), output `FX_NR7_FADE_OUTPUT.txt`, ledger family fx_nr7 trial F2m. Ledger now 40 of 40: THE LAB BUDGET IS SPENT.
## Verdict: fails acceptance A (consistency); the 2026 hold-out was NOT opened; idea closed
| period | trades | mean R | PF | daily t | win | pairs > 0 |
|---|---|---|---|---|---|---|
| DEV 2022-24 | 2,578 | -0.162 | 0.74 | -4.79 | 32.8% | 7/28 |
| VAL 2025 | 874 | -0.243 | 0.62 | -4.21 | 31.5% | 5/28 |
| 2022-25 pooled | 3,452 | -0.183 | 0.71 | -6.25 | 32.5% | 3/28 |
Both directions lose by similar amounts: the cause is spread at entry (9.2 bp mean) and exit, not direction (diagnostic in FX_NR7_RESULT.md: corrected mid-to-mid gross -2.1 bp for the fade and -3.8 bp for the continuation = no edge).
## What would be needed to look again
A variant that does not trade the rollover hour (entries only 02:00-22:00 server time, exits before 22:00) would be a NEW variant outside the 40-variant budget (needs a dated amendment with a higher bar); the gross edge seen (none: -2 to -4 bp per trade mid-to-mid) is far too small to move the pass speed, so it is not recommended.
