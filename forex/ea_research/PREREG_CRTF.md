# Pre-registration CRTF: Candle Range Theory traded as in reel 12 (written 2026-10-14 ~22:35, before any code or result)
the trader on `CRT_RESULT.md`: "you're not backtesting it right". Correct on three points: CRT is not entered blindly at the next day's open. As drawn in reel 12 and as CRT is taught: (1) after the daily CRT forms, the entry comes from the lower timeframe inside candle 3 (a manipulation sweep of the session range, then a market structure shift, stop under the manipulation low, target the other end of candle 1); (2) the sweep should happen at a higher-timeframe key level; (3) the 4H "1am-5am-9am New York" CRT model is the other standard form. CRT_RESULT stays on the record (the daily formation itself: gross zero); this round tests the full model. Counted together: 5 CRT variants in this window.

## Data and execution
MT5 broker M1 bid/ask, 46 markets, data before 2026-01-01 (2026 sealed). Daily candles as in `PREREG_CRT.md` (server day, bars 01:00-22:59). M5 pattern bars on the New York clock from M1 mid with true highs/lows (as in ICT2). Killzones London 02:00-05:00 NY, NY AM 07:00-10:00 NY. Market entries at the open of the minute after the signal (server minute :00 -> :01), long at the ask / exits at the bid (short mirrored), stop first if both in one minute, gapped stops at the open. Stop distance at least 2 spreads.

## Cells (3)
1. **F1 = daily CRT + LTF entry.** Candles 1/2 as in CRT (bullish: candle 2 trades below candle 1's low, closes back inside, high not above candle 1's high; bearish mirror). On candle 3 (next server day), in the London killzone, then (if nothing fired) the NY AM killzone: the session range = mid low (bullish) from 01:00 server to the killzone start. Manipulation = the first M5 bar of the killzone trading below that range low. Structure shift = within the next 24 M5 bars, the first M5 close above the highest high of the 6 M5 bars before the manipulation bar. Entry long at the next minute; stop = the lowest low from the manipulation bar to the shift bar; target = candle 1's high; only if the target is at least 1R away. The setup is void for the day if price trades below candle 2's low first. Exit at 22:55 server of candle 3 at the latest. Bearish mirror. One trade per CRT.
2. **F2 = F1 + key level:** candle 2's sweep also takes the previous server week's low (bullish) / high (bearish) - higher-timeframe liquidity.
3. **F3 = 4H CRT 1am-5am-9am NY:** candle 1 = 01:00-05:00 NY, candle 2 = 05:00-09:00 NY (sweeps candle 1's low and closes back inside, high not above candle 1's high; bearish mirror); entry at 09:00 NY (09:01 by the first-minute rule); stop = candle 2's extreme; target = candle 1's other extreme; exit at 13:00 NY at the latest.
P&L in R with real bid/ask (net); gross (mid) R, win rate and median R reported.

## Periods and gates
DEV 2022-01..2024-12, VAL 2025, HOLD 2026-01..09 (sealed; one look only for a passing cell). Daily portfolio series, Newey-West t lag 1.
1. DEV mean net >= +0.05 R and t >= 2.40 (Bonferroni, 3 cells).  2. VAL mean net > 0 and t >= 1.65.  3. Net positive in at least 3 of 4 years.
4. Placebo (seeds 61-63): F1/F2 - the same LTF trigger run on a random other day of the same period and market in the same direction (candle-2 low replaced by the previous day's low), target at the same distance as a share of price, up to 5 draws to find a day where the trigger fires; F3 - entry at 09:01 NY on a random day, same side and stop/target distances. The real DEV t must exceed the 95th percentile of the 9 placebo DEV t (this asks whether the CRT context adds anything to the trigger).
5. No single market makes more than 40% of the DEV net R. XAUUSD reported alone.

## Honest prior
About 4%: the trigger is a session sweep + structure shift (its parts lost alone: SWEEP_ASIA, MSS2022) and the daily CRT formation is gross zero; the combination and the key-level filter are what is new.
