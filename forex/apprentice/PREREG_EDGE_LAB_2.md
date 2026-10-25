# PREREG_EDGE_LAB_2: six slower gold-futures ideas (lower cost drag), same sealed hold-out

Written 25 Oct 2026 (local clock) BEFORE any result of these six ideas was computed. Batch 1 (`PREREG_EDGE_LAB_1.md`) found no finalist on DEV (all four intraday ideas lost about 0.1-0.2 R net, random-side P 0.57-0.91); its hold-out was never opened. the trader: "lets go". Claude chose the ideas.

## Why these
Batch 1 lost mostly to costs on 1.5-3 point stops (about 0.1-0.16 R a trade). Here every stop is at least 3 points (rule below) and most are 10+ points, so costs fall to roughly 0.02-0.07 R. These are textbook ideas, picked before any look at the data.

## Data, split, costs
- Same Databento GC.F 1-minute series, aggregated to bars on the Chicago/New York trade-day clock: daily bars run 17:00 ET to 17:00 ET (day id = (ET-naive epoch + 7 h) // 1 day); 4-hour bars start 17,21,01,05,09,13 ET; 1-hour bars on ET hours.
- **DEV** = 2019-06-19 to 2023-12-31 (dated by the entry bar). **HOLD-OUT** = 2024-01-01 to 2026-09-25, still sealed (batch 1 never opened it). It may be opened ONCE per finalist, and only after the DEV rule below picks a finalist.
- Entry at the close of the signal bar +/- 0.1 point slippage against; stop exits at the stop -/+ 0.1 point (gap: at the open); market-type exits at the bar close -/+ 0.1 point; targets need 0.1 point of trade-through; same-bar stop and target counts as a stop. Commission USD 1.20 round trip per micro: R cost = 1.2 / (risk points x 10). R net = (exit - entry) x side / risk - commission R. Stops/targets are checked on the BAR high/low of the idea's own timeframe.
- Risk = the stop distance in points. **A signal whose risk is under 3.0 points is skipped** (stay flat). One position at a time per idea; no signal while in a position (EMA_CROSS_H1 flips at the exit bar).

## The six ideas (all parameters fixed here)
ATR(14) = simple mean of the last 14 true ranges on the idea's timeframe, measured at the signal bar.
1. **DONCHIAN_H4.** 4-hour bars. Long if the close > highest high of the previous 20 bars; short if the close < lowest low of the previous 20. Stop = entry -/+ 2 x ATR. Exit at a bar close beyond the previous 10-bar opposite channel (long: close < lowest low of the previous 10; short: close > highest high of the previous 10), or the stop, or after 120 bars.
2. **DONCHIAN_D.** Same on daily bars: 20-day entry, 10-day exit, stop 2 x ATR, maximum 60 bars.
3. **TSMOM_D.** Daily bars, weekly. On each Friday's daily bar close: side = sign of (close / close 60 bars earlier - 1); stop 2 x ATR; exit at the next Friday's daily close (or the stop); maximum 8 bars.
4. **EMA_CROSS_H1.** 1-hour bars. EMA20 crosses above (below) EMA50 = long (short) at that bar's close; stop 3 x ATR; exit and flip at the opposite cross (at its bar close), or the stop; maximum 400 bars.
5. **H1_PULLBACK.** 1-hour bars. Long trend = close > EMA50 and EMA50 > EMA50 five bars earlier; short trend = the reverse. Signal = a bar in the trend whose low (high) touches EMA20 and closes back beyond it in the trend direction (close > open for longs, close < open for shorts). Stop = lowest low (highest high) of the last 3 bars -/+ 0.1 point. Target = entry +/- 2 x risk. Time exit after 24 bars.
6. **RSI2_D.** Daily bars, RSI(2) with Wilder smoothing (alpha 0.5), SMA(200). Long if RSI2 < 10 and close > SMA200; short if RSI2 > 90 and close < SMA200. Stop 3 x ATR. Exit at a close with RSI2 > 70 (long) or < 30 (short), or the stop, or after 10 bars.

## Direction skill, not drift
Each trade also gets a mirror: same entry bar, same exit bar, opposite side, stop at the same distance on the other side (and for idea 5 the mirrored 2R target). Random-side P = share of 20,000 draws (each trade independently actual or mirror) whose mean R is at least the actual mean. Gold's 2024-2026 uptrend therefore cannot pass by itself.

## Finalist rule (DEV only; 10 ideas tested in total, Bonferroni alpha 0.05 / 10 = 0.005)
All must hold on DEV: at least 40 trades; mean R net >= +0.20; random-side P <= 0.005; mean R net > 0 in at least 3 of the 4 calendar years 2020-2023 (a year with fewer than 3 trades counts as not positive). If none qualifies, the hold-out stays sealed and the verdict is "none of these ten ideas has an edge".

## Hold-out rule (one look per finalist)
At least 25 trades AND mean R net >= +0.15 AND random-side P <= 0.05 AND mean R net >= 0 for longs and for shorts when each has at least 10 trades. Otherwise fail, no re-tuning. A pass is evidence, not proof: it would still need a forward demo gate before any purchase.

## Honest limits
Slow ideas trade rarely, so DEV has few trades and low power: a real but small edge can be missed, and a lucky one can pass. Continuous front-month series (roll jumps), idealised fills, a single instrument. Nothing here promises a withdrawal.
