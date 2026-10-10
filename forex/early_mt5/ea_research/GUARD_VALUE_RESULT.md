> **WITHDRAWN 2026-10-09 (local clock 11:59): the tables in this file that include the PROFIT cap, the pass lock or the carry-over of closed positions are WRONG. The minute-level carry-over model kept counting the floating P&L of positions the guard had already closed ("phantom" floating profit), which re-triggered the profit cap on the following days and inflated every profit-cap result (sum of daily P&L +48%, days above +2,000 from 6 to 49). Superseded by `forex/early_mt5/ea_research/clean_guard_sim.py` and `CLEAN_GUARD_RESULT.md`. Loss-cap-only breach figures were conservative.**
# What each lever is worth for "pass by 30 November" (37 business days), 2022-26 starts (local clock about 11:55, 2026-10-09)

`guard_value.py` (output `GUARD_VALUE_OUTPUT.txt`; its optional last block, the last 12 months at a 300-business-day life, crashed on an empty sample and is not needed: the 12-month tick-level comparison is in `mt5data/SIZING_TICK_2026.txt`). MT5 broker-based series, minute-level halts, every start day.

| configuration | pass by 30 Nov | breach by 30 Nov | pass over a 300-bd life | breach over a 300-bd life |
|---|---|---|---|---|
| x1.0, NO guard (the EAs as published) | 12.8% | 1.9% | 70.8% | 5.1% |
| x1.0, both daily caps (what runs today) | 22.4% | 0.0% | 75.4% | 5.4% |
| x1.0, caps + pass lock | 23.8% | 0.0% | 76.5% | 5.4% |
| x1.4, NO guard | 26.9% | 18.8% | 71.6% | 28.4% |
| x1.4, both daily caps | 40.8% | 2.9% | 89.7% | 10.3% |
| x1.4, caps + pass lock | 43.9% | 2.9% | 89.7% | 10.3% |

Reading (ranked by gain in P(pass by 30 Nov) from the 12.8% starting point): (1) the two daily caps, ALREADY APPLIED: 12.8% -> 22.4% (x1.75) at the live size, and at 1.4x they turn 26.9% / 18.8% breach into 40.8% / 2.9%; (2) size 1.0 -> 1.4 on top of the caps, NOT applied: +18.4 points (22.4% -> 40.8%); (3) the pass lock, NOT applied: +1.4 to +3.1 points, free. All three together (1.4x + caps + lock): 43.9%, 3.4 times the starting point. Without the caps, 1.4x would not be usable: 18.8% of attempts breach by the deadline.
