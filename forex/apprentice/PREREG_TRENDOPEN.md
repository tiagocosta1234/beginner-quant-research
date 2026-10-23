# PREREG_TRENDOPEN: with the 30-minute trend, after a pullback, at the London open (gold futures)

Written 23 Oct 2026 ~00:5x local (local clock), before any P&L of this rule was computed (header time corrected from an estimate before any P&L). Goal set by the trader on 22 Oct: "you get really good at trading".

## Why, and the honest prior
- In the read test (`READ_TEST_RESULT.md`), trades with the 30-minute trend made +0.119 R each (69 trades), against -0.269 for those against it (24).
- Resumptions after a pullback went 10 / 10.
- That split was chosen after seeing the trades, so it may be noise. This rule fixes it in advance and tests it on days never looked at one by one.
- Prior: low.
  - Every mechanical form of the trader's setup has failed: EMA12 0 / 32, MANUALRULE 0 / 12, TRAP12 0 / 18, the rubric -0.114 R on 632 trades.
  - The rubric's "with the trend" grade-A setups did worse, not better.

## Data and days
- Databento GC 1-minute continuous front month. Weekdays 2020-01-02..2025-12-31, with the same quality filters as `rubric_backtest.py`:
  - at least 120 bars from 06:00 to 08:15 local;
  - no jump above 8 points between bars, so roll days drop out.
- Excluded:
  - the reserved windows (2023-11-28..12-27, 2025-02-28..03-29, 2025-04-01..05-31);
  - Sep-Nov 2024 (the hand desk);
  - Jun-Aug 2024 (the trader's training-camp window);
  - the 100 read-test days (`state_t/order.csv`);
  - the trader's January 2026 days (2026 is not loaded at all).
- **DEV = 2020-2022. VAL = 2023-2025, one look, only if DEV passes.**

## Rule (one trade a day)
Scan the candles i = 07:59..08:14 local in order. Take the first one where all of these hold:
1. **Trend:** the close of i minus the close 30 candles earlier has the trade's sign and is at least 1.0 ATR14.
2. **Pullback:** at least one of the three candles before i closed against the trade.
3. **Signal candle:**
   - closes in the trade's direction with a body of at least 0.8 ATR;
   - close-side wick at most half the body;
   - close on the trade's side of the EMA 12.
4. **Not extended:** the candle's open is within 1.5 ATR of the previous candle's EMA 12.

**Bracket:** the the trader-style level from `manual_read.manual_bracket` for that side and candle. Target = the nearest level at least 2 ATR away, else at least 0.8 ATR; if there is no level, 2.5 ATR. Stop = target distance / 0.53.

**Execution:** `desk.simulate`, i.e. entry at the next candle's open plus 1 tick; stop first if a bar touches both; 1 tick on the stop plus 0.15 points; flat at 20:00.

## Measures
- **Primary (DEV):** mean R per trade after costs, and the sign-flip P of R against its mirror (same entry and distances, other side; 20,000 draws, seed 7).
  - **DEV passes iff mean R >= +0.05 and P <= 0.01.**
- **VAL (one look):** passes iff mean R > 0 and P <= 0.05.
- **Secondary (reported, no bar):**
  - the same entries with a 1:1 bracket (stop as above, target at the same distance);
  - each year;
  - longs against shorts;
  - the trade count.
- **Trials:** 1 primary + 1 secondary bracket.
