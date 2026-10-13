# Erratum 2026-10-11: the -500 per-stream daily clip made the 8-strategy book look good

`combine_all.build()`, `eval_cycles_all.py`, `ALL_POSITIVE_ONE_CURVE.png` and `EVAL_CYCLES_2022_2026.png` clip every stream's DAILY result at -500 USD
(`X.clip(lower=-500)`). That rule is not implementable: it removes the part of each losing day below -500 after the day is known, with no cost
on the winning days (a real stop would also cut trades that recover, and gaps jump over it). Over 2022-26 it added about 166K USD at stream scale
(per stream: SDB 24K, XAU5 13K, gold nights 38K, NSDQ nights 21K, pre-FOMC 6K, crypto weekend 36K, turn of month 13K, COT 16K).

Without the clip (`book_variants.py`, output `BOOK_VARIANTS_OUTPUT.txt`, 2026 regime, account at +560 counted):

| Book | daily sd 2026 | 2026 evals pass/fail | max DD 2022-26 | P(pass) 30 Oct / 30 Nov / 22 Dec | breach |
|---|---|---|---|---|---|
| A, as charted (with clip) | 717 | 7/0 | 2,504 | 12 / 86 / 98% | 0.0% |
| A, no clip (pair scaled down to fit) | 822 | 2/0 | 8,256 | 2 / 29 / 50% | 0.5% |
| B, pair untouched at x1.2 + 6 others on top, no clip | 1,087 | 4/0 | 9,163 | 10 / 61 / 81% | 0.3% |
| Pair only (x1.2) | 791 | 5/0 | 10,330 | 7 / 62 / 83% | 0.1% |

Conclusion: the "29 passes, 0 fails" and "9 of 9 monthly starts in 2026" results came from the clip. Without it the book does not beat the pair.
Also: book A ran the pair at 0.65x / 0.50x of the live lots. The EA build for the 8-strategy book is stopped. The pair alone stays the plan.
Also checked today (read-only, portable terminal on account <acct>): NSDQ+/SP+/DOW+/DAX+/BTCUSD+/ETHUSD+ exist, crypto trades on weekends,
the account charges no swap and no commission (gold held over the 9-10 Oct rollover: swap 0.00).
