# Family ID result: the RSI(2) dip rule at H1 and H4 on six indices (2026-10-12)

Pre-registration: PREREG_INTRADAY_DIP.md. MT5 broker M1 bid/ask, spread paid on both fills, SP / NSDQ / DOW / DAX / NIKKEI / ASX pooled, observation = entry day. Hold-out unopened.

| | Trades per year | DEV 2022-24 | VAL 2025 | Indicative Sharpe (25k per trade) | Verdict |
|---|---|---|---|---|---|
| Daily (reference, EV1, SP/NSDQ/DOW) | about 20 | +61 bp per trade, PF 2.9 | hold-out +85 bp, PF 6.0 | about 0.3 | candidate |
| **ID1 H1** | 859 | **+1.3 bp**, PF(day) 1.14, t 1.10 | +1.9 bp, t 1.03 | -0.66 / 0.44 | **fail** |
| **ID2 H4** | 244 | **+2.9 bp**, PF(day) 1.13, t 0.83 | +12.0 bp, t 2.41 | -0.35 / 1.65 | **fail** (DEV) |

## Verdict: the edge does not survive faster bars.
The same rule gives 40 times more trades at H1 and 12 times more at H4, but the edge per trade collapses from about +60-85 bp (daily) to +1 to +3 bp (DEV), which is within the spread and noise. H4's 2025 (+12 bp, t 2.4) is a one-year result against a flat DEV. By market: NSDQ, SP and DOW are marginally positive at H4 (+3.5 to +4.4 bp), NIKKEI and ASX negative.
Reading: the index dip effect is a multi-day, daily-close phenomenon (overnight and multi-day reversal after sell-offs), not an intraday one. Breadth cannot be bought by shrinking the bar size with this rule.
Where breadth could still come from: more independent instruments at the daily horizon (6-7 indices instead of 3-4) gives perhaps 35 entry days a year, still Sharpe well under 1 for that leg. The 30-day target needs Sharpe 6; no recombination of the dip rule gets near it.
