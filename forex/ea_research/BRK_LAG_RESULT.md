# BRK-LAG result (breakout day round 31, 2026-10-15 14:05, local clock): the laggard does not catch up
Pre-registration PREREG_BRK_LAG.md, engine brk_lag.py (truncation PASS), rows D:/finance/si_ledgers/BRK_LAG.parquet. When at least half of the other members of a related group (US indices, USD-weak FX, JPY-weak crosses, metals, energy, crypto) have broken out of their opening box in the same direction, enter the member still inside its box at market, stop one box away, hold to the close.
| Z1 laggard entry (net R) | DEV | VAL | 2026 | random side, same minute |
|---|---|---|---|---|
| all groups (n 6,570 / 2,428 / 1,745) | -0.043 (t -1.3) | -0.074 | -0.047 | -0.031 / -0.034 / -0.024 |
By group (DEV / VAL / 2026): US indices +0.030 / +0.031 / -0.035 (control +0.005 / +0.019 / -0.058); USD-weak FX +0.031 / -0.119 / +0.017; JPY crosses -0.055 / -0.163 / +0.024; metals -0.219 / +0.120 / -0.288; energy -0.011 / -0.116 / -0.008; crypto -0.146 / -0.036 / -0.148.
0 of 1 passes; the laggard entry is slightly WORSE than a random side at the same minute: a market that stays inside its box while its group breaks out is, if anything, telling you the group move is not broad. With round 12 (confirmation by the partner: no edge) this closes the cross-market timing family for breakouts.
