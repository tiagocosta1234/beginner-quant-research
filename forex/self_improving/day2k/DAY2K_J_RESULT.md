# DAY2K-J result (2026-10-14): rank every MT5 broker symbol and go long the one most likely to go up - the pick does not beat buying everything

Pre-registration `PREREG_DAY2K_J.md` (commit 2744034b), engine `day2kj.py`, cells `D:\finance\si_ledgers\DAY2KJ_cells.csv`. 34 liquid markets, six rankers (pooled logistic and boosting P(up) from DAY2K-H, trend 20 / 60 / 120 days, 5-day reversal), three holding horizons (10:05 -> 21:55, 16:35 -> 21:55, 10:05 -> 5 trading days later), buy at the ask, sell at the bid, net return in ATR20 units, compared with buying every market the same day. HOLD sealed. No order was placed.

## Gates
Oracle +0.65..+0.94 ATR; shuffled-score placebos 181-183: 0 survivors (best t 1.91 / 2.38 / 1.99). A bug in the oracle control (it shuffled) was found and fixed before any real cell was read.

## Result (18 cells)
S1 survivors **0**. Same-day horizons: the top pick earns -0.03..+0.02 ATR (t -1.4..+1.1) against -0.001 / -0.007 for buying everything, i.e. no better than a random market; win share 47-54%. Five-day horizon: +0.03..+0.18 ATR in DEV' (best trend20 +0.177, HGB +0.151) against +0.066 for buying everything (the markets drifted up), paired difference vs buy-everything t -0.4..+1.0; in 2025 +0.09..+0.28 against +0.10 (trend60 +0.28, t 1.94; paired t 1.4). Win share 50-59%. The classes picked: boosting favours FX crosses (73%), trend favours gold, Bitcoin, USDJPY and US indices.

## Reading
Ranking all the symbols and buying the top one does not choose a market that goes up more than the average market: same-day, it is a coin flip; over five days it earns roughly what the drift gives everything. Nothing to buy on this evidence.
