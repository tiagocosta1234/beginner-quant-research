# PREREG_EMA15: 15-minute 12 EMA cross with the trend, London morning, 1:1 to the nearest FVG / clear high-low (gold futures)

Written 23 Oct 2026 (local clock, time in the commit), before any P&L of this rule was computed.
the trader: "london session, 15 min time frame, if candle closes above EMA and trend is bullish, buy, if candle closes below EMA and trend is
bearish, short, 1:1 and target at nearest unmitigated fvg or clear high/low".

## Why, and the honest prior
- The 1 / 3 / 5-minute forms of the 12 EMA rule all lost at real costs: EMA12 0/32, MANUALRULE 0/12, EMA1000 0/1,000 (best around -0.02 R before spread).
- The 15-minute timeframe was never tested. A slower bar may cut the noise and the cost per R.
- Prior: about -0.05 to 0 R a trade after costs. A pass would be a surprise.

## Data
- Databento GC 1-minute, local clock, built into 15-minute bars (`forex/apprentice/desk.py` `raw()`).
- **DEV:** 2019-07-01 .. 2022-12-31. **VAL:** 2023-01-01 .. 2024-12-31. **HOLD:** 2025-01-01 .. 2025-12-31, one look, only for a candidate that passed DEV and VAL. 2026 is never loaded.
- Days with a minute-to-minute jump above $8 between 07:00 and 16:59 (contract roll) are skipped.

## The rule (all on completed 15-minute bars; nothing uses a bar that has not closed)
- **EMA:** 12-period EMA of the 15-minute closes, continuous across days.
- **Signal bar:** opens 08:00 .. 11:45 local (closes 08:15 .. 12:00).
  - Long: close > EMA12 and the previous bar's close <= its EMA12, and the trend is bullish.
  - Short: the mirror.
  - Only the first signal of the day is traded. One trade a day.
- **Trend:** three definitions = three trials.
  - **T50:** close > EMA50 and EMA50 > EMA50 four bars earlier (bearish = the mirror).
  - **T80:** the same with EMA80 (about the 1-hour EMA20).
  - **TPD:** the previous weekday's 21:59 close > its 08:00 open (bearish = below).
- **Entry:** the next bar's open, 1 tick (0.1) worse.
- **Target:** the nearest level beyond the entry, in the trade direction, at least 0.5 x ATR14(15m) away. Candidate levels, all known at the signal close:
  - the near edge of an unmitigated 15-minute FVG formed since the previous weekday 08:00. Bearish gap above for longs (bar1 low > bar3 high, target = bar3 high), bullish gap below for shorts. Unmitigated = no later bar traded into the gap.
  - unbroken 15-minute swing highs / lows (2 bars each side) since the previous weekday 08:00;
  - the previous weekday's 08:00-21:59 high / low;
  - today's Asia (00:00-07:59) high / low.
  - No level in range = no trade.
- **Stop (1:1):** D = |target - entry|; stop = entry -/+ D, filled 1 tick through.
- **Exits:**
  - a target fills only if traded 1 tick through;
  - a 1-minute bar that reaches both stop and target counts as the stop;
  - otherwise flat at the 16:30 bar's open.
- **Costs:** commission 0.15 points a round turn. R = net points / D.

## Measures and bars
- For each trial and period: trades, win %, mean R after costs, t-stat, mean R without costs.
- Yardsticks, no bar:
  - the same rule with NO trend filter;
  - the INVERTED rule (fade every signal) for T50;
  - long-only vs short-only.
- **DEV pick:** the trial with the best DEV mean R. If none is above 0, the family fails at DEV.
- **VAL pass:** the picked trial's VAL mean R > 0 with one-sided t P <= 0.05, AND it beats its own no-trend version on VAL.
- **HOLD:** opened only after a VAL pass. HOLD mean R > 0 confirms. One look.
- Bonferroni context: 3 trials. DEV-best is reported with its raw and its x3 P.
- the trader's live bar of +0.5 R a trade is reported next to every mean.

## Rules
- No change after the first P&L. The `--dry-run` (counts, truncation causality test, hand check of 3 signals) prints no P&L.
- Results go to `EMA15_RESULT.md` and the ledger, pass or fail.
