# Pre-registration UTBOT: UT Bot Alerts (Pine v4) on every MT5 broker symbol and every intraday timeframe (written 2026-10-14 before any run)
the trader's idea: a TradingView script "UT Bot Alerts" that gives buy/sell signals; "backtest it on every intraday timeframe on every single symbol". Source pasted by the trader (ATR trailing-stop flip, defaults a = 1, ATR period c = 10, Heikin Ashi OFF).

## Faithful port (checked against the Pine text)
src = close; xATR = RMA(true range, 10) (Pine atr, Wilder; implemented as EWM alpha 1/10 without a seeded SMA, a difference only in the first ~50 bars); nLoss = a x xATR.
Trailing stop ts[i]: if src > ts[i-1] and src[i-1] > ts[i-1]: max(ts[i-1], src - nLoss); elif src < ts[i-1] and src[i-1] < ts[i-1]: min(ts[i-1], src + nLoss); elif src > ts[i-1]: src - nLoss; else src + nLoss (ts[-1] = 0).
buy = src > ts and crossover(src, ts) (src > ts[i] and src[i-1] <= ts[i-1]); sell = src < ts and crossover(ts, src) (ts[i] > src and ts[i-1] <= src[i-1]). ema(src, 1) = src.
Signals are known at the close of bar i (the alert fires on bar close; no repainting: no security() call with lookahead, Heikin Ashi off).
## Execution (the script has no exit of its own)
Stop-and-reverse: always in the market after the first signal: long after a buy until the next sell and vice versa (a same-side repeat is ignored). Order at the OPEN of the first bar after the signal bar whose open is not in server hours 23 or 0 (rollover rule; a flip in that window waits for the hour-1 bar), long entry/short exit at the ask, short entry/long exit at the bid (MT5 broker M1 bid/ask resampled), no commission (account <acct> pays none), no swap (swap-free), 1 unit notional per trade, trade return in bp. The last open trade of a period is dropped. Signals use mid OHLC.
## Universe and grid
All 46 symbols with MT5 broker M1 files (`forex/data_mt5/*_M1_rates.parquet`, 2021-12-01 .. 2026-10-02; XAUUSD tick file excluded) x 8 timeframes M1, M3, M5, M15, M30, H1, H2, H4 (bars aligned to the server day) = up to 368 cells. One parameter set only (the defaults); variants (Key Value 2/3, Heikin Ashi) are NOT part of this test and are not run.
## Periods and gates
DEV 2021-12-01..2023-12-31, VAL 2024-01-01..2025-12-31, HOLD 2026-01-01.. (never loaded unless `--hold`). A trade belongs to the period of its exit.
Per-trade statistics (sequential trades do not overlap): mean net bp, t = mean / (sd / sqrt n), hit rate, trades, total net return. Yardstick: buy-and-hold net of one spread, reported per symbol.
Multiple testing (368 cells): a cell is a CANDIDATE if DEV mean net > 0 with t >= 3.8 (two-sided 5% / 368) and n >= 100 trades, AND VAL mean > 0 with t >= 1.65 and n >= 50, AND the DEV t exceeds the 95th percentile of the placebo maximum t over all cells (100 draws, each cell's signal series circularly shifted by a random offset of at least 5 days against the price, positions rebuilt). A candidate is audited (year by year, hour of day, spread paid, 1-bar latency, long vs short legs, drift vs buy-and-hold) before any claim and only then is the 2026 HOLD opened once.
Reported not gated: the fraction of cells with positive net in DEV and VAL (a no-skill system should be well below half after spreads), best cells per symbol and per timeframe.
Honest prior: a published ATR trailing-stop flip is a trend follower with a spread cost per flip; I expect most intraday cells to lose to spreads and a few to look good by chance. Kill rule: no variants after the run.
