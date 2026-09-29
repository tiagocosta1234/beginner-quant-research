# Support/resistance bounce (Round 30/30b) -- MGC edge, pairs with an MNQ edge

**Status: real, walk-forward validated. Best deployed alongside an MNQ edge as a combined portfolio, not alone.**

## What it is

Detects a causally-confirmed swing high/low on the 15-minute MGC (Micro Gold)
chart, waits for price to later touch that level (within 0.5x ATR(14,15m)),
and fades the touch: short on a touch of resistance from below, long on a
touch of support from above. Exit uses the same ATR-trailing mechanism as
the MNQ random-entry edge (1.0x ATR initial stop, 1.5x trailing, no fixed
target).

## The real number

Parameters (`swing_k=3, tol_atr=0.50`) are the pair Round 30b's own per-fold
train-selection picked in 5 of 6 walk-forward folds -- the dominant, most
representative choice, not a cherry-pick.

**As part of a combined MNQ+MGC portfolio (Round 34, refined sizing sweep):
MNQ $245/trade + MGC $650/trade -> 87.8% success, 3.8% ruin** against that
round's real target gap and deadline. This is a real, strong number, but --
same caveat as the trader's card -- it's tied to a specific historical account
state/deadline (Round 31-34, 2026-09-20) that has since moved on; treat the
87.8%/3.8% figure as "this is what a well-sized combined portfolio can look
like," not a number to reuse unchanged.

Individually-buffer-safe sizing alone (MNQ $75, MGC $200) is too
conservative to be useful against a real short deadline (0.4% success in
Round 31) -- the combined-and-aggressively-sized version is what actually
works, a real, checked finding, not an assumption.

## Where the code lives

- Research: `futures/docs/EDGE_VALIDATION_RESULTS.md` Round 30/30b (the edge), Round 31/31b-e/33/34 (the combined-portfolio sizing).
- Live: `live_bot/support_resistance_bounce_strategy.py` (`BOT_STRATEGY=support_resistance_bounce`, `BOT_INSTRUMENT=MGC`).

## Real caveat, disclosed in the file's own docstring

Round 30b fixed a real bug in the original Round 30 signal generator (it
fired on every level touch with no one-position-at-a-time gating) -- the
live version's level-consumption design exists specifically not to repeat
that. There's also a documented live-vs-backtest gap on level detection
while a position is open -- read the file's module docstring before running.
