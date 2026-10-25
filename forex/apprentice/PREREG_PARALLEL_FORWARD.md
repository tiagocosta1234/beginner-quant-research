# PREREG_PARALLEL_FORWARD: London First 15m 1:1 indicator vs Claude's daily call, forward demo, 4 symbols

Written Sun 25 Oct 2026 (local clock, local = London) BEFORE the first test day. the trader: "lets backtest this indicator and you in parallel then, until how long?"

## Length
Mon 26 Oct to Fri 18 Dec 2026 = **40 trading days** (8 full weeks). Checkpoint Fri 6 Nov (10 days) = process check only, no go/no-go. Early stop only by the futility rule below.
Why 40: one observation per day (the average of the 4 symbols; they move together so they are not 4 independent samples). The assumed standard deviation of that daily average is 0.9R (replaced by the observed one at the end). At 40 days the standard error is about 0.14R, so the test has 80% power to see a true edge of about +0.35R or more (one-sided 5%). A true edge of +0.10R would need about 800 days. So this test can confirm a BIG edge or reject a big one; it cannot say anything about a small one. The 2019-2023 tests (PREREG_EDGE_LAB_5) point to about -0.04 to -0.17R net, so a pass would be a surprise.

## Track A: the indicator (mechanical)
File `LONDON_FIRST15_1TO1.pine` as saved in TradingView on 25 Oct 2026, settings frozen: direction rule Candle, stop buffer 0.5 x candle range, risk floor 0.03 x prior daily ATR, auto cost by symbol (round trip MGC 0.32, MNQ 1.1, MES 0.74, MYM 4.4 points = 1 tick slippage per side + USD 1.20 commission per micro), 1-minute chart, symbols MGC, MNQ, MES, MYM. Any change to these = the test restarts from day 1.
One trade per symbol per day. Entry = the 08:15 London candle close, stop and 1R target from the indicator, flat at 16:00 London, stop first on a tie.

## Track B: Claude's call
Each trading day at 08:27 local wall clock (the 08:15 candle is on the delayed feed by then), for each symbol Claude reads the first 15-minute candle and the day's bias note and writes LONG or SHORT (never skip), with a one-line reason, into `PARALLEL_LOG.csv` BEFORE reading any later price. Same entry, stop and target as track A.
Scoring of B without extra data: same direction as A = same result; opposite direction = the mirror trade, R_B = -(gross R of A) - cost in R (exact for 1:1 geometry except same-bar ties).

## Daily record
At 16:10 local wall clock the closed trade of each symbol (its label R) is appended to `PARALLEL_LOG.csv`. The log, not TradingView's limited 1-minute history, is the record.

## Metric and gates
One observation per day = mean of the 4 symbols' net R.
- **Gate A (what would justify buying ONE account):** at least 40 days AND mean daily net R >= +0.25 AND one-sided P <= 0.05 against the random-side baseline (flip each symbol-day's side, 20,000 draws, resampled at day level). Not reached before the end of the test, no purchase on this indicator's account.
- **Futility stop:** after 20 days (Fri 20 Nov), mean daily net R <= -0.40 = stop and drop the indicator.
- **Track B** is reported (mean R and the B-minus-A difference on days it disagrees with A). It has no gate. Claude never trades real money and never places orders; the trader buys and trades himself.

## Honest limits
Four symbols on the same days = far fewer independent samples than 160 trades. Delayed feed (about 10 minutes) matters only for real order timing, not for this simulation. Days a market has no data are skipped for that symbol. Money note: the 31 Dec withdrawal goal cannot be served by waiting for this gate; the gate protects the purchase money.
