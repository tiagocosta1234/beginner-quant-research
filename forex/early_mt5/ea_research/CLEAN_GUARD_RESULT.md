# Clean guard simulation: which levers really raise P(pass by 30 November) (local clock about 12:05, 2026-10-09)

`clean_guard_sim.py` (raw outputs `CLEAN_GUARD_OUTPUT_5Y.txt`, `CLEAN_GUARD_OUTPUT_12M.txt`). It replaces the carry-over approximation, which kept counting the floating P&L of positions the guard had already closed and so inflated every profit-cap result (see the banner on the withdrawn files and Update 33 of the checkpoint). Event-driven: the guard really closes the positions open at the halt minute at that minute's market price, drops trades that would have opened later that day and never lets a closed position contribute again. Validation: with no guard the total P&L equals the sum of the trades' P&L in every row. Horizon 37 business days (today .. 30 Nov). Minute-close equity (the tick-level work remains the reference for single-tick steps).

## P(pass by 30 Nov) / breach by 30 Nov
| size and guard | last 12 months (MT5 broker real-tick trades, 222 starts) | 2022-26 (MT5 broker trades at constant % risk, 1,189 starts) |
|---|---|---|
| x1.0 no guard | 39.6% / 9.9% | 9.1% / 0.0% |
| x1.0 both caps (what was running) | 37.4% / 0.0% | 9.0% / 0.0% |
| x1.0 loss cap only | 39.2% / 0.0% | 9.1% / 0.0% |
| x1.0 loss cap only + pass lock | 41.0% | 9.7% |
| x1.2 no guard | 55.0% / 9.9% | 13.9% / 1.9% |
| x1.2 both caps | 41.9% / 0.0% | 13.0% / 0.0% |
| x1.2 loss cap only | 50.9% / 0.0% | 14.0% / 0.0% |
| **x1.2 loss cap only + pass lock** | **55.0%** | **15.4%** |
| x1.4 no guard | 62.6% / 17.6% | 20.9% / 13.7% |
| x1.4 both caps | 44.1% / 0.0% | 16.6% / 0.3% |
| x1.4 loss cap only | 54.5% / 0.0% | 20.4% / 0.3% |
| x1.4 loss cap only + pass lock | 55.9% | 22.5% |

## Findings
1. The PROFIT cap (+2,000 a day) lowers P(pass) in every row (x1.4 loss-only 54.5% vs both caps 44.1% in the last 12 months; 20.4% vs 16.6% over five years): it ends good days early and forgoes upside that would have counted up to the 2% limit. REMOVE it (live input InpGuardDayProfitPct 2.0 -> 0.0).
2. The LOSS cap (-2,000) costs 0-8 points of P(pass) and removes the breaches (9.9% -> 0% at x1.0 and 17.6% -> 0% at x1.4 in the last 12 months). KEEP it.
3. The pass lock (guard flattens at equity 108.3%) adds 0.6 to 4 points in every row. KEEP / ADD it.
4. Size: x1.0 -> x1.2 is worth +14 points (last 12 months, loss cap + lock) and +5.7 points over five years; x1.2 -> x1.4 adds +0.9 (12 months) and +7.1 (five years) but at x1.4 the tick-level work found a day on which equity crossed the -2,500 line in a SINGLE tick (no reaction time helps) and x1.2 had none: x1.2 is the choice.
5. Odds are regime-bound: the same configuration passes by 30 Nov in 55% of the last-12-month starts and in 15% of all 2022-26 starts. Config chosen: x1.2 (SDB 0.14, 5-minute EA 0.05), loss cap only, pass lock. Versus what was running: +17.6 points (last 12 months), +6.4 (five years).
Known caveat of the lock: it stops the guard for good once equity is at 108.3%; if MT5 broker removes the excess of a +2%-a-day-capped profit from the balance AFTER that, the balance could end below 108,000 and the test not be registered as passed while the guard is locked (re-attach the EA to unlock): check the MT5 broker dashboard whenever the positions disappear after a big day.
