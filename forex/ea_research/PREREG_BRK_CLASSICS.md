# Pre-registration BRK-CLASSICS (breakout day, round 8; written 2026-10-15 11:56 local (commit time), before any code or result)
The named breakout strategies of the trading literature not yet tested here. Session definitions, execution and costs as rounds 1-7 (MT5 broker M1 bid/ask, 46 markets, sessions from `breakouts.session`; stop orders fill at the level or the minute's open beyond it; market entries at the next minute's ask/bid; stops on the executable side, gapped stops at the open; exit at the session close capped 22:55 server; R >= 2 spreads). Daily ATR14 / previous close / previous range from server days (01:00-22:59). Random-entry control (same window, random side, same R, same exit) for every cell.

## Cells (6)
- **C1 Larry Williams volatility breakout k = 0.5 (all 46 markets):** O = mid at the session open; buy stop at O + 0.5 x previous day's range, sell stop at O - 0.5 x range, live until 3 h after the open; stop = O (R = 0.5 x range); exit at the session close.
- **C2 the same with k = 0.25** (stop = O, R = 0.25 x range).
- **C3 5-minute opening range (Zarattini, Barbon and Aziz 2023, QQQ):** indices only (SP, NSDQ, DOW, DAX, NIKKEI, ASX). First 5-minute candle of the cash session: up candle -> buy at the next minute's ask, stop at that candle's low; down candle -> sell, stop at its high; doji (|close-open| < 1 spread) -> no trade; exit at the session close. Checked out-of-sample on FTSE / CAC / Russell (MT5 broker files, as INDEX-OOS) in the same run.
- **C4 cash-gap continuation (indices):** gap = (mid at the session open - previous session close at its close time) / ATR14; if |gap| >= 0.3 -> trade in the gap's direction at open + 5 minutes; stop 0.5 ATR; exit at the session close.
- **C5 cash-gap fade (indices):** same gaps, trade AGAINST the gap at open + 5 minutes; target = the previous session close (gap fill), stop 0.5 ATR, else exit at the session close.
- **C6 inside-day breakout (Crabel, all markets):** if yesterday's server-day range was inside the day before's, stop orders today at yesterday's high and low (01:05 -> 20:00 server), stop at the other side, exit 22:55 server.

## Gates
DEV 2022-24, VAL 2025, 2026 non-clean. 1. DEV mean >= +0.05 R and t >= 2.6 (daily portfolio NW lag 1; Bonferroni 6). 2. VAL mean > 0 and t >= 1.65. 3. Beats its random control by >= 0.05 R in DEV and VAL. C3 also reported on the three MT5 broker indices.
## Honest prior
About 5% each; C3 is the best-documented (published on QQQ 2016-2023) but rounds 1-7 found the index breakout decaying after 2022.
