# Self-improving trader v1/v2: result (2026-10-12)

Pre-registration: PREREG_SELF_IMPROVING.md (+ Amendment 1). Code: platform_pit.py, grammar.py, loop.py. Ledgers: SI_V1_*, SI_LEDGER_V2.csv, SI_PLACEBO_LEDGER_V2_{7,8,9}.csv (append-only). HOLD 2026 never read.

## What was built
A point-in-time data platform (4 index CFDs, one decision bar per day, causal by construction, checked: cutting the future does not change any entry signal), a strategy grammar (4 families, ~thousands of cells), an agent loop (random + mutation of the best specs, every spec hashed and ledgered, cumulative Benjamini-Hochberg over every spec ever tried), and a PLACEBO mode that runs the identical loop on structureless price paths to measure the machine's own false-discovery rate.

## v1 (raw mean > 0): failed calibration
Real 2,400 specs -> 662 S1 survivors, 407 VAL passes. Placebo worlds -> 90 / 373 / 262 survivors. The test was rewarding index drift (3-5 bp/day, 2022-25) and the winner's curse. v1 survivors are not evidence.

## v2 (excess over holding the index for the same days)
| | specs tried | S1 survivors (BH q=0.10, cumulative m=2,400) | best DEV t |
|---|---|---|---|
| Real data | 2,400 | **0** | 3.34 |
| Placebo 7 | 2,400 | 0 | 2.63 |
| Placebo 8 | 2,400 | 5 | 3.30 |
| Placebo 9 | 2,400 | 39 | 4.83 |
The real market's best of 2,400 is indistinguishable from the best of 2,400 in a world with no structure. No spec reaches S1, so none goes to S2/S3/S4. The earlier RSI(2) leg under the same test: DEV excess +40 bp (t 2.65), VAL +36.5 bp (t 0.64): a weak signal, the same kind of result as the best searched specs.
Calibration is still imperfect (placebo 9 gives 39 false survivors), so even a positive result in this machine would need the stricter random-entry permutation null before anyone trusts it.

## Meaning for the account
Nothing in this search space (dip/RSI/low/breakout/pop-short on SP, NSDQ, DOW, DAX at the close, 2022-26) beats the installed system or adds to it with evidence. The installed system stays. The machine is now reusable: any new information source (alternative data, other markets, intraday features) can be fed through platform_pit.py and judged with the same cumulative bar and placebo control.

## Next, if continued (not started)
1. Strict null: per-spec random-entry permutation (same holding days) instead of the t-test, then rerun placebo until false survivors are about zero.
2. New information in the platform: MT5 broker gold intraday sessions, FX majors, the macro event calendar, crypto, each with its own placebo.
3. promote.py (S4 add-on test against the installed system, then tester real ticks, then forward) is only written when a spec reaches S3.
