# D2_MT5WEEKLY_RESULT - D2 under MT5 broker's written reply (2026-10-15, local clock 19:23)
Pre-registration PREREG_D2_MT5WEEKLY.md (commit at 19:21); runner d2_mt5weekly.py; output D2_MT5WEEKLY_OUTPUT.txt. Engine check: with next-day re-entry the runner reproduces D2_MT5RULE exactly.

## MT5 broker's reply (the trader's paste) settles two rules and leaves one grey
1. Daily loss level = 00:00-server starting BALANCE minus the fixed 2.5%; equity touching it is a breach; a floating loss carried into the day already counts. This is what D2_MT5RULE simulated.
2. Only 2,000 USD a day of closed profit counts; the excess is removed at rollover. Also simulated.
3. Closing and reopening to stay under the cap is "not defined"; MT5 broker advises letting positions run "rather than structuring trades specifically to stay under the daily cap". The next-day re-entry after a profit close is therefore not forbidden but goes against MT5 broker's advice.

## Result: pass / breach % (181 rolling starts 2022-01..2025-06, balance guard 1,500, take-profit +1,800 at 22:30, pass lock)
| policy | gross | 30 Oct | 22 Dec | 31 Mar 27 | 30 Jun 27 |
|---|---|---|---|---|---|
| next-day re-entry (D2_MT5RULE, against MT5 broker's advice) | 100k | 0 / 0 | 0 / 1.1 | 29.8 / 3.3 | 59.7 / 4.4 |
| next-day re-entry | 150k | 0 / 1.7 | 2.2 / 12.2 | 27.6 / 25.4 | 49.7 / 35.4 |
| **W1: flat until the next Monday 18:00 decision** | 100k | 0 / 0 | 0 / 0 | 14.4 / 0.6 | 40.9 / 1.1 |
| **W1** | **150k** | 0 / 0 | **4.4 / 1.7** | **42.0 / 8.3** | **59.7 / 12.7** |
Re-entering only at D2's own weekly decision cuts the time in the market after a profit day, which lowers the breach rate enough that 150k gross becomes the better size: about the same pass rate by June 2027 as the old plan at 100k, faster by March (42% vs 30%), at 8-13% breach instead of 3-4%. Without any take-profit the pass rate is 0% (profit is counted only when closed, at most 2,000 a day).

## Reading for the trader
W1 is the version that fits MT5 broker's answer: the book trades only on its normal Monday schedule; the +1,800 close is an ordinary take-profit, and nothing is reopened before the next weekly decision. Still slow: 0-4% by 22 Dec, about 40% by end of March. In-sample caveats as in D2_MT5RULE (2022 starts mostly go nowhere).
