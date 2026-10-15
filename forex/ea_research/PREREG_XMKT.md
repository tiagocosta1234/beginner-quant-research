# PREREG_XMKT - the untested cross-market and daily-pattern items of the trader's 50-hypothesis list (written 2026-10-15 local clock 19:03, before any P&L)
Items 10, 11, 12, 13, 14, 15, 18, 19, 20 and 34 (16 is not defined well enough to code without a search; the other items are covered by earlier families: see the triage in XMKT_RESULT.md).

## Common rules
MT5 broker M1 bid/ask 2021-12..2026-10-02; longs fill at the ask, shorts at the bid, exits on the other side at the minute's open; result in basis points of price, net of the spread. Times are New York local unless marked server; nothing is decided or traded in server hours 23 or 0. One fixed rule per hypothesis, no parameter search.
- X10 open price discovery (SP, NSDQ, DOW): overnight move = 09:30 mid - previous 15:55 mid; first reaction = 10:00 mid - 09:30 mid; if the reaction has the opposite sign to the overnight move, trade in the reaction's direction 10:00 -> 15:55.
- X11 SP leads NSDQ / X12 NSDQ leads SP: 09:30-11:00 on a 5-minute grid; leader 5-minute return z > 1.5 (z vs the previous 20 days' 5-minute returns in the same window) while the follower's z is below half the leader's -> trade the follower in the leader's direction for 15 minutes; one position at a time.
- X13 DAX before the US open: sign of DAX 03:00 -> 09:25 -> trade SP the same way 09:35 -> 11:30.
- X14 NIKKEI -> USDJPY: sign of NIKKEI 20:00 (previous evening) -> 02:00 -> trade USDJPY the same way 03:00 -> 07:00.
- X15 oil -> USDCAD on EIA crude-stock days (MT5 calendar event 840200001, UTC times): WTI return over the first 15 minutes after the release; if |return| > 0.3%, trade USDCAD the OPPOSITE way from release + 16 min to + 90 min.
- X18 DAX session -> SP afternoon: sign of DAX 03:00 -> 11:30 -> trade SP the same way 11:35 -> 15:55.
- X19 triangular residual: res = EURJPY mid - EURUSD mid x USDJPY mid at each minute close; if |res| > the EURJPY spread, trade EURJPY toward the implied price from the next minute for 5 minutes; one position at a time.
- X20a / X20b stress contagion: the first 30-minute SP drop < -1.0% between 09:30 and 15:00 -> short USDJPY (X20a) / long XAUUSD (X20b) from the next minute for 60 minutes.
- X34 close strength: for SP, NSDQ, DOW, DAX, NIKKEI, XAUUSD, if the server-day close (22:55) is in the top 10% of the day's 01:00-22:55 range -> long the next server day 01:05 -> 22:45; bottom 10% -> short.

## Tests
11 hypotheses. Periods DEV 2022-24, VAL 2025, 2026 (these families never used 2026). Pass: DEV+VAL t of net bp per trade >= 2.61 (one-sided 5% / 11), mean > 0 in DEV, VAL and 2026, and at least 100 trades. A passer then needs HistData 2020-21 (where the symbols exist) and MT5 broker real ticks before it is a candidate. Reported for every hypothesis: trades, gross and net bp, win rate, t, by period.

## Honest prior
Cross-index lead-lag on dealer CFD quotes is usually arbitraged inside the minute; the triangle is quoted by one dealer and should not deviate by more than its spread; X13 / X14 / X18 resemble the B12 partner-index and DAX-led tests (negative). Expected: 0 or 1 pass.
