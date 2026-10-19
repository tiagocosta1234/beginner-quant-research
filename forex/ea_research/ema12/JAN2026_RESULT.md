# JAN2026 result: the two mechanical 12 EMA rules look in January 2026 like they did in 2022-25 (no edge), 2026-10-19

Pre-registration `PREREG_JAN2026.md` (sha256 8b02d2ef5075724e47ab45f1472c54090b56e1b4baf6bb1f4d1aa94e86f8e081, local clock 14:18, before any P&L), script `jan2026_look.py`, output `JAN2026_OUTPUT.txt`, table `JAN2026_TRIALS.csv`.
Time stamps from the file system: PREREG written and hashed 14:18:13 (its header says "14:2x" and the dry-run "14:17": both were estimates; the dry-run ran between the 14:15 and 14:18 clock readings), run finished 14:18:27, result 14:19.
Waiver: the trader, 19 Oct ("run a january 2026 run"), January only, descriptive. MT5 broker M1 bid/ask, rows with time >= 2026-02-01 never read (last bar read 2026-01-30 23:58). The 44 trials are exactly the registered ones (32 EMA12 + 12 MANUALRULE).

## Result
| group (mean of trial means) | Jan 2026 | DEV 2022-24 | VAL 2025 | trials with Jan mean R > 0 |
|---|---|---|---|---|
| MANUALRULE gold (6) | -0.229 | -0.082 | -0.056 | 0 |
| MANUALRULE gold K1, London + NY | -0.195 | -0.078 | -0.052 | 0 of 2 |
| EMA12 gold (16) | +0.014 | -0.061 | -0.095 | 10 |
| MANUALRULE Nasdaq (6) | -0.217 | -0.105 | -0.079 | 0 |
| EMA12 Nasdaq (16) | -0.030 | -0.077 | -0.095 | 9 |
| **all 44** | **-0.066** | -0.076 | -0.087 | 19 |

- the trader's own wording as a rule (MANUALRULE K1, gold): London 16 trades, 7 above zero, mean R -0.344 (t -1.79); NY 15 trades, 9 above zero, -0.047. The rule fires on 16 of the 21 January London sessions.
- EMA12 gold London: the unfiltered variants lose -0.36..-0.47 R (n 19, t -1.7..-2.5), three of the four momentum-filtered ones gain +0.13..+0.25 (n 16) and the fourth loses -0.05: opposite signs for the same session, i.e. noise at n of about 20. NY gold unfiltered +0.05..+0.24, also noise.
- 19 of 44 above zero is what chance gives; the all-44 average (-0.066) sits between DEV and VAL.

## Reading
- January adds nothing for the mechanical rules: no trial is a candidate and none is opened further on 2026 (n of about 20 per trial; a mean R has a standard error near 0.18).
- It says nothing about the trader's discretionary entries: the mechanical stand-in reproduced his side on 10 of 22 days in his own 30-trade window. That is what the blind replay (`PREREG_BLIND2026.md`) tests.
- Per-day trades were not saved or shown, so a blind replay of January days stays blind.
- Hold-out status: 2026-02-01..2026-09-30 is still sealed; January 2026 and 1-16 Oct 2026 are open data.
