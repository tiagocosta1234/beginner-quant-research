# PREREG_DISP24: a displacement candle in the first 15 minutes, stop at the candle's extreme, on all MT5 broker (written 20 Oct 2026, local clock; before any result)

Origin: the trader's walk-through of his own entries (`MANUAL_WHY_ENTRIES.md`, 20 Oct): trade 4 (5 May 2025 08:08 Buy) "comes purely from the great displacement on the candle close"; trade 6 (28 Jan 2026 08:01 Buy) had its stop "on the entry's candle since it was inside a rejection block, kind of making it a protected low"; he defines a strong candle as good displacement with a body bigger than the sum of the wicks and a really small wick on the close side; BOS and the EMA are context; he says he will keep testing the first 15 minutes of the session. Every earlier mechanical test of his setup started from an EMA cross (EMA1000, MANUALRULE, EMA12) or a sweep (SWEEP36): none started from the displacement candle itself, which is what he says the trigger is. Mechanical test only: it says nothing about his discretion (which day, which block, the bias). Honest note: the definition of 'displacement' below comes from his words and the values of the candles he showed (body 1.0-1.4 ATR, close-side wick 2-13% of the body), not from tuning on any result; nothing was run before this file.

## Data and periods
MT5 broker M1 bid / ask for all 46 markets (`forex/data_mt5`), DEV 2022-01-01..2024-12-31, VAL 2025-01-01..2025-12-31. Nothing after 2025-12-31 is ever loaded (the sealed 2026 days stay sealed). Server clock = local + 2 h; sessions: London 08:00 local, NY 09:30 New York (`ema12_test.open_min`, as in EMA1000 / SWEEP36).

## Rules (all fixed now)
- **Candles:** 1-minute mid candles (open / high / low / close of (bid + ask) / 2); ATR = mean high-low range of the prior 14 candles (lagged one candle).
- **Window:** candles whose open lies in the first 15 minutes after the session open (15 candles). One trade per day, session and market: the first candle that gives a signal.
- **Displacement candle (buy):** close > open; body (close - open) >= 1.0 x ATR; upper wick (high - close) <= 0.15 x body; body > (upper wick + lower wick). Sell: mirrored (open - close >= 1.0 x ATR, lower wick (close - low) <= 0.15 x body, body > sum of the wicks).
- **BOS (variant axis):** required = the close is above the highest high of the previous 5 candles (buy) or below the lowest low of the previous 5 candles (sell); none = not required.
- **EMA context (variant axis):** EMA12 of the 1-minute mid close (ewm span 12, adjust False, whole series). none = no condition; near = the EMA lies between (low - 0.25 x ATR) and (high + 0.25 x ATR) of the signal candle.
- **Entry:** at the open quote of the next candle (a buy at the ask, a sell at the bid), a market order, lag 1; no trade if the next candle is more than 2 minutes after the signal candle.
- **Stop:** at the signal candle's low (buy) or high (sell), mid-based ('protected low'). No trade if the stop is not at least 0.2 ATR from the entry price or is on the wrong side.
- **Target:** entry + trade side x m x stop distance, m a variant axis (0.53 = his habit, 1.0, 2.0).
- **Exits:** a long stops when the bid low <= stop and reaches the target when the bid high >= target; a short with the ask high / ask low; same-minute stop + target = loss; at most 60 candles from the entry minute, then closed at the exit-side close. R = P&L / stop distance.
- **Variants (24, own count):** BOS in {required, none} x EMA in {none, near} x m in {0.53, 1.0, 2.0} x session in {London, NY}.

## Descriptive extras (never a bar)
(a) the same entries on the inverted side (opposite direction, same stop and target distances) and the skill (rule minus inverted) / 2; (b) a CONTROL with only 'body >= 1.0 x ATR' (no close-wick limit, no body-over-wicks rule, no BOS, no EMA condition; same stop, target and entry), to see whether his candle-quality rules add anything; (c) a no-spread (mid prices) version of the rule and of the control as a ceiling; (d) XAUUSD alone and XAUUSD + NSDQ; (e) per-market medians; (f) coverage of his own April-May 2025 trades (29 in DEV / VAL range): on how many of his days the rule (BOS none, EMA none) fires, on the same side, on the same candle.

## Bars (candidate = all of them, real bid / ask)
Pooled over the 46 markets per variant, day-clustered t: DEV n >= 3,000 trades, DEV mean R >= +0.03, DEV t >= 2.64 (one-sided Bonferroni 0.1 / 24); VAL mean R > 0 and t >= 1.65; every DEV year mean R > 0; the best market removed: mean R > 0 and t >= 2.5. A candidate would only earn one look at the 2026 hold-out, with the trader's OK; no candidate = nothing goes near the account and the hold-out stays sealed.

## Checks before the run (dry run, no P&L)
Truncation test (data after the entry minute cut: same signal, same entry and stop), hand check of printed trades on his candles of 5 May 2025 (London, wickless buy at 08:08) and 28 Apr - 1 May 2025, trades per year, 24 variants counted.

## Honest prior
About 3% that any variant passes. The 12 EMA family (2,044 mechanical trials on MT5 broker prices, then the same 1,000 variants re-run with no spread, limit entries and pullbacks) and SWEEP36 (36 variants) all lost to the spread (0.18-0.22 R a trade) with no direction skill; here the stop sits at the candle extreme, which is at least one ATR away, so the spread is a smaller share of R than in EMA1000, the same one reason SWEEP36 gave, and SWEEP36 still lost 0.22 R. If this also fails, the mechanical question about his stated trigger is closed in all its forms and only the blind replay and the forward log can say anything about his edge.
