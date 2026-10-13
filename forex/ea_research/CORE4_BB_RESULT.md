# CB1 result: the trader's Core 4 + Bollinger 4-hour RSI(2) variant on MT5 broker data (2026-10-12)

Pre-registration: PREREG_CORE4_BB.md. Rules as in the trader's script (Cutler RSI(2), SMA200/5/20, lower Bollinger 20/2, SP + NSDQ + DOW + NIKKEI), executed on MT5 broker 4 h bars with ask in / bid out.

| Window | Trades (per year) | Days | Mean per day-observation | PF(day) | t | Indicative Sharpe |
|---|---|---|---|---|---|---|
| **Out-of-sample 2022-01 .. 2024-09** (decides) | 152 (55) | 94 | **+2.7 bp** | 1.12 | **0.34** | 0.45 |
| In-sample 2024-10 .. 2026-09 (window the Yahoo script saw) | 123 (62) | 84 | +21.7 bp | 2.46 | 2.80 | 1.12 |
Yahoo script on its own 730 days: about 80 trades, +27 bp, semesters -31, -8, -9, +70, +52, +47 bp, Sharpe 1.4.

## Verdict: fails out-of-sample (needs +15 bp, PF 1.3, t 1.65; gets +2.7 bp, t 0.34).
The rule earns money only in the window it was tuned on (after the DAX/ASX removal and the Bollinger filter were chosen from that window's results) and nothing in the 33 months before it: the textbook signature of in-sample selection. Per market out-of-sample: NSDQ +22, DOW +3, SP +2, NIKKEI -5 bp.
Even the in-sample result (+22 bp, about 60 trades a year, Sharpe 1.1) is far under the Sharpe 6 a 30-day pass needs.
