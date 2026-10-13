# Pre-registration: five hypotheses on data we never used (family AL) (written 2026-10-12, before any return was computed)

the trader: "(original wording omitted)". Fincept Terminal is the data source: its scripts point at key-free feeds (alternative.me Fear & Greed, DefiLlama stablecoins, FRED), plus Binance's public funding-rate history. These are not price-derived signals, which is what 13 price-only families lacked.
Files (all pulled 2026-10-12 into `D:\finance\data_macro\alt`): `fng.csv`, `funding_BTCUSDT.csv`, `funding_ETHUSDT.csv`, `stablecoins.csv`; real yields `D:\finance\data_macro\DFII10.csv`.
Instruments on MT5 broker M1 bid/ask (`data_mt5`, 2021-12 .. 2026-10-02, swap-free): BTCUSD+ and ETHUSD+ (24/7) for AL1-AL4, XAUUSD+ for AL5. Spread paid on every fill (long: ask in / bid out; short: bid in / ask out). Return in bp of the entry price. BTC and ETH trades of the same entry date are averaged into one observation. One position per asset at a time (a signal while a position is open is ignored).
Periods by entry date: DEV 2022-01-01 .. 2024-12-31, VAL 2025, HOLD-OUT 2026-01-01 .. 2026-09-30 (one look, accepted trials only).

## Rules (fixed now, one parameter set each)
- AL1 FEAR BUY: Fear & Greed value of day D (published 00:00 UTC on D, describes D-1) <= 25: long BTC and ETH at 00:00 UTC of D, exit 7 days later.
- AL2 GREED SELL: value >= 75: short, exit after 7 days.
- AL3 FUNDING EXTREMES: at each 00:00 UTC funding settlement, trailing 24 h funding = sum of the last three 8 h rates (that settlement included). >= +0.09% (crowded longs, about 33% a year): short for 3 days. <= -0.03%: long for 3 days. Both sides are one trial.
- AL4 STABLECOIN LIQUIDITY: every Monday 00:00 UTC, growth of total stablecoin supply from the observation 29 days before to the observation of the day before (strictly earlier, causal) >= +2%: long BTC and ETH for 7 days.
- AL5 REAL YIELDS -> GOLD: at 15:59 New York on day D, the 5-observation change in the 10-year TIPS yield (DFII10) using observations strictly before D (FRED publishes with a lag): <= -10 bp: long gold; >= +10 bp: short gold; hold 5 trading days.

## Acceptance (one-sided, in the hypothesised direction)
DEV: >= 30 observations, mean net return >= +40 bp (AL1-AL4, crypto spreads and noise are larger) or >= +15 bp (AL5), t >= 1.65; VAL 2025: mean > 0; HOLD-OUT 2026: mean > 0 (accepted trials only). Nothing goes live from this round: an accepted trial is a candidate that still needs a correlation check with the pair, an MT5 broker tester run and the pass-speed question.

## Honest prior
Low to moderate. Fear & Greed and funding are crowded, widely published signals and crypto 2022-26 had one bear and two bull years; stablecoin growth is a slow liquidity proxy; real yields and gold decoupled in 2022-25 (central-bank buying), so AL5 is the least likely. Five trials: about one false DEV pass expected by luck, which is why VAL and HOLD both decide. Trials AL1-AL5 (DEV, VAL).
