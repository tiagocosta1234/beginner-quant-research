# TRB-BEST (2026-10-15 ~11:20 local): the best breakout the grid finds in 2022-24, and what it did in 2025 and 2026
the trader: "is this truly the best the breakouts can get? I don't believe it". Script `trb_best.py` (cache `data\tmp\trb_cache_2026`, table `data\si_ledgers\TRB_BEST.csv`). For each of the 46 MT5 broker, the configuration with the highest total net R over 2022-2024 (at least 150 trades) out of the 2,808 TRB variants (39 box times x 3 box lengths x both/long/short x 8 stop/target sets; stop orders at the box, real bid/ask), then the same configuration in 2025 and 2026-01..10-02 (2026 already opened for the breakout family in ORB_TREND_2026_RESULT.md).

| | in-sample 2022-24 | 2025 | 2026 (9 months) |
|---|---|---|---|
| average R per trade of the 46 "best" breakouts | +0.101 | -0.117 | -0.125 |
| markets whose best breakout made money | 41 / 46 | 11 / 46 | 9 / 46 (2 / 46 in both years) |
| top 10 in-sample, total at $1,000 per trade | +$1,521,587 (+0.221 R/trade) | -$100,665 (-0.060) | -$190,862 (-0.163) |
| USDJPY best (15:00 server, 30-min box, both sides, stop 1 box, target 3) | +0.296 R, +$208,754 | +0.018, +$4,350 | -0.114, -$21,590 |
| NSDQ best (same slot) | +0.265 R, +$189,079 | -0.026, -$6,507 | -0.121, -$23,443 |
| XAUUSD best (16:00 server, 30-min box, both, stop 1, target 2) | +0.107 R, +$82,680 | -0.004, -$1,106 | -0.046, -$8,859 |

Reading: the best breakouts in hindsight are spectacular (USDJPY +$209k, the top ten +$1.5M at $1,000 a trade over 2022-24), and almost none of them keeps working: 9-11 of 46 make money in each later year, which is what chance gives, and the average flips from +0.10 R to -0.12 R a trade. The in-sample winners cluster on the 15:00-15:30 server box, the half hour that ends at the 08:30 New York data release: in the 2022-24 inflation shock, US data moves ran; since 2025 they do not. Patterns do change through time, as the trader says, but the change was not visible in advance (ORB-REFINE regime rules E/F failed) and selecting on past results picks the pattern that is about to stop.
