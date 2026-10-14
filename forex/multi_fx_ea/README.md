# multi_fx_ea: the best-performing EAs developed in the lab (EURUSD / USDJPY / GBPUSD and other FX)
Created 2026-10-14 at the trader's request. Only EAs that clear every admission gate go in this folder's top level; everything else stays in `candidates/` with its status.

## Admission gates (all required)
1. Pre-registered rule (PREREG file committed before any run), development and validation periods both pass the registered bars (Bonferroni for the number of trials).
2. A clean out-of-sample test on data the rule has never seen (an unopened hold-out, or a forward log); a hold-out that has been peeked at does not count.
3. MT5 tester on MT5 broker real ticks with commission, spread and capped lot sizing; matches the Python engine trade for trade.
4. Works under the MT5 broker rules: daily loss line (guard stops at 1.5-2.0%), no all-or-nothing sizing, no hedging unless MT5 broker allowed it in writing (it did on 2026-10-11).
5. Correlation of daily P&L with the live gold pair <= 0.3 and an uplift in the clean pass simulation with at most 1 point of extra breach.
6. A forward paper log of at least 60 trading days that agrees in sign and rough size with the backtest.

## Status board
| EA | status | where |
|---|---|---|
| (none yet) | no rule has cleared gate 1 on the three pairs | - |
| fade_ema_bracket (EURUSD) | candidate, fails gate 1 (2025 validation) and gate 2 (2026 peeked) | candidates/fade_ema_bracket.md |
The live gold pair (ManualSDB, XAU5, ManualDip) is managed in `forex/` and is not part of this folder.
