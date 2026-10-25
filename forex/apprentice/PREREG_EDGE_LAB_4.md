# PREREG_EDGE_LAB_4: the trader's "STDV PO3 - Optimised" London-only indicator, every market and timeframe available

Written 25 Oct 2026 (local clock) BEFORE any result was computed. the trader: "run all runs you can". The rules are the Pine script saved in TradingView after the London-only edit (backup of the original in `pine_backups/`). Because many runs are tested, the hold-out stays sealed and the bar is stricter.

## The strategy (exactly as coded)
- Signal bar close crosses above the highest high (below the lowest low) of the previous 20 bars, with volume > 1.3 x SMA(20) volume and a candle in the same direction, RSI(14) in 55-72 (long) or 28-45 (short), close on the right side of EMA(50), range >= 0.8 x ATR(14) (Wilder), cooldown 30 minutes since the last trade, one trade at a time.
- Sessions on LONDON local time (Europe/London, DST-aware): entries only for bars opening 08:00-15:29, open trades closed at the OPEN of the first bar after 16:00.
- Entry = signal bar close. Long: stop = the 20-bar low, target = the 20-bar high + range. Short mirrored. Stop first if both are hit in one bar; the signal bar itself is not scored.
- R gross = (exit - entry) x side / risk, exactly like the indicator. R net also subtracts costs: 1 tick of slippage per side plus USD 1.20 round-trip commission per micro contract (point values per micro: ES 5, NQ 2, GC 10, SI 1000; tick: ES 0.25, NQ 0.25, GC 0.1, SI 0.005).

## Runs
Markets with long 1-minute history: ES, NQ, GC, SI (Databento continuous front month, 2019-06 to 2026-09). Timeframes: 1, 3, 5, 10, 15 minutes (resampled from 1m). That is 20 runs. Micro Dow (the chart the trader is looking at) has only about three months of 1-minute data, so it cannot be tested meaningfully.

## Split and rule
DEV = trades entered 2019-06-19 to 2023-12-31. HOLD-OUT 2024-01-01 to 2026-09-25 stays SEALED for this strategy (it may be opened once, for one finalist). Mirror baseline and random-side P as in the earlier batches. Tested so far including this batch: 11 + 20 = 31, so Bonferroni alpha = 0.05 / 31 = 0.0016.
Finalist on DEV: at least 100 trades AND mean R NET >= +0.10 AND random-side P <= 0.0016 AND mean R net > 0 in at least 3 of the 4 calendar years 2020-2023. None = "no edge for this strategy on any market / timeframe tested".

## Honest limits
Continuous front-month series, idealised fills, signals on resampled bars. With 20 runs, a few will look good by luck; only the pre-registered rule counts.
