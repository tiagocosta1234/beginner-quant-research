# UJ_CONF result - USDJPY London breakout: no confluence clears the bar, two repeat in 2025 (0 of 9 kept)

Run 2026-10-17 23:53 local (local clock, second PC). Pre-registration `PREREG_UJ_CONF.md` (registered 23:52, frozen by sha256 at 23:53:02
in `C:\work\scratch\uj_conf_freeze.txt`). Engine `uj_conf.py` (reproduces `usdjpy_sens.run` exactly: 1,219 of 1,219 trades,
max |dR| 0), output `UJ_CONF_OUTPUT.txt`. Base at today's cost (0.6-pip spread floor): DEV 765 trades +0.103 R, VAL 253 +0.108 R.
No 2026 subset was looked at.

| confluence | DEV with: n, R | DEV without: n, R | t | kept | 2025 with / without |
|---|---|---|---|---|---|
| C1 break also beyond the Asian range | 204, +0.150 | 561, +0.086 | +0.37 | no | -0.008 / +0.146 |
| C2 with the 20-day trend | 388, +0.113 | 377, +0.094 | +0.12 | no | +0.209 / -0.003 |
| **C3 risk-on alignment (NSDQ overnight move agrees)** | 376, **+0.239** | 389, **-0.027** | +1.63 | no | **+0.222 / -0.013** |
| C4 USD-wide alignment (EURUSD + GBPUSD) | 372, +0.123 | 393, +0.085 | +0.23 | no | +0.171 / +0.037 |
| **C5 unmitigated FVG inside the box** | 261, **+0.277** | 504, **+0.014** | +1.44 | no | **+0.250 / +0.036** |
| C6 box not in the smallest third (>= 0.125 ATR) | 510, +0.106 | 255, +0.098 | +0.04 | no | +0.115 / +0.091 |
| C7 late trigger (> 8 min after 08:30) | 262, -0.005 | 503, +0.160 | -1.06 | no | -0.047 / +0.201 |
| C8 not stretched over 5 days | 499, +0.158 | 266, +0.000 | +1.01 | no | +0.178 / -0.042 |
| C9 Asian session moved the same way | 376, +0.176 | 389, +0.033 | +0.88 | no | +0.151 / +0.068 |

## Reading
- By the pre-registered rule nothing is kept (no t >= 2.0 on DEV): with ~375 trades per side, a 0.25 R gap is still inside the
  noise of a rule whose trades range from -1 R to +8 R.
- Two flags behave the same way in 2025 as in 2022-24, at a similar size: **C3 risk-on alignment** (+0.26 R gap in DEV,
  +0.24 in 2025) and **C5 FVG in the box** (+0.26, +0.21). C8 (not stretched) and C9 (Asia aligned) also repeat, more weakly.
  This is a candidate list, not a result: they were not kept by the rule, and 2025 is now seen.
- C7 (the late trigger, LDN3F filter F2) is WRONG for USDJPY in both periods (-0.005 vs +0.160, 2025 -0.047 vs +0.201): the
  LDN3F forward test applies it to all markets; for USDJPY it removes the better trades.
- The clean next test for C3 and C5: a new pre-registration run once on data never used for them, i.e. the 2020-21 HistData
  files (on the main PC) and/or the 2026 hold-out, with no change to the definitions.

## In the account's environment (base rule, USDJPY, 2022-25 trades, from 95,472, MT5 broker rules; pass% / breach%)
| risk, cost | R a trade | 22 Dec | 31 Mar 2027 | 30 Jun 2027 |
|---|---|---|---|---|
| $150, bars | +0.104 | 0.0 / 2 | 0.2 / 14 | 1.5 / 20 |
| $250, bars | +0.104 | 0.1 / 20 | 3.6 / 38 | 10.1 / 45 |
| $150, real-tick haircut 0.06 R | +0.044 | 0.0 / 5 | 0.1 / 22 | 0.6 / 32 |
| $250, real-tick haircut 0.06 R | +0.044 | 0.1 / 27 | 2.0 / 50 | 5.3 / 59 |
Breach stays 4-50 times more likely than a pass at every size.
