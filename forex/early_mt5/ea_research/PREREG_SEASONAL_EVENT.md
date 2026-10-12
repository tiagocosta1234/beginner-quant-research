# Pre-registration: three documented index anomalies, no tuning (written 2026-10-12, before any return was computed)

Request: the trader, "(original wording omitted)" = look for a different TYPE of edge instead of repeating SDB on other markets. Own EAs only, nothing is bought.
Three published calendar anomalies, rules taken from the literature as written, one parameter set each, US indices only (SP+, NSDQ+, DOW+ on MT5 broker M1 bid/ask, `data_mt5`, 2021-12 .. 2026-10-02; no swap on the swap-free account).
All trades LONG, entry at the ASK, exit at the BID (spread paid), return in bp of the entry price. The three indices are averaged into ONE observation per event/day (they are ~0.9 correlated).

- SE1 OVERNIGHT: buy at the 15:59:00 New York bar open, sell at the next trading day's 09:30:00 bar open (consecutive trading days, gap <= 4 calendar days). Overnight-premium literature (Cooper-Cliff-Gulen, Lou-Polk-Skouras).
- SE2 TURN OF MONTH: buy at 15:59 NY on the 4th-from-last trading day of a month, sell at 15:59 NY on the 3rd trading day of the next month (Ariel 1987, Lakonishok-Smidt 1988).
- SE3 PRE-FOMC DRIFT: buy at 14:00:00 NY on the trading day BEFORE an FOMC announcement, sell at 14:00:00 NY on the announcement day, i.e. just before the statement (Lucca-Moench 2015). FOMC dates from `D:\finance\data_macro\event_calendar.csv`.

Periods by entry date: DEV 2022-01-01 .. 2024-12-31, VAL 2025, HOLD-OUT 2026-01-01 .. 2026-09-30 (one look, accepted trials only).

## Acceptance (positive direction is the literature's, so one-sided)
- DEV: mean net bp >= the economic floor AND t >= the bar. SE1: floor 2 bp/night, t >= 2.0 (about 750 nights). SE2 and SE3: floor 10 bp/event, t >= 1.65 (about 36 and 24 events).
- VAL 2025: mean > 0. HOLD-OUT 2026: mean > 0.
- Even if a trial passes, it is a candidate only: these edges are a few bp to tens of bp per trade, so their use for passing MT5 broker fast (the pass-speed gate) is a separate pre-registered question; nothing goes live from this round.

## Honest prior
SE1: moderate that the overnight premium persists (2022-26 had the 2022 bear market), small after costs. SE3: low (the pre-FOMC drift faded after 2015, 24 DEV events). SE2: low to moderate. Trials logged as SE1-SE3 (DEV, VAL).
