# PREREG_SWEEP36: a sweep reversal with the trader's confirmation, on all MT5 broker (written 20 Oct 2026, local clock; before any result)

Origin: the trader's second kind of setup (30 Apr 2025 08:04 Buy; `MANUAL_WHY_ENTRIES.md`): a sweep of a recent low (or high) followed by a confirmation in the reversal direction, in his words "either a gap in the reversal direction, or a significant displacement candle (BOS)". On his 8 sweep entries the confirmation came 0-5 minutes AFTER his entry and waiting did not change the outcomes (n 8, descriptive, `MANUAL_SWEEP_CONFIRM_OUTPUT.txt`). The open question is whether a confirmed sweep reversal, taken mechanically on EVERY sweep (not only the ones he took), has an edge. Honest note: the idea comes from an in-sample look at his entries; no parameter below was chosen or tuned on them. Mechanical test only: it says nothing about his discretion.

## Data and periods
MT5 broker M1 bid / ask for all 46 markets (`forex/data_mt5`), DEV 2022-01-01..2024-12-31, VAL 2025-01-01..2025-12-31. Nothing after 2025-12-31 is ever loaded (the sealed 2026 days stay sealed, as in EMA1000). Server clock = local + 2 h; sessions: London 08:00 local, NY 09:30 New York (`ema12_test.open_min`).

## Rules (all fixed now)
- **Candle series:** 1-minute mid candles (open / high / low / close of (bid + ask) / 2); ATR = the mean high-low range of the prior 14 candles (lagged one candle).
- **Window:** candles k whose open lies in the first 30 minutes after the session open. One trade per day, session and market: the first candle k that gives a signal; if a buy and a sell signal appear on the same candle, no trade.
- **Sweep (buy side):** in the 10 candles k-9..k the lowest low is below the lowest low of the L candles before them (k-9-L..k-10). Sell side: the same with highs. L is a variant axis.
- **Confirmation at candle k, in the reversal direction:** GAP = low[k] > high[k-2] (buy) or high[k] < low[k-2] (sell); DISP = a displacement candle: body >= 1.0 x ATR in the trade direction AND the close beyond the extreme of the previous 5 candles (a break of structure): close > the highest high of k-5..k-1 (buy) or < the lowest low of k-5..k-1 (sell). The confirmation mode is a variant axis: gap, disp, or either.
- **Entry:** at the open quote of candle k+1 (a buy at the ask, a sell at the bid), a market order, lag 1.
- **Stop:** at the sweep extreme: the lowest low (buy) or highest high (sell) of the 10 candles k-9..k, mid-based. If the stop is not at least 0.2 ATR from the entry price (or on the wrong side), no trade.
- **Target:** entry + trade side x m x stop distance, m a variant axis (0.5, 1.0, 2.0); m = 0.5 is the shape of the trader's trades.
- **Exits:** a long stops when the bid low <= stop and reaches the target when the bid high >= target; a short with the ask high / ask low; same-minute stop + target = loss; at most 60 candles from the entry minute, then closed at the exit-side close. R = P&L / stop distance.
- **Variants (36, own count):** L in {30, 60} x confirmation in {gap, disp, either} x m in {0.5, 1.0, 2.0} x session in {London, NY}.

## Descriptive extras (never a bar)
(a) the same entries on the inverted side (opposite direction, same stop and target distances) and the skill (rule minus inverted) / 2; (b) a CONTROL without the sweep requirement (confirmation only), to see whether the sweep adds anything; (c) a no-spread (mid prices) version as a ceiling; (d) XAUUSD alone and XAUUSD + NSDQ; (e) per-market medians; (f) the mean R split by confirmation type.

## Bars (candidate = all of them, real bid / ask)
Pooled over the 46 markets per variant, day-clustered t: DEV n >= 3,000 trades, DEV mean R >= +0.03, DEV t >= 2.77 (one-sided Bonferroni 0.1 / 36); VAL mean R > 0 and t >= 1.65; every DEV year mean R > 0; the best market removed: mean R > 0 and t >= 2.5. A candidate would only earn one look at the 2026 hold-out, with the trader's OK; no candidate = nothing goes near the account and the hold-out stays sealed.

## Checks before the run (dry run, no P&L)
Truncation test (data after the entry minute cut: same signal and entry), hand check of printed trades including the 30 Apr 2025 London case (expected: a buy confirmed at 08:09 by a displacement candle, entry 08:10), trades per year, 36 variants counted.

## Honest prior
About 3% that any variant passes: 2,044 mechanical trials of the 12 EMA family on MT5 broker prices gave 0 passes and a random-side drag of 0.18 R; here the stop sits at the sweep extreme (several ATR away) so the spread is a smaller share of the stop than in EMA1000, which is the one reason this test is less handicapped; no direction skill is expected.
