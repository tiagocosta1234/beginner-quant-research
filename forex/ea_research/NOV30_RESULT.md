# NOV30 result: chance of passing by 30 Nov 2026 from the live state (2026-10-18 23:5x local clock, main PC)

Plan: PREREG_NOV30.md (amendment 1), plan text NOV30_PLAN_APPROVED.md. Command: `python -m forex.ea_research.nov30 --start 2026-10-19`
(full output NOV30_OUTPUT.txt, grid NOV30_GRID.csv, 71 configurations). Start state 95,472.14 (counted -4,527.86), horizons from Mon 19 Oct:
31 business days to 30 Nov, 47 to 22 Dec. Legs: gold pair (ManualSDB + XAU5, same multiplier), ManualDip, USDJPY London breakout; guard day stop 1,500,
news flat on CPI. Pools: MT5 broker 12 months (gold-flattered), FT 2022-26, MIX = their average. 20,000 paths per pool.

## Engine checks
1. Pair x1.5 + ManualDip 500 from 97,708: 18.0% / 4.3% breach by 30 Nov, 36.5% / 6.2% by 22 Dec. Expected 18.0% / 36.5%. **MATCH.**
2. USDJPY alone, from 95,472, by 30 Nov: $500 a trade pass 0.17% / breach 63.1%; $250 pass 0.00% / breach 18.5%. Second PC reference
   (PASS_BY_NOV_LAPTOP.txt): $500 0.5% / 50.8%; $250 0.0% / 10.7%. **Pass matches in size (under 1%, the pre-registered "~1%"); breach is
   12 points higher at $500 and 8 higher at $250.** Cause tested the same night: nov30 subtracts a 0.06 R cost haircut per trade that the second PC
   script did not (pre-registered, amendment 1). With haircut 0 the same machinery gives $500 0.23% / 56.1% and $250 0.01% / 13.1%, so the haircut
   explains about 7 of the 12 and 5 of the 8 points; the rest is the sampling method (pass70's pools and blocks against the second PC's 5-day blocks
   on 2022-25). Not an exact reproduction, direction and size explained; USDJPY adds almost nothing to any frontier line, so the conclusions
   below do not depend on it.

## Frontier (MIX; pass / breach by 30 Nov, then by 22 Dec)
| pair | dip | USDJPY | 30 Nov pass | 30 Nov breach | 22 Dec pass | 22 Dec breach | worst day |
|---|---|---|---|---|---|---|---|
| x1.8 | 500 | $150 (max pass) | 8.5% | 29.6% | 20.7% | 33.8% | -2,176 |
| x1.5 | 1000 | 0 | 8.2% | 17.7% | 22.5% | 20.9% | -1,813 |
| x1.5 | 500 | 0 | 8.0% | 17.3% | 22.5% | 20.3% | -1,813 |
| x1.2 | 1000 | 0 (best pass per breach) | 5.3% | 11.2% | 17.7% | 13.5% | -1,772 |
| x2.0 | 1000 | $150 | 7.1% | 35.0% | 17.1% | 40.2% | -2,417 |

Robustness of the max-pass point: seed 2 7.8% / 29.5%; only 70% of the pair's edge 4.0% / 41.7% (22 Dec 10.4% / 48.3%). Best-ratio point
with 70% edge: 2.8% / 17.6% (22 Dec 10.3% / 21.7%). Dynamic-sizing ceiling over pair multipliers: 9.4% / 37.0% (lambda 0), 7.6% / 16.3% (lambda 1).
By pool, the pass chance comes from the 2025-26 gold trend: x1.5 + dip 1000 gives MT5 broker 14.0% but FT 2.4%.

## Reading
- **The best pass chance by 30 Nov is 8.5%, below the 10-25% pre-registered expectation** (the start is 2,236 lower than the 97,708 reference).
  **In 69 of the 71 configurations the breach probability is larger than the pass probability** (the other two, ManualDip alone at 500 and 1000, are 0.0% / 0.0%) (breach 0 to 74.6%, pass 0 to 8.5%).
- By 22 Dec the pair x1.5 gives about 22% pass against about 20% breach; the breach is permanent (no reset, nothing more will be bought).
- USDJPY adds breach faster than pass; ManualDip at 1,000 adds about 0.2 points of pass for 0.4 of breach over 500. The pair multiplier drives
  everything, and above x1.5 the breach grows faster than the pass.
- No point reaches 70% (needs an annual Sharpe of about 7.7); the no-edge coin flip of +/-2,000 a day reaches 16.6% pass / 71.4% breach and is
  banned by MT5 broker, which shows how little skill the gold pair adds at this horizon.
- Caveats: the gold pair is in-sample (SDB is probably a curve-fit) and flattered by the 2025-26 gold trend; pools are bootstrapped from history.

## Decision for the trader
Pick a frontier point (maximum pass x1.8, or lowest breach per pass x1.2 / x1.5), or do not arm the book. Nothing was built or armed.
