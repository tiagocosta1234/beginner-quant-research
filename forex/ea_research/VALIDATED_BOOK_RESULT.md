# VALIDATED_BOOK_RESULT - account plans built only from legs that survived an out-of-time test (2026-10-15, local clock 15:37)

> **2026-10-15 15:52: the account numbers in this file are SUPERSEDED by `D2_MT5RULE_RESULT.md`** (MT5 broker's daily line is set from the day-start BALANCE, so a held book carries floating losses into the line, and only realised profit counts, at most +2,000 a day). The edge results (DEV / VAL / OOT / HOLD / ticks) are unaffected.
Pre-registration `PREREG_VALIDATED_BOOK.md` (commit 7e39d4de). Code `validated_book.py`, output `VALIDATED_BOOK_OUTPUT.txt`, rows `D:/finance/si_ledgers/VALIDATED_BOOK.csv`.

## Verdict: no add-on qualifies; D2 (100k gross, 1,500 day guard) alone is the best validated plan
Bar: +2 points of pass by 30 Jun 27 with at most +1 point of breach. pass% / breach%:
| configuration | pool | 22 Dec | 31 Mar 27 | 30 Jun 27 | 31 Dec 27 |
|---|---|---|---|---|---|
| **D2 100k** | 2022-25 | 2.6 / 4.1 | 35.5 / 8.5 | **60.2 / 9.9** | 82.3 / 10.9 |
| D2 100k | 2022-26 | 3.4 / 7.0 | 33.5 / 13.9 | 54.6 / 16.4 | 74.3 / 18.2 |
| + USDJPY 150 | 2022-25 | 5.3 / 7.1 | 40.2 / 13.2 | 62.0 / 15.2 (fails: +1.8 / +5.3) | 78.5 / 16.6 |
| + USDJPY 300 | 2022-25 | 7.8 / 17.4 | 34.3 / 30.2 | 47.6 / 35.1 | 57.8 / 38.5 |
| + DA dips | 2022-25 | 3.0 / 4.5 | 35.2 / 9.3 | 60.0 / 11.0 (fails) | 81.2 / 12.0 |
| + USDJPY 150 + DA | 2022-25 | 5.7 / 8.2 | 39.1 / 15.4 | 60.1 / 17.8 | 75.2 / 19.4 |
| D2 75k + USDJPY 300 + DA | 2022-25 | 4.8 / 13.1 | 27.6 / 26.4 | 42.5 / 31.8 | 56.2 / 36.1 |
- Legs on 1,198 common days (2022-02-15..2026-10-02): USDJPY +0.066 R a trade after the 0.06 R real-tick haircut (1,174 trades); DA 114 days, +25 USD a day on its days at its registered size. Daily correlations: D2-USDJPY -0.03, D2-DA +0.18, USDJPY-DA -0.01.
- USDJPY adds a little speed by 22 Dec (+2.7 to +5 points) but much more breach: its -81 R drawdowns land on the same thin 5,708 buffer.
- Sample sensitivity: D2 100k alone here starts on 2022-02-15 as one continuous run and gives 60.2 / 9.9 by 30 Jun 27; in D2_ACCOUNT (from 2022-01-03, restarted per period) 53.5 / 13.6. Read the D2 numbers as about 50-60% pass / 10-20% breach by 30 Jun 27, 2-3% / 4-8% by 22 Dec.
- The day lows are summed across legs (pessimistic) and the USDJPY day low is its stop (a gap through it is only in the haircut).
