# BRK-CAL result (breakout day round 32, 2026-10-15 14:06, local clock): calendar days do not switch breakouts on
Pre-registration PREREG_BRK_CAL.md, engine brk_cal.py, trades = round 1 session breakouts held to the close (BRK_EXITS.parquet).
| cell (net R) | DEV | VAL | 2026 | same markets, other days DEV / VAL / 2026 |
|---|---|---|---|---|
| C1 turn of the month, indices (n 838 / 274 / 227) | +0.029 (daily t -0.6) | +0.067 | +0.090 | +0.054 / +0.054 / -0.071 |
| C2 Monday-Wednesday after options expiry, indices (n 609 / 200 / 150) | -0.045 (t -0.5) | -0.078 | -0.131 | +0.064 / +0.079 / -0.024 |
| C3 first trading day of the month, all markets (n 1,569 / 546 / 456) | +0.113 (daily t -2.5) | +0.058 | +0.070 | -0.039 / -0.082 / -0.042 |
0 of 3 pass. Post-OPEX index breakouts are worse than other days (the pin-release story does not hold). C3 fails the pre-registered daily t (equal-weighting days lets the weekend crypto-only month starts, which lose, dominate); at the trade level it is +0.113 (t 2.2) / +0.058 (t 0.8) / +0.070 (t 0.8), above other days in all three periods, carried by FX and indices in 2022-24 (+0.19 each). By trading day of the month (DEV): day 1 +0.109, day 2 +0.039, day 3 +0.017, day 4 -0.012, day 5 -0.023; in 2025 and 2026 the order is not kept (day 2-3 best). With round 4's month-opening-range lead this is a weak, post hoc "start of the month" observation, not an edge.
