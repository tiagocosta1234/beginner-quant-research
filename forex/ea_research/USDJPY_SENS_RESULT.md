# USDJPY London breakout: sensitivity map (2026-10-15 14:20, local clock; diagnostic, not a test)
Script `usdjpy_sens.py`, table `D:/finance/si_ledgers/USDJPY_SENS.csv`. Same engine as PRESAMPLE L1 (OCO stop orders for 150 min after the box, stop at the other side, no target), 27 neighbours: open 07:00 / 08:00 / 09:00 London x box 15 / 30 / 60 min x exit 15:00 / 17:00 / 20:00 London. Mean net R a trade; 2020-21 on HistData (+ MT5 broker spread), 2022-26 on MT5 broker bid/ask.
| open | box / exit | 2020-21 | 2022-24 | 2025 | 2026 |
|---|---|---|---|---|---|
| **08:00** | 15 / 15:00 | +0.120 | +0.229 | +0.037 | +0.231 |
| **08:00** | 15 / 17:00 | +0.175 | +0.205 | +0.042 | +0.139 |
| **08:00** | 15 / 20:00 | +0.240 | +0.199 | +0.068 | +0.176 |
| **08:00** | 30 / 15:00 | +0.255 | +0.148 | +0.091 | +0.244 |
| **08:00** | **30 / 17:00 (the tested rule)** | **+0.260** | **+0.146** | **+0.108** | **+0.114** |
| **08:00** | 30 / 20:00 | +0.326 | +0.137 | +0.128 | +0.114 |
| **08:00** | 60 / 15:00 | +0.131 | +0.211 | +0.211 | +0.093 |
| **08:00** | 60 / 17:00 | +0.188 | +0.190 | +0.154 | +0.047 |
| **08:00** | 60 / 20:00 | +0.240 | +0.216 | +0.122 | +0.091 |
| 07:00 (9 cells) | range | +0.04..+0.28 | +0.03..+0.21 | -0.20..+0.01 | -0.27..+0.10 |
| 09:00 (9 cells) | range | +0.13..+0.25 | +0.06..+0.15 | -0.17..+0.01 | +0.01..+0.35 |
**All 9 cells of the 08:00 London open are positive in all four periods** (12 of 27 overall). The result is a plateau around the London open (box length and exit time barely matter), not a single tuned point; one hour earlier or later it weakens and turns negative in 2025. 2025 is the weakest year everywhere (+0.04..+0.21 at 08:00).
Reading: the 08:00 London USDJPY breakout is the most robust breakout found on MT5 broker data, and the only one confirmed out of time. It is still a small edge (+0.1..+0.25 R a trade) with long drawdowns, chosen from 46 markets.
