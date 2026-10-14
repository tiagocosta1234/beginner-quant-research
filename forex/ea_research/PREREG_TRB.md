# Pre-registration TRB: time-range breakout with the selection process of reel 13 (written 2026-10-14 ~23:05, before any code or result)
Source: reel 13 (`reels/13_breakout_lesson/`, NQ futures trader, transcript in `transcrito.txt`): pick a time of day with consistent volatility spikes; mark the high/low of a short box (5-30 min, on 5/30-minute candle boundaries); place a buy stop at the high and a sell stop at the low, whichever fills first is the trade; fixed take-profit / stop; "track every R:R", choose the best set on the last 3 months, choose between the top two on 6 months, trade the winner live; long-only or short-only if the data says so. BRK (`BREAKOUTS_RESULT.md`) tested one fixed opening-range rule; the new element here is his data-driven selection, which this round runs causally (walk-forward), exactly as a trader following the video would, month by month.

## Data and orders
MT5 broker M1 bid/ask, 46 markets, server clock, data before 2026-01-01 (2026 sealed). Mid = (bid + ask) / 2.
- Box start times T every 30 minutes from 01:00 to 20:00 server (39 slots); box lengths L in {5, 15, 30} min; box = mid high/low of the M1 bars in [T, T+L); range = high - low.
- Orders live from T+L to T+L+120 min: buy stop at the box high (fills when the ask reaches it, at the level or at the minute's ask open if beyond), sell stop at the box low (bid). Minute :00 bars do not trigger (first-minute rule). Modes: BOTH (one-cancels-other; both in one minute = no trade), LONG only, SHORT only.
- Exit: stop SL x range, target TP x range, SL in {0.5, 1.0}, TP in {0.5, 1, 2, 3} (8 sets, including the "negative R" 1:0.5 the video mentions); time exit 240 min after the box ends, capped at 22:55 server. Stop checked on the executable side, stop first if both in a minute, gapped stop at the open. No trade if the stop is closer than 2 spreads.
- 39 x 3 x 3 x 8 = 2,808 configurations per market, all simulated on every day.

## The selection process (walk-forward, causal; one configuration per market per month)
For month m (first m = 2022-07): volatility of a slot = mean |mid(T+15 min) / mid(T) - 1| over the previous 3 months; candidates = configurations whose slot is one of the 4 most volatile; top two candidates by total R over the previous 3 months (at least 15 trades); the one with the higher total R over the previous 6 months is traded during month m.
## Cells and periods
W1 = the process on all 46 markets; W2 = the process on the equity indices SP, NSDQ, DOW, DAX (his market). DEV 2022-07..2024-12, VAL 2025, HOLD 2026-01..09 (sealed; one look only for a passing cell).
## Statistics and gates
Daily portfolio series of the walk-forward trades (mean net R per day), Newey-West t lag 1.
1. DEV mean net >= +0.05 R and t >= 2.24 (Bonferroni, 2 cells).  2. VAL mean net > 0, t >= 1.65.  3. Net positive in at least 3 of the 4 years 2022H2-2025.
4. Placebo (seeds 81-83): each month a RANDOM configuration from the same candidate set instead of the selected one; the real DEV t must exceed the 95th percentile of the 6 placebo DEV t (does the selection add anything over picking at random?).
5. No single market more than 40% of the DEV net R (W1).
Reported: the in-sample illusion (average trailing-3-month R per trade of the selected configurations, i.e. what his backtest shows, against the R they earn the next month), by market, long/short split.

## Honest prior
About 3%: selecting the best of hundreds of configurations on 3 months of data is the classic recipe for picking noise; the opening-range rule behind it was +0.035 R on indices in BRK (t 1.6).
