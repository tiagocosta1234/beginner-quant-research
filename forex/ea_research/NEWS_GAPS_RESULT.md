# US releases on MT5 broker real ticks: how far prices jump in 10 seconds (2026-10-15 14:39, local clock; descriptive)
Script `news_gaps.py`, table `data/si_ledgers/NEWS_GAPS.csv`. CPI and NFP (08:30 New York = 13:30 London most of the year) and FOMC (14:00 New York = 19:00 London most of the year; one hour earlier in the weeks when only Europe has changed its clocks), Oct 2025 - Oct 2026 (11 CPI, 12 NFP, 8 FOMC), MT5 broker ticks. Move = largest mid move away from the last price before the release within 10 s / 60 s. "Card stop" = the daily card's typical stop: gold 0.26% of price (~$11), Nasdaq 0.20% (~55 points), USDJPY 0.13% (~20 pips, its London box), S&P 0.20%, EURUSD 0.10% (scale only).
| market, release | median 10-s move | median, in card stops | largest | share of releases > 1 stop in 10 s / in 60 s | spread before -> 1 s after (median) |
|---|---|---|---|---|---|
| Gold, CPI | $14.8 | 1.34 | 4.1 | 64% / 82% | 0.52 -> 0.54 |
| Gold, NFP | $14.9 | 1.28 | 5.4 | 55% / 82% | 0.47 -> 1.06 (up to 5.1) |
| Gold, FOMC | $6.7 | 0.58 | 3.7 | 38% / 50% | 0.46 -> 1.74 |
| Nasdaq, CPI | 57 pts | 1.14 | 3.0 | 64% / 82% | 1.67 -> 1.72 |
| Nasdaq, NFP | 57 pts | 1.13 | 2.5 | 58% / 75% | 1.67 |
| Nasdaq, FOMC | 14 pts | 0.26 | 1.9 | 25% / 38% | 1.67 |
| USDJPY, CPI | 23 pips | 1.13 | 3.1 | 55% / 55% | 7.8 -> 9.1 pips |
| USDJPY, NFP | 27 pips | 1.33 | 3.2 | 83% / 83% | 9.6 -> 10.4 pips |
| S&P, CPI / NFP | 14 / 11 pts | 0.92 / 0.74 | 3.1 / 2.2 | 46% / 33% (10 s) | 1.1 |
| EURUSD, CPI / NFP | ~20 / ~30 pips | 1.5 / 2.3 | 4.1 / 3.1 | 55% / 92% (10 s) | widened |
Largest single gaps: gold NFP 2026-09-04 $62.7 in 10 s (5.4 stops, spread $5.09), gold CPI 2026-08-12 $46.9, gold NFP 2026-08-07 $42.5, gold NFP 2026-10-02 $40.4, gold FOMC 2026-07-29 $38.7.
Reading for the trader: MT5 broker widens spreads 10-15x around US releases (USDJPY from 0.6 to 8-10 pips, gold up to $5), and in more than half of the CPI / NFP releases the price jumps past a card-sized stop within 10 seconds, so a stop there fills far beyond its level (4 Sep: -5.8 R on a stop meant to lose 1 R). Any position with a tight stop must be flat before CPI and NFP (13:30 London) and FOMC (19:00 London); the old AccountGuard news-flat (ManualNews.csv) did this for the EAs, the manual card must do it by hand, and ManualORB has no news filter yet (open item before any use).
