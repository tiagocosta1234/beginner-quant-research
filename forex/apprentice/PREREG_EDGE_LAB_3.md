# PREREG_EDGE_LAB_3: the trader's idea, "15m bias + 5m candle in favour, 1:1 with a wide stop"

Written 25 Oct 2026 (local clock) BEFORE any result of this idea was computed. the trader's words: "an indicator that simply checks the 15m bias, then waits for a 5min candle closes above/below, waits for it to be in favor of the bias and 1:1 stop with wide stop". Batches 1 and 2 (ten ideas) found no finalist on DEV; the hold-out is still sealed. Claude turned the words into the exact rules below; where the trader's words were open, the choice is stated.

## The idea (all parameters fixed here)
- **Bias (15m):** as in the A+ checklist, evaluated once at 08:00 local: last closed 15m candle's close vs the 15m EMA12, and the 15m EMA12 vs its value 4 candles earlier. Both above and rising = long; both below and falling = short; anything else = no trade that day.
- **Trigger (5m):** from 08:00 to 11:00 local, the first 5-minute candle (local-aligned) that closes above (long) / below (short) the 5-minute EMA12 AND is in the bias direction (close > open for longs, close < open for shorts). Entry at that candle's close +/- 0.1 point slippage against. One trade a day.
- **Stop ("wide"):** 3 x ATR(14) of 5-minute candles at the signal candle (simple mean of the last 14 true ranges). A signal whose stop is under 3.0 points is skipped. **Target:** 1:1 (entry +/- 1.0 x risk). Time exit at 17:00 local.
- Open choices made by Claude: "above/below" = the 5m EMA12 (the EMA in the trader's setup); "wide" = 3 x 5m ATR; window 08:00-11:00 (the London morning); no other filter. No variants will be run on DEV.

## Data, split, costs (as batch 1)
Databento GC.F 1-minute bars, Europe/London clock. DEV = 2019-06-19 to 2023-12-31; HOLD-OUT = 2024-01-01 to 2026-09-25 (sealed). Entry at the 1m close that completes the 5m candle +/- 0.1 point; stop exit at the stop -/+ 0.1 point (gap: at the open); target needs 0.1 point of trade-through; same-bar stop and target counts as a stop; stops and targets checked on 1-minute bars. Commission USD 1.20 round trip per micro (R cost = 1.2 / (risk points x 10)). R net = (exit - entry) x side / risk - commission R.

## Direction skill, not drift
Mirror trade = same entry, same distances, opposite side (so at 1:1 it is the opposite bet). Random-side P = share of 20,000 draws, each trade independently actual or mirror, whose mean R is at least the actual mean.

## Finalist rule (DEV only; 11 ideas tested in total, Bonferroni alpha 0.05 / 11 = 0.0045)
All must hold on DEV: at least 150 trades; mean R net >= +0.10 (a win rate of about 55% at 1:1); random-side P <= 0.0045; mean R net > 0 in at least 3 of the 4 calendar years 2020-2023. Otherwise the verdict is "no edge", the hold-out stays sealed, and no variant (other window, stop width, EMA) is tried on DEV.

## Hold-out rule (one look, finalist only)
At least 100 trades AND mean R net >= +0.10 AND random-side P <= 0.05 AND mean R net >= 0 for longs and for shorts. Otherwise fail, no re-tuning.

## Honest limits
At 1:1 the strategy needs a win rate above roughly 52-53% just to break even after costs, so even a real directional skill can be small. Continuous front-month series, idealised fills, one instrument.
