# Pre-registration CRT: Candle Range Theory on the daily candle, every MT5 broker market (written 2026-10-14 ~22:30, before any code or result)
Source: reel 12 ("XAUUSD x ALCHEMIST", `reels/12_xauusd_x_alchemist/NOTAS.md`): a day trades through the previous day's low (high), closes back inside its range, and the next candle is expected to reach the other side. Untested here: the ICT scan's SWEEP_PD used an M15 sweep in the New York morning with a 2R target, not a DAILY close back inside with the opposite end of the range as the target.

## Data and rules
MT5 broker M1 bid/ask, 46 markets, server clock, data loaded only before 2026-01-01 (2026 sealed). Daily candle of a server day = mid prices of the bars 01:00-22:59 (rollover hours 23 and 0 excluded); close = mid close of the last bar before 23:00.
- Candle 1 = previous day with at least 300 bars: range [L1, H1]. Candle 2 = day D.
- **Bullish CRT:** low(D) < L1 and L1 < close(D) < H1, and high(D) <= H1. **Bearish:** high(D) > H1 and L1 < close(D) < H1, and low(D) >= L1. (An outside day = no trade.)
- Entry at 01:05 server of the next day with data (long at the ask / short at the bid; a missing 01:05 bar -> first bar after it within that hour, else no trade).
- Stop = the sweep extreme of day D (low(D) for longs, high(D) for shorts); target = the other end of candle 1 (H1 for longs, L1 for shorts). No trade if the entry is already beyond the target or the stop, or if the stop is closer than 2 spreads.
- Exits on the executable side minute by minute, stop first if both in one minute, gapped stops at the open.
**Cells (2):** CRT1 = exit at 22:55 server of the entry day at the latest (candle 3 only); CRT5 = held up to 22:55 server of the 5th trading day (weekends held; MT5 broker swap-free).
P&L in R with real bid/ask (net); gross (mid) R reported next to it.

## Periods and gates
DEV 2022-01..2024-12, VAL 2025, HOLD 2026-01..09 (sealed; one look only for a cell that passes 1-5). Daily portfolio series = mean net R of the trades entered that day; Newey-West t, lag 1 (lag 5 for CRT5).
1. DEV mean net >= +0.05 R and t >= 2.24 (Bonferroni, 2 one-sided cells).  2. VAL mean net > 0 and t >= 1.65.  3. Net positive in at least 3 of the 4 years 2022-2025.
4. Placebo (3 worlds, seeds 51-53): every real trade re-entered at 01:05 server of a random other day of the same period and market, same side, same stop and target distances as shares of price, same exit rule; the real DEV t must exceed the 95th percentile of the 6 placebo DEV t.
5. No single market makes more than 40% of the DEV net R. Gold (XAUUSD) reported on its own, not gated.

## Honest prior
About 4%: the intraday version of the same idea (sweep and close back) lost on every asset class; a daily close back inside is a slower, cleaner version of it.
