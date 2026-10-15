# PREREG_D2_MT5RULE - the D2 book under MT5 broker Pro's BALANCE-based daily line and the 2%-a-day profit removal (written 2026-10-15, before any run; commit time = registration time)

## Why (a flaw in D2_ACCOUNT / VALIDATED_BOOK)
MT5 broker's Daily Drawdown article (intercom 11769446, re-read today): "Every new day at 00:00 Server Time, we set your loss level = Starting Balance of the new day - that fixed $ amount"; a breach is equity or balance at or below that level at any time. The level comes from the BALANCE: floating losses carried from earlier days count against today's line, and floating profits give no room. Profits count only when realised, and MT5 broker Pro removes realised profit above 2% (2,000) of a day at rollover. The earlier D2 account simulations measured each day's loss from the previous day's equity and counted floating P&L as balance: right for a book that is flat at rollover, wrong for a book that holds for weeks. This round simulates the exact rule. No new signal; D2's weights, filter and band are unchanged.

## Execution modes (2 configurations x 4 sizes; descriptive, no edge claim)
- HOLD: D2 as registered (weekly Monday 18:00 rebalance, positions held). Guard: close everything when equity <= day-start balance - 1,500 (the trigger minute's bid low), re-enter at the next business day 18:00. Profit skim: at 22:30 server, if the book's floating profit is >= 1,800, close everything (realised, counted up to 2,000) and re-enter at the next business day 18:00 (a later time on another day, not an immediate close-and-reopen). Pass lock: if day-start balance + realised today + floating >= 108,100 at any minute, close everything; the realised day counts at most +2,000.
- DAILY: open the current week's D2 targets at the bar opening at 01:05 server every weekday (after the rollover hour; buys at the ask) and close everything at the bar opening at 22:45 server (at the bid). The book is flat over every rollover and weekend, so each day's loss is measured from a balance with no floating positions. Weights from the Monday 18:00 signal (D2 rules), applied from the next 01:05. Same 1,500 guard (flat for the rest of the day). Realised day gain counted up to +2,000.
- Sizes G = 50k, 75k, 100k, 150k.
- Breach: equity <= day-start balance - 2,500 or <= 92,000 at any minute. Pass: counted balance >= 108,000.

## Account estimate
- HOLD is path dependent (floating P&L carries over), so it is simulated on real history from every 5th business day start in 2022-01-03 .. 2025-06-30 (about 180 overlapping starts), from 97,708.08, to 30 Jun 27-length horizons (fraction of starts that pass / breach within 48 / 119 / 184 business days); starts overlap, so this is a descriptive range, not an independent sample.
- DAILY is flat at every rollover, so its days are close to independent: 5-day block bootstrap of its day results (as SWAPFREE_MT5SIM) AND the same rolling historical starts, both reported.
- Also reported per mode: mean USD a day, costs, guard / skim / lock counts, worst day, by year 2022-26.

## Honest expectation
HOLD will breach more than D2_ACCOUNT said (a 2022-type slide breaches through carried floating loss unless the guard realises it first, which turns the book into a stop-loss strategy) and the skim cuts the trend's winners; DAILY pays a spread every day (about 0.7 bp of gross) and loses the overnight and weekend part of the drift. Either may turn D2 from 'pass > breach' into 'not usable on MT5 broker Pro'; that is the point of the round.
