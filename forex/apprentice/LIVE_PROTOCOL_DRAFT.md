# LIVE_PROTOCOL (DRAFT for the trader to approve; applies only once an account exists)

Written 25 Oct 2026 (local clock), calm, before any live money. Claude does not place orders or touch accounts; the trader trades. Claude reads this back, checks each trade against it, and reports honestly.

## Before 08:00 (all must be true or no trade today)
1. 15-minute bias written down: long / short / neutral. Neutral = no trade.
2. Daily loss and trade count reset; no open position; not tilted (if the last trade or the day before upset you, say so and skip today).
3. Contract size = the LOWER of USD 400 risk and the firm's contract cap (3 minis / 30 micros on Broker Flex).

## Entry (08:00-08:15 only, if the phase 3 rule is approved)
- A 1-minute candle CLOSES beyond the 12 EMA on the bias side.
- Target (high-low / order block / FVG) and stop (beyond an order block or FVG) set BEFORE entry, with a planned RR of at least 1.0.
- Screenshot taken before entry; the trade is logged with the price levels before the result is known.

## After entry
- The stop is NEVER moved. No breakeven moves, no widening. The trade ends at the stop or the target.
- No second trade after a loss. No trade outside the window.

## Daily and weekly stops
- One trade a day. After a loss: done for the day.
- 3 losses in a row: pause the next trading day and review the last 3 trades with Claude before the next entry.
- Account at 50% of the drawdown used: risk drops to half until a new high-water mark.
- A day that makes more than 40% of the total test profit: stop for the day (consistency limit).

## What Claude does
- Reads the checklist back before each session; asks "bias written? window? size?".
- After each trade: logs R, checks stop not moved, entry inside the window, screenshot present; flags any breach plainly.
- Weekly: honest numbers (win rate, mean R after costs, streak), never rounded up.
- Never promises a withdrawal and never says "this one is safe".

## Hard limits
- Claude never places orders, buys accounts, or arms anything for the trader. the trader buys and trades himself. No account is bought until a pre-registered gate has passed.
