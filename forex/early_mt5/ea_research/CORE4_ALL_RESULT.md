# CA result: the trader's Bollinger + RSI(2) 4-hour rule on every MT5 broker symbol (2026-10-12)

Pre-registration: PREREG_CORE4_ALL.md. 46 MT5 broker symbols, 4 h bars, long only, ask in / bid out. Out-of-sample 2022-01..2024-09 decides; in-sample 2024-10..2026-09 is the window the rule was chosen on.

| Group | OOS day-obs, mean, PF, t | In-sample mean, t | Verdict |
|---|---|---|---|
| indices (6) | 115, +0.3 bp, 1.01, 0.05 | +16.6 bp, 2.65 | fail |
| metals (2) | 50, -13.6 bp, 0.69, -0.95 | -81.4 bp, -2.06 | fail |
| **energy (WTI, BRENT)** | **33**, **+89.3 bp**, PF 5.0, t 2.85 | +55.1 bp, t 1.14 | **fail on count** (33 < 40 required) |
| crypto (8) | 116, -38.5 bp, 0.65, -1.30 | -29.2 bp, -1.14 | fail |
| FX (28) | 352, +3.8 bp, PF 1.46, t 2.59 | +0.5 bp, t 0.28 | fail (mean far under 15 bp, in-sample zero) |
| all 46 | 452, -3.2 bp, 0.90 | -3.2 bp | fail |
Symbols with a positive mean: out-of-sample 21/46, in-sample 19/46: exactly what luck gives (23 of 46).

## Verdict: no group passes. The rule is not an edge on MT5 broker's markets.
- Indices: nothing out-of-sample (+0.3 bp), the in-sample +17 bp is the tuned window again.
- Crypto and metals lose; FX is flat (+4 bp out-of-sample, +0.5 in-sample): after a 2 bp spread there is nothing.
- Energy is the only lead and the only group positive in BOTH windows with a decent t (OOS +89 bp, PF 5.0, t 2.85; in-sample +55 bp), but it is two near-identical markets, about 18 trades a year, and the registered minimum (40 day-observations) is not met (33). With five group trials one such result is within what luck gives. Not accepted; could only be re-checked forward (live/demo) or with a new pre-registration on oil alone, which cannot add history (MT5 broker data start 2021-12).
- Even the best case (energy, Sharpe about 1) is far from the Sharpe 6 a 30-day pass needs.
