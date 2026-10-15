# COST-OOS result (breakout day round 11, 2026-10-15 12:01): the cost filter avoids losses out of sample but does not create profit
Pre-registration `PREREG_COST_OOS.md`, engine `cost_oos.py`, rows `D:\finance\si_ledgers\COST_OOS.parquet`. Instruments never used today (MT5 broker files): UK100, FRA40, US2000, MSFT, NVDA (XPTUSD / XPDUSD produced no box >= 25 spreads: their spreads are too wide). Net R with an assumed commission of 0.5 median spread per round trip.

Profile by box width (spreads): < 10 **-0.533** (1,434), 10-15 -0.067, 15-25 -0.086, 25-40 +0.026, 40-60 +0.040, > 60 -0.063. All boxes -0.133.
| rule | trades | net R (with commission) | trade t / daily t | positive instruments | by year 2022 / 23 / 24 / 25 / 26 | gates |
|---|---|---|---|---|---|---|
| K2 box >= 40 spreads | 1,614 | +0.009 (+0.000) | +0.01 / -0.07 | 2 / 5 (NVDA +0.137, MSFT +0.050; FRA40 -0.068, US2000 -0.043, UK100 -0.007) | +0.016 / -0.023 / -0.007 / +0.177 / -0.057 | nnY |
| K1 box >= 25 spreads | 3,160 | +0.025 (+0.013) | +0.65 / -0.94 | 4 / 5 | +0.063 / -0.028 / +0.017 / -0.072 / +0.026 | nYY |
0 of 1 primary pass.

Reading: the COST half of round 10 travels (narrow boxes lose heavily everywhere: -0.53 R below 10 spreads here, -0.15..-0.23 R on MT5 broker; wide boxes cut the loss to about zero), the INFORMATION half does not (+0.08 R on MT5 broker is about 0 here). Rule for any breakout trading: never trade a box narrower than about 25 spreads; but a wide box is a necessary condition, not an edge.
