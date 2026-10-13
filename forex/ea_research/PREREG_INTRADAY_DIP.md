# Pre-registration: the dip-buying rule at 1 hour and 4 hours on six indices (family ID) (written 2026-10-12, before any intraday bar was evaluated)

the trader: "sim, regista e corre esse teste". Why: the only mechanism with confirmed edge is short-term dip buying in equity indices (ManualDip, RSI(2) on SP/NSDQ/DOW: MT5 broker hold-out PF 6.0, 35 distinct days, but only about 20 entry days a year, so annualised Sharpe of that leg is about 0.3). The question is whether the SAME rule on faster bars keeps its edge per trade while giving hundreds of trades a year. See `REQUIRED_EDGE_OUTPUT.txt`: a 22-day pass needs Sharpe about 6, which only breadth can reach.

## Data and bars
MT5 broker M1 bid/ask (`data_mt5`, 2021-12 .. 2026-10-02, swap-free), indices SP, NSDQ, DOW, DAX, NIKKEI, ASX. Bars built from M1 on the SERVER clock (epoch buckets): H1 = 3,600 s, H4 = 14,400 s. Bar close = bid close of its last minute; bar open ask / bid = ask-open / bid-open of its first minute. Bars with fewer than 30 M1 minutes (H1) or 120 (H4) are dropped. A signal needs the next bar to start within 2 bar lengths (no entry across weekend or session gaps).

## Rule (the daily RSI(2) rule, unchanged, bar count instead of days; no re-tuning)
RSI(2) (Wilder) of bar closes < 10 AND close > SMA(200 bars): signal at the close of bar i. Entry: ASK-open of bar i+1. Exit signal at the close of bar j > i: close > SMA(5 bars) OR RSI(2) > 70 OR j - i >= 5; exit at the BID-open of bar j+1. Long only, one position per index at a time. Return in bp of the entry price, spread paid on both fills, no other cost.
Two trials: ID1 = H1, ID2 = H4, each pooling the six indices.

## Statistic and acceptance (per trial)
Trades of the same calendar day (server date of entry) are averaged into one observation (indices and bars move together; t is conservative). Periods by entry date: DEV 2022-01-01 .. 2024-12-31, VAL 2025, HOLD-OUT 2026-01-01 .. 2026-09-30 (one look, accepted trials only).
Accept: DEV >= 150 observation-days, mean >= +15 bp per day-observation, PF by day >= 1.3, t >= 2.0; VAL mean > 0 and PF >= 1.0; HOLD mean > 0.
Reported, not part of the test: trades per year, and an indicative annualised Sharpe of the daily P&L with a fixed 25,000 USD notional per trade (all business days of the window, zero days included).
A pass is a candidate only: correlation with the pair and ManualDip, an EA with a server-side stop, an MT5 broker real-tick tester run and the pass-speed gate come next. Nothing goes live from this round.

## Honest prior
Moderate that the edge per trade shrinks on faster bars (microstructure noise, wider relative spread overnight when index CFDs are thin), low that it stays at +60 bp or more. The deciding numbers are bp per trade against the spread and the trade count: below roughly +15 bp the spread eats it. Two trials (ID1, ID2).
