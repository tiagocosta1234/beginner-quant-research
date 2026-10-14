# Pre-registration BRK: classic breakouts on every MT5 broker market (written 2026-10-14 ~22:40, before any code or result)
the trader: "trade breakouts". Already tested and not repeated: gold Donchian G1-G6, gold opening-range breakout (London 08:00 / NY 09:30, 1R target), FX NR7 daily, swing-level S/R breakouts (552 cells), the 20-day turtle (agent lab), MQL5 Market range-breakout demos; ManualSDB (live) is itself a daily breakout. New here: the four classic intraday breakout forms run on all 46 markets at each market's own session, with end-of-session exits (no fixed target: breakouts are supposed to run).

## Data and execution
MT5 broker M1 bid/ask, 46 markets, data before 2026-01-01 (2026 sealed). Local session clocks from the server clock with time zones. M5 pattern bars on the session's local clock from M1 mid (true highs/lows). Entries at the open of the minute after the signal (server minute :00 -> :01), long at the ask, exits at the bid (short mirrored); stops minute by minute, gapped stops at the open; no entry or exit in server hours 23 and 0 (exits capped at 22:55 server). Stop distance at least 2 spreads. One trade per cell, market and day (B3: one position at a time).
Sessions: SP, NSDQ, DOW, crypto: New York 09:30-16:00; WTI, BRENT: New York 09:00-14:30; DAX: Frankfurt 09:00-17:30; NIKKEI: Tokyo 09:00-15:00; ASX: Sydney 10:00-16:00; FX, XAUUSD, XAGUSD: London 08:00-17:00.

## Cells (4)
1. **B1 opening-range breakout:** box = mid high/low of the first 30 minutes of the session; first M5 close outside the box between open+30 min and close-60 min -> trade the break; stop = the other side of the box; exit at the session close.
2. **B2 Asian-range breakout** (FX and metals): range = 00:00-07:00 London; first M5 close outside it between 07:00 and 12:00 London -> trade the break; stop = the other side of the range; exit 17:00 London.
3. **B3 Bollinger squeeze breakout** (H1 bars on the server clock, hours 23 and 0 excluded): Bollinger(20, 2) on H1 mid closes; squeeze = band width at its lowest of the last 120 H1 bars; the H1 bar after a squeeze bar closes outside a band -> trade the break at the next H1 bar; stop 1.5 x ATR(14, H1); exit 12 H1 bars later.
4. **B4 previous-day high/low breakout:** the day opens (01:05 server mid) inside the previous server day's range; first M5 close (server clock) above its high / below its low between 09:00 and 20:00 server -> trade the break; stop = 25% of the previous day's range back inside from the broken level; exit 22:55 server.
P&L in R with real bid/ask (net); gross (mid) R, win rate and median reported.

## Periods and gates
DEV 2022-01..2024-12, VAL 2025, HOLD 2026-01..09 (sealed; one look only for a passing cell). Daily portfolio series, Newey-West t lag 1.
1. DEV mean net >= +0.05 R and t >= 2.50 (Bonferroni, 4 cells).  2. VAL mean net > 0 and t >= 1.65.  3. Net positive in at least 3 of 4 years.
4. Placebo (seeds 71-73): every real trade re-entered at a random minute of the same entry window on a random other day of the same period and market (B3: a random H1 bar), same side, same stop distance as a share of price, same exit rule; the real DEV t must exceed the 95th percentile of the 12 placebo DEV t.
5. No single market makes more than 40% of the DEV net R. By-class and by-market tables reported (indices B1 = the Zarattini et al. 2023 QQQ opening-range result, checked here on MT5 broker's NSDQ/SP/DOW).

## Honest prior
About 5%: breakouts are the strategy family with the best published record (trend premium, the QQQ opening-range paper), but every intraday breakout tested here so far was at or below cost.
