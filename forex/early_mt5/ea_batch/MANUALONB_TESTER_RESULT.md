# ManualONB (strategy S3) in the MT5 Strategy Tester on MT5 broker real ticks (2026-10-12)

EA `forex/early_mt5/expert_advisors/ManualONB.mq5` (compiled 0 errors / 0 warnings in the portable tester `D:\finance\mt5_mt5_tester`, never on the live terminal), NSDQ+, M1, Model=4 every tick based on real ticks, 2025-10-01 .. 2026-09-30, deposit 100,000, InpRiskUSD = 300 per trade. Pre-registration: PREREG_NQ3.md addendum 2. Runner `verify_manualonb_mt5.py`, raw log `MANUALONB_TESTER_LOG.txt`.

| Run | Trades | Win | Net | PF | Avg per trade | Equity DD |
|---|---|---|---|---|---|---|
| R0 no execution delay | 103 | 47% | **+1,792 USD** | 1.15 | +7.7 pts (+17 USD) | 2,252 |
| **R1 250 ms delay** | 103 | 47% | **+1,589 USD** | **1.13** | +7.0 pts (+15 USD) | 2,262 |
| Python model, same window, slippage 0 / 1 | 103 / 103 | – | – | – | +12.8 / +11.2 pts | – |

Parity with the Python model: 103 trades each; **100 of 103 on the same day and side** (R0 and R1). On the matched trades the tester averages +9.6 / +9.0 points against Python's +13.4 (slippage 0) or +11.8 (slippage 1): real ticks cost about 4-6 points per trade more than the Python model with zero slippage, about the "2-3 points of slippage" stress case.
**Registered check (R1: >= 30 trades, net > 0, PF >= 1.1): PASS** (103 trades, +1,589 USD, PF 1.13).

## Reading
- The EA does what the Python rule does (same entries), so the earlier Python numbers were about the right strategy.
- The money is small: +1,589 USD in 12 months at 300 USD risk per trade is +1.6% of 100,000 a year. Scaled to the 0.3 NQ equivalent (about 860 USD risk, 2.9x the size) that is about +4,600 a year, about 0.4% a month, consistent with the Python Jan-Sep 2026 figure (+4,558 at slippage 1) and with its weak 2025.
- Real ticks and a 250 ms delay take the edge down to the stress case of the slippage study; the strategy survives the registered check but with a thin margin (PF 1.13).
- It remains a small, uncorrelated leg (daily correlation with the pair -0.01; at 0.2 NQ it added about +3 points of pass probability in the planning simulation, before these real costs), not a way to pass faster. Not on any live account.
