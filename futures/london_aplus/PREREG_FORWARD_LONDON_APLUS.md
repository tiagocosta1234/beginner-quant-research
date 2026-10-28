# PREREG_FORWARD_LONDON_APLUS: paper forward log of the claude.pine rule, 28 Oct - 18 Dec 2026

Written Tue 2026-10-27 11:38 (local clock) BEFORE any forward result. the trader: a year-end target -> plan in C:\Users\author\.claude\plans\parsed-greeting-eclipse.md.
Base rate first: the rule is about -0.05 R over 2026 and +0.10 R over Aug-Oct (25 trades on micro gold, 109 on 8 micros); likely no edge. Honest chance of USD 10K of withdrawals by 31 Dec is well under 1%.

## Rule (frozen = claude.pine as of today)
A+ London 12 EMA, 1-minute chart, London 08:00-08:15, 1:1, 1.5-6 pt risk (gold; % of price elsewhere), 2 of 3 confluence, flat 16:00 London.
Markets: MGC, MNQ, MES, MYM on TradingView Paper (never the BROKER eval chart). Costs for the score: fee + 1 tick (MGC 0.292, MNQ 0.860, MES 0.494, MYM 3.44 points per round trip).
Every setup is written to FORWARD_LOG.csv (columns in the file header) BEFORE its result is known; a setup that is not logged before the result does not count.

## Bar (one look, Fri 18 Dec 2026, scored by score_forward.py)
>= 50 logged trades AND mean net R > +0.05 AND win rate >= 53% AND no single market > 40% of trades. Fewer than 50 trades = inconclusive (rule neither confirmed nor closed).
If the bar fails the rule is closed and 1:1 indicator work stops. If it passes: a lead only (50-70 trades cannot prove +0.1 R); a small live test, not scaling.
