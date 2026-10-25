# PREREG_EDGE_LAB_5: London first-15m candle, 1:1, one trade EVERY day

Written 25 Oct 2026 (local clock) BEFORE any result was computed. the trader: "1 trade per day minimum, and things that increase the chances of hitting TP; then which symbols and timeframes".

## Base trade (every trading day, nothing is skipped)
- Candle = 08:00-08:15 London time (DST-aware), built from 1-minute data. Entry = the candle close (08:15). Target = exactly 1R. Time exit at the open of the first bar at or after 16:00 London. Stop first if stop and target are in the same bar.
- Stop = the opposite end of the candle plus a buffer. Risk floor: if the candle range is below 0.03 x prior-day ATR(14) of daily bars, the risk is raised to that floor (so tiny candles are still tradeable and costs do not explode).
- Costs: 1 tick slippage per side + USD 1.20 round-trip commission per micro (ES 5, NQ 2, GC 10, SI 1000 USD per point; tick 0.25, 0.25, 0.1, 0.005).

## Variants (8 per market, 32 runs; Bonferroni with the 31 earlier ideas: alpha = 0.05 / 63 = 0.0008)
Direction rule x stop buffer.
- D1 follow the candle (close above open = long). Doji: follow the daily trend rule D2.
- D2 daily trend: long if the prior daily close is above the mean of the last 20 daily closes, else short.
- D3 prior-day continuation: long if the prior day closed above its open, else short.
- D4 Asia drift: long if the 08:00 open is above the 00:00 UTC open of the same day, else short.
- B0 stop buffer 0. B1 stop buffer = 0.5 x candle range beyond the extreme (a wider stop, bigger target).
Why these: the only ways to raise the chance of a 1:1 target are a better direction call (D1-D4) or lowering how much cost eats the 1R (wider stop, B1). A wider stop does not change the win chance of a driftless market.

## Timeframe question
The candle is always the 15-minute one. The chart timeframe only decides how finely stop and target are resolved. For the best variant per market I also report exits resolved on 1m, 3m, 5m and 15m bars (coarser bars are more pessimistic because stop wins ties).

## Split and rule
DEV = 2019-06-19 to 2023-12-31 (about 1,100 days per market). HOLD-OUT 2024-01-01 to 2026-09-25 sealed. Mirror baseline: each trade's side flipped (same stop and target distances), random-side P from 20,000 draws as before.
Finalist: n >= 800 AND mean R net >= +0.05 AND random-side P <= 0.0008 AND mean R net > 0 in at least 3 of 4 calendar years 2020-2023. Anything that passes is opened ONCE on the hold-out; anything that does not pass is reported as no edge. Filter defaults in the indicator are chosen from this table only if a finalist exists; otherwise the indicator ships the variant with the best DEV result and says plainly that it is not validated.
