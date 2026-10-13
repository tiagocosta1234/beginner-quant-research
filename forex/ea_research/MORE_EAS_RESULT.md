# Families TS, PI, LL result (2026-10-12)

Pre-registration: PREREG_MORE_EAS.md. MT5 broker M1 bid/ask, spread paid, hold-outs unopened.

| Trial | DEV | VAL 2025 | Verdict |
|---|---|---|---|
| TS trend on 18 markets (DEV 2023-24) | Sharpe **0.498** (bar 0.5), 2023 +1.2%, 2024 +2.7%, 4% annual vol | +6.2% (Sharpe 1.88) | fail by 0.002 |
| PI index pairs (3 pairs pooled) | +0.29 bp/trade, t 0.01 (51 trades) | +30 bp, t 0.78 (18) | fail |
| LL1 DAX session -> US afternoon | -2.73 bp/day, t -1.08 (737 days) | +6.3 bp, t 1.14 | fail |
| LL2 NIKKEI session -> DAX | +2.29 bp/day, t 0.72 (754) | +0.9 bp, t 0.17 | fail (t < 2) |

## Verdict: none passes, the 2026 hold-out was not opened for any.
TS missed the registered Sharpe bar by 0.002; the bar is not moved. It is the closest thing to a diversifier found this week, but at the registered 10% per-market vol target the whole 18-market book earns about 2% a year on 4% volatility (about +2,000 USD a year per 100,000 USD of NAV): on MT5 broker it is far too slow to matter for a pass, and its 2023-24 edge is small. Its 2025 (+6.2%, Sharpe 1.9) looks better, which is the same gold-and-trend regime the pair already lives in, so it would not diversify the gold exposure much.
PI: no reversion edge between correlated indices after costs. LL1/LL2: no lead-lag that survives the spread.
