# PREREG HWR - high-win-rate, small-daily-win index strategies built on the validated dip edge, judged on MT5 broker cycles

Registered 2026-10-18 00:06 local (local clock, second PC PC-2), before any P&L of these trials was computed.
the trader: "find a strategy with a high win rate and small daily wins" (after UJ_EVAL_CYCLES showed that MT5 broker's +2,000 daily cap
confiscates the rare big wins a 28%-win breakout lives on). Principle: a win rate is set by the trade geometry, the profit by
the edge (random entries with a small target win 82% and lose, `MICRO_SCALP_RESULT.md`). So the trials start from the one
fast-repeating edge that passed out-of-sample and hold-out checks, the index dip reversal (`DIP_ADDON_RESULT.md`, ManualDip:
+62.8 bp a trade, win 57%, 4 of 5 years positive), and change only breadth and geometry.

## Common
- Markets: SP, NSDQ, DOW (decision 15:49 New York), DAX (17:19 Berlin), NIKKEI (14:49 Tokyo), ASX (15:49 Sydney). MT5 broker M1 bid/ask
  2021-12..2026-10-16, zero-spread minutes repaired (`brk_patterns.load`). Long only.
- Daily decision price = mid close of the decision minute; daily return SD = 60-day SD of decision-to-decision returns.
- Entry: ask open of the minute after the decision minute (+1e-5 slippage). Exit: bid open of the minute after the decision
  minute on the exit day; stop = entry x (1 - 3 SD), checked on M1 bid lows (fill at the stop, or the open if it gapped).
- R = net P&L / (entry - stop). One position per market at a time.

## Trials (3)
- **DIP6:** the registered ManualDip signal (3-day log return / (SD x sqrt 3) <= -2) on the 6 markets; exit at the next day's
  decision time (1-day hold).
- **DIP6-TP:** same entries; target = entry x (1 + 1 SD) on M1 bid highs; otherwise exit at the decision time after at most
  3 trading days.
- **CONNORS-RSI2:** decision close above its 200-day average and RSI(2) of decision closes (Wilder, alpha 1/2) < 10 -> buy;
  exit at the decision time of the first day whose decision close is above its 5-day average, at most 10 trading days.

## Periods
DEV 2022-01-01..2024-12-31 (CONNORS starts when 200 days of history exist, about 2022-10), VAL 2025, HOLD 2026-01-01..2026-10-16
(one look, only for trials that pass DEV and VAL; the 4-market DIP rule's 2026 is already known, the 6-market and TP variants
and CONNORS are not).

## Acceptance
- DEV: n >= 100; mean net R > 0 with day-clustered t >= 2.4 (Bonferroni, 3 trials); positive in >= 2 of 3 DEV years.
- VAL: mean > 0, t >= 1.65. HOLD: mean > 0, t >= 1.65.
- **MT5 broker fit (the point of this round):** win rate, share of trading days with a win, and the share of days whose realised
  P&L would exceed $2,000 at the tested size are reported; then the account environment decides usability:
  (a) back-to-back fresh MT5 broker Pro evaluations (100,000 -> 108,000, floor 92,000, -2,500 day, +2,000 day cap) over 2022-25 at
  $250 / $500 / $1,000 risk a trade, (b) from the live balance 95,472 by 30 Jun 2027 (5-day block bootstrap of 2022-25 days):
  usable only if P(pass) > P(breach). Floating losses are counted conservatively: every open position at its worst M1 point
  of the whole hold on each of its days.

## Honest prior
About 25% for at least one trial passing DEV + VAL (the underlying edge is already validated); much lower for passing the
MT5 broker test quickly: the dip edge fires about 20-35 days a year.

## Amendments
(none yet)
