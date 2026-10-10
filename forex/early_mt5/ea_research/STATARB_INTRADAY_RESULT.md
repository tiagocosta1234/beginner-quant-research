# R: intraday pairs stat-arb on six linked MT5 broker pairs: result (2026-10-10, local local clock)

Pre-registration `PREREG_STATARB_INTRADAY.md` (commit cde42ef, before any P&L), simulator `statarb_intraday.py`, output `STATARB_INTRADAY_OUTPUT.txt`, ledger family statarb_intraday (six trials). The 2026 hold-out was NOT opened. Context: the trader's goal "um novo sistema, 70% chance de passar o desafio este mes" (spec: about 500-600 USD a day with a daily Sharpe of 0.5-0.85).

## Verdict: all six pairs FAIL acceptance 1 and 2 by a wide margin; the class is closed
| pair | DEV 2022-24: trades, net bp/trade (gross), daily t | VAL 2025: net bp/trade (gross), daily t | round-trip spread paid (DEV / VAL) |
|---|---|---|---|
| R1 SP/DOW | 4,640, -1.81 (+0.08), -11.0 | -2.52 (-0.23), -8.1 | 1.49 / 1.91 bp |
| R2 SP/NSDQ | 4,650, -1.36 (+0.27), -9.2 | -1.73 (+0.51), -8.6 | 1.29 / 1.89 |
| R3 XAU/XAG | 4,764, -3.06 (+0.60), -13.9 | -4.62 (-0.10), -8.2 | 3.38 / 4.25 |
| R4 BRENT/WTI | 4,602, -10.85 (+0.89), -52.6 | -8.50 (+0.67), -42.2 | 11.36 / 8.79 |
| R5 AUD/NZD | 4,555, -0.77 (+0.49), -5.8 | -1.75 (+0.47), -9.3 | 0.89 / 1.86 |
| R6 EUR/GBP | 4,872, -0.43 (+0.27), -3.2 | -0.89 (+0.33), -4.7 | 0.36 / 0.87 |
Every pair loses in every year 2022-2025.

## Reading
- The residual between linked instruments does mean-revert a little (gross +0.1 to +0.9 bp a trade in most pair-years), but that is less than the spread on every pair, including the cheapest (EUR/GBP: gross +0.27 bp against 0.36 bp paid in DEV and 0.87 bp in VAL).
- Signals cluster when quotes are wide: the spread actually paid on signal minutes is up to twice the median (SP/DOW 1.9 bp in 2025 against a 1.6 bp median), because a z-score of 2 is often a quote dislocation, not a tradable mispricing.
- For the goal this is a clean negative. The class that, in principle, can produce a high daily Sharpe (many short hedged trades) has no edge after MT5 broker's costs at a five-minute horizon. Going faster is not allowed (MT5 broker HFT rule, and it would be latency arbitrage).
