# Pre-registration FX3-JPY22: USDJPY long in the 22:00 server hour, confirmation on 2026 (written 2026-10-14 before the 2026 numbers were computed)

Origin: the only cell that passed K3's training rule on 2022-25 (CONFLUENCE_H1_RESULT.md: +0.77 bp/hour, t +4.3, found by scanning 924 hour x market cells, so the 2022-25 figure is selection-biased).
ONE trial. Rule: every weekday, buy USDJPY at the ask at the open of minute 5 of server hour 22, sell at the bid at the open of minute 5 of server hour 23 (K3's registered
execution); skip if either bar is missing or the day is not Mon-Fri; slippage 0.1 bp per side. Data: MT5 broker M1 bid/ask, server clock.
Test window: 2026-01-01..2026-09-30 (unseen by this rule: K3 trained on 2022-25 only), plus 2022-25 reported for context only.
Accept: 2026 net mean > 0, one-sided t >= 1.65, and net >= 0.3 bp per trade. Descriptive extras (not trials): exit at 22:55 instead of 23:05; spread at exit.
