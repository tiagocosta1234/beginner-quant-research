# BEST3M_CYCLE_RESULT - an MT5 broker evaluation trading every symbol's best recent breakout at once (2026-10-15, local clock 17:54)
Pre-registration PREREG_BEST3M_CYCLE.md (commit a01a73a9). Code best3m_cycle.py, output BEST3M_CYCLE_OUTPUT.txt, cycles data/si_ledgers/BEST3M_CYCLE_B.csv. Dry run: the monthly picks are identical when the data after the pick date is cut. MT5 broker bid/ask, spreads paid; MT5 broker Pro rules (8% target, 92,000 floor, 2,500 daily line from the day-start balance, +2,000 a day counted).

## Verdict: the policy breaches almost every cycle; even the look-back table itself breaches above $100 a trade
- **A, in-sample (the table's 46 rules traded over the same 3 months they were chosen on, 2026-07-03..10-02):** +541.6 R on 1,906 trades (21 a day). At $100 a trade it passes in 18 days (worst day -$1,554, losers-only -$2,097). At $200 or $300 a trade it BREACHES in 0-7 days: one day lost -16.8 R because about 20 correlated setups fail together.
- **B, causal (each month, every symbol's best rule of the previous 3 months, 2022-03..2026-10):** -0.052 R a trade (2022 +0.020, 2023 -0.063, 2024 -0.045, 2025 -0.097, 2026 -0.067), 32,789 trades. Over the same 3 months as A it made **-224.8 R** instead of +541.6.
| risk a trade | pass within 30 d | breach within 30 d | pass ever | breach ever |
|---|---|---|---|---|
| $100 (optimistic / pessimistic daily line) | 2.6% / 2.6% | 37% / 57% | 6.8% / 4.7% | 93% / 95% |
| $200 | 2.1% / 0% | 95% / 100% | 2.1% / 0% | 98% / 100% |
| $300 | 2.1% / 0% | 98% / 100% | 2.1% / 0% | 98% / 100% |
235 cycle starts; no start year does better (at $200: 0-6% pass, 94-100% breach).

## Reading for the trader
A table of last-3-months winners always looks like a money machine (+541 R) because it is chosen after the fact. Traded forward, the same selection loses (-0.05 R a trade, about the spread), and with 20+ setups a day the losses come together: the daily 2,500 line is hit on the first bad day. This is the best3m table's honest test: do not trade it.
