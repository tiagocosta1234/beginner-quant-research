# Pre-registration: the trader's Fibonacci 79% + order-block idea on MT5 broker's Nasdaq, causal version (family FO) (written 2026-10-12, before any MT5 broker trade of it was computed)

the trader: "backtest this strategy idea: macro-trading-lab/fib_retrac_backtest.py". Read before running. Idea: long only on MNQ; 15 m chart; entry at the 79% fib of the last 20 bars' range (high - 0.79 x range) when that level sits inside the latest bullish order block (a down candle whose NEXT candle closes above its open); stop = the 20-bar low; target = the latest 1 h swing high (high above the 2 bars before and after); sessions New York 09:30-16:00 or Tokyo 19:00-02:00 (NY clock); no entries in the 09:45 / 10:00 / 13:45 / 14:00 bars; forced exit at the 15:45 and 01:45 bar close; one position.
Run as written on Yahoo (`period=60d`, 3 MNQ contracts): 2026-08-03 .. 2026-10-12, 76 trades, +13,997 USD, PF 2.72, win 52.6%, average planned reward:risk 4.88.

## Why that number cannot be trusted (declared lookahead in the script)
(1) the order block is detected with `Close.shift(-1)` (the NEXT candle) and attached to the candle itself; (2) the 1 h swing high needs the two FOLLOWING hourly bars, yet is used from the swing bar onwards; (3) entry needs `Low <= fib < Close`, i.e. knowing how the bar closes, and fills at the fib price inside the bar; (4) only 60 days of data (about 12 weeks of intraday trades) and one regime.

## Test on MT5 broker data (NSDQ, the cash index CFD that stands in for MNQ), causal
MT5 broker M1 bid/ask (`data_mt5`, 2021-12 .. 2026-10-02). 15 m and 1 h bars built from M1 on the server clock (epoch buckets; sessions via New York time). Bid high = max(bid-open, bid-close) of each minute (the M1 data has no high column; small underestimate of highs, declared). Costs: entries at the ask, exits at the bid (spread paid). No lookahead:
- the order block of bar k is usable only from the bar after k+1 (known when k+1 closes);
- a 1 h swing high is usable only after the second following hourly bar has closed;
- the 20-bar range uses the bars BEFORE the signal bar (not the current one).
Two variants, each a trial:
- **FO1 limit order**: a resting buy limit at the 79% fib (computed on prior bars, OB zone and swing already known, sessions and embargo as above) fills when the bar's ask-low reaches it (fill at min(fib, ask-open)); no `Close > fib` condition. If the same bar's low also reaches the stop, the trade is stopped at once; target hits are checked from the next bar on. Exits from the bar after the fill: forced exit at the close of the 15:45 / 01:45 bars, then stop (a gap through it exits at the open), then target (gap above exits at the open), in that order (stop before target when both).
- **FO2 confirmed**: signal on a closed bar with `Low <= fib < Close` (fib from the prior 20 bars) and fib inside the known OB; enter at the NEXT bar's ASK-open (stop = prior-20 low, target = swing known then; skipped if the entry is not between stop and target); same exit rules.
Result per trade: R = (exit - entry) / (entry - stop); also USD at 500 risk per trade = 500 x R.

## Windows and acceptance (by entry date)
DEV 2022-01-01 .. 2024-12-31, VAL 2025, HOLD-OUT 2026-01-01 .. 2026-09-30 (one look, accepted variants only).
Accept: DEV >= 40 trades, mean R >= +0.15 after spread, PF(R) >= 1.3, one-sided t >= 1.65 (day-averaged); VAL mean R > 0; HOLD mean R > 0.
Reported: trades, win rate, planned reward:risk, mean R, total R, indicative USD at 500 per trade, by year; SP and DOW as a descriptive check (not trials).
A pass is a candidate only (EA build, MT5 broker tester with real ticks, correlation with the pair, pass-speed gate). Nothing goes live from this round.

## Honest prior
Low. The Yahoo result carries four lookaheads and 60 days; ICT-style order-block / fib entries are discretionary patterns that rarely survive a causal test and a spread. If anything survives it will be the limit-order variant with a large reward:risk (most trades lose 1R, winners pay 3-5R), which needs a high enough win rate; a win rate near 25% with RR 4.9 is breakeven before costs. Two trials (FO1, FO2).
