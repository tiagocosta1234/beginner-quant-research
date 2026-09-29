# the trader (TOD filter + VWAP-Z combined) -- Rounds 57-75

**Status: real, live-tested (placed real trades on the $250K account before it breached via manual trading, unrelated to strategy performance). Sizing below is specific to a now-past deadline -- needs re-deriving against current account state before reuse.**

## What it is

Composes two independently-validated components, checking TOD first then
VWAP-Z, so they gate each other through `live_bot`'s existing
one-position-at-a-time rule (no custom logic needed):
- **TOD-filtered random entry** (`random_entry_atr_trail_strategy.py`,
  `tod_filter=True`): Rounds 19-26's validated edge -- the edge lives
  entirely in the EXIT (ATR-based trailing stop, cut losses fast, let
  winners run), not the entry; entry timing/direction is genuinely random.
  Round 39 found restricting entries to the last third of the RTH session
  roughly doubled OOS per-trade expectancy.
- **VWAP Z-score** (`vwap_zscore_strategy.py`): Round 49's MNQ edge.

## The real number

Sizing is a function of the account's OWN current buffer/target-gap/deadline,
re-derived multiple times as the account's state changed -- **not a fixed
number to reuse blindly.** The last real derivation (Round 75, 2026-09-23,
after a real DLL breach from manual trading): **TOD $1,680 / VWAP-Z $1,200 ->
P(success)=19.1%, P(ruin)=62.8%** against that day's real $22,402.18 target
gap and 27 trading days to a 2026-10-30 deadline. This was an explicit,
informed, aggressive choice (the account's real buffer was the binding
constraint, not a risk-tolerance preference) -- **the underlying deadline has
likely passed or moved by now; re-sweep before ever using this sizing again.**

Each component ALONE is real but insufficient: TOD-filtered random entry
alone still gave ~0% probability of reaching a profit target before that old
deadline (Round 40); VWAP-Z alone asymptotes to ~50-52% (Round 49b) at any
sizing. Only the composed pair, sized against the real account state, is
worth deploying.

## Where the code lives

- Research: `futures/docs/EDGE_VALIDATION_RESULTS.md` Rounds 19-26 (random entry), 49 (VWAP-Z), 57-75 (the composition and successive re-sizings).
- Live: `live_bot/manual_strategy.py` (`BOT_STRATEGY=manual`), wrapping `random_entry_atr_trail_strategy.py` + `vwap_zscore_strategy.py` internally.

## Real caveat

The sizing figures above are tied to a SPECIFIC account state and deadline
that this campaign has since moved past (the whole campaign's framing has
shifted to the long-run reinvestment-snowball model, not a single fixed
deadline). Do not reuse `$1,680`/`$1,200` on a different account without
re-running the sizing sweep against that account's real current
buffer/target-gap -- this is explicitly how the number was derived every
time it changed.
