# Family AL result: five hypotheses on data we never used (2026-10-12)

Pre-registration: PREREG_ALT_DATA.md. Data via Fincept's key-free feeds (Fear & Greed, DefiLlama stablecoins, FRED) and Binance public funding history. MT5 broker M1 bid/ask, spread paid, hold-outs unopened.

| Trial | DEV 2022-24 (n, bp, t) | VAL 2025 (n, bp, t) | Verdict |
|---|---|---|---|
| AL1 fear buy (F&G <= 25, 7 d) | 41, +55, 0.33 | 15, -148, -1.05 | fail |
| AL2 greed sell (F&G >= 75, 7 d) | 22, -38, -0.22 | 8, +460, 1.91 | fail (22 < 30 obs, wrong sign in DEV) |
| AL3 funding extremes (3 d) | 35, -53, -0.55 | 1, -686 | fail |
| AL4 stablecoin growth >= 2% (7 d) | 50, +139, 1.18 | 36, -49, -0.39 | fail (t < 1.65, negative VAL) |
| AL5 real yields -> gold (5 d) | 95, +32, 1.56 | 21, -111, -1.78 | fail (t just under 1.65, negative VAL) |

## Verdict: none passes, no hold-out opened.
Fear & Greed and funding carry no contrarian edge on MT5 broker's BTC/ETH after the spread; stablecoin growth shows a positive DEV mean with no consistency (VAL negative). The gold real-yield rule is the nearest miss in DEV (+32 bp, t 1.56) and then loses in 2025 (-111 bp, t -1.78), the decoupling of gold from real yields (central-bank buying) the prior warned about.
Across 14 families now none has produced a non-gold edge beyond ManualDip. New data types (sentiment, derivatives positioning, liquidity, macro) did not change that on these simple, published rules.
