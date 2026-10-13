# Pre-registration: "Trade with Pat" supply/demand zones (youtube WnzC8qnfhUA), single position and the "trading basket" (family Z, one trial + one diagnostic)

Written 2026-10-10 (time = the commit adding this file), BEFORE any simulation. the trader: "(original wording omitted)" (test the entry with one position, and measure the basket honestly). Video rules [01:43-13:18]; the basket is a scaled martingale (0.15 / 0.30 / 0.60 lot at three zones), which the video admits can lose when price "continues forever".

## Data
MT5 broker M1 bid/ask 2021-12 .. 2026-09; H1 bars of the mid. Markets: 28 FX pairs, SP, NSDQ, DOW, DAX, NIKKEI, ASX, XAUUSD (35).

## Zones (fixed now)
Demand: an impulse = 3 consecutive bullish H1 bars whose combined body >= 1.5 x ATR14(H1), containing at least one fair value gap (low of bar k+2 > high of bar k inside the impulse), and whose high breaks the highest high of the 20 bars before it (break of structure). Zone = the bar just before the impulse (its low to its high). Supply mirrored. A zone is valid for 120 H1 bars after the impulse and is used once (first touch).
Confirmation (video [08:38-10:30]): an H1 bar whose low enters the demand zone (<= zone high), closes above the zone high, and whose range is < 2 x ATR (price "slows down"; no huge candle). Mirrored for supply.

## Z1: single position (the trial)
Entry at the open of the minute 2 minutes after the confirmation bar's close (ask to buy, bid to sell, +0.1 bp). Stop: 2 bp beyond the zone's far edge. Target: the impulse's extreme (the "recent price" the video targets); skip if the target is < 1 R away. Exit on stop / target from M1 bid/ask (both in one minute = stop), else after 48 H1 bars, and always flat by Friday 21:00 server. Result in R.
Periods: DEV 2022-24, VAL 2025, HOLD-OUT 2026 (one look). Acceptance: DEV >= 200 trades, mean R > 0, t >= 2.0; VAL mean R > 0; HOLD mean R > 0.

## Z2: the basket (diagnostic, NOT a trial; never to be used on MT5 broker)
Same entries; d = entry-to-stop distance of Z1. Units: 1 at the entry, 2 more at entry - d, 4 more at entry - 2d (longs; mirrored). The whole basket closes when its P&L reaches 1 x d x (total units) above zero... precisely: at the Z1 target if only the first unit is open, otherwise when price returns to the basket's average entry + d; it is stopped at entry - 3d (all units). Sized so the FIRST unit risks 0.15% of 100K (the video's 0.15 / 0.30 / 0.60 of a 1-lot plan: total 1.05% if all three fill). Reported: win rate, mean R of the 1-unit-equivalent, worst basket loss in USD, and how many baskets would have crossed MT5 broker's 2,500 USD daily line.

## Honest prior
About 7% for Z1 (supply/demand retests failed in this repo, Round 196; FVG combos too, Round 189). The basket will show a high win rate by construction; the question is the size of its losses.
