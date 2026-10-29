# Glossary

| term | meaning here |
|---|---|
| **R** | one unit of risk: the distance from entry to stop, in money or points. A trade that hits a target twice as far as the stop wins 2R; a stopped trade loses 1R. Results are quoted as mean R per trade after costs. |
| **1:1, 0.5R, k:1** | target-to-stop ratios. A 0.5R target sits half as far away as the stop. |
| **Net / gross** | after / before trading costs. |
| **Costs** | fees plus slippage (futures) or the bid/ask spread (MT5), per round trip. On micro gold about 0.32 points, $3.20 a contract. |
| **MAE / MFE** | maximum adverse / favourable excursion: how far price went against / for a trade before it closed. |
| **DEV / VAL / OOT / HOLD** | development, validation, out-of-time and hold-out periods; see [methods.md](methods.md). |
| **Pre-registration (prereg)** | a file stating the rule and the pass bar, committed before the test runs. |
| **Random-side P** | the share of coin-flip copies of the same trades that did at least as well as the real rule. Small means the direction carried information. |
| **Bootstrap P** | the share of resampled results with a mean at or below zero. |
| **Walk-forward** | refitting a rule only on data before each test window, then testing on the next window. |
| **Meta-labeling** | a second model that decides which signals of a first rule to take. |
| **POC / value area** | point of control: the price with the most volume in a session's volume profile; value area: the price range holding about 70% of that volume. |
| **FVG** | fair-value gap: a three-candle pattern where the middle candle leaves a gap between the first candle's high and the third candle's low (or the reverse). |
| **OTE** | optimal trade entry: a pullback into the 61.8-79% retracement of a move. |
| **ORB** | opening-range breakout: trading a break of the first minutes' high or low. |
| **PO3** | "power of three": the idea that a session accumulates, sweeps one side of the Asia range, then moves the other way. |
| **VWAP z-score** | the distance of price from the volume-weighted average price, in standard deviations. |
| **EA** | expert advisor: an automated strategy running inside MetaTrader 5. |
| **Swap** | the daily financing charge (or credit) on a forex or CFD position held past the rollover. |
| **Basis / carry** | the difference between a futures price and spot, which builds financing into the futures price. |
| **Roll** | closing an expiring futures contract and opening the next one. |
| **Drift book** | a long-only portfolio meant to earn the slow upward drift of risky assets, here with a 200-day trend filter. |
