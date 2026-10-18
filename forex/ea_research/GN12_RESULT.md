# GN12 result - post-release breakouts on scheduled US event days do not pay (0 of 4)

Run 2026-10-18 14:58 local (local clock, second PC PC-2). Pre-registration `PREREG_GN12.md` (commit d46f3f1b), engine `gn12.py`,
dry run `GN12_DRYRUN.txt` (truncation PASS x4), output `GN12_OUTPUT.txt`. Net R a trade, MT5 broker bid/ask, 2026 hold-out sealed.

| trial | DEV 2022-24 | info over random (t) | same rule, other days | years | VAL 2025 | verdict |
|---|---|---|---|---|---|---|
| K1 NSDQ, CPI / NFP / FOMC | +0.014 (t 0.07), n 89 | +0.110 (0.57) | +0.181 | -0.26 / +0.27 / +0.01 | -0.142 (n 29) | FAIL |
| K2 XAUUSD, CPI / NFP / FOMC | +0.059 (t 0.62), n 87 | +0.175 (1.67) | -0.011 | -0.09 / +0.07 / +0.19 | -0.043 (n 28) | FAIL |
| K3 NSDQ, Treasury auctions | +0.260 (t 1.99), n 178 | +0.263 (1.75) | +0.077 | +0.63 / +0.15 / -0.01 | -0.013 (n 59) | FAIL |
| K4 XAUUSD, Treasury auctions | -0.021 (t -0.21), n 175 | -0.046 | -0.069 | +0.03 / -0.30 / +0.21 | -0.169 (n 59) | FAIL |

## What it shows
- **Event days are not better breakout days.** On CPI / NFP / FOMC days the Nasdaq post-release breakout earned +0.01 R against
  +0.18 R for the same rule on ordinary days; gold's +0.06 R is noise and negative in 2025. FOMC days were negative in both
  markets. With the release absorbed in seconds (TICK_EVENTS), the rest of the day is not a trend the box can catch.
- **Nasdaq on auction days (+0.26 R, t 1.99) is the 2022 effect again:** +0.63 R in 2022, +0.15 in 2023, -0.01 in 2024 and -0.01 in
  2025, the same decay as every breakout family (BREAKOUT_KNOWLEDGE fact 4).
- Gold's auction-day box is narrow (19 spreads) and loses.

## Account view (2022-25 trades, from 95,472, MT5 broker rules)
Best row K3 at $500 a trade: 0.0% pass / 8% breach by 22 Dec, 4.1% / 30% by 30 Jun 2027. Nothing usable.

## Running count
GN1-GN12: 37 of 40 variants of this research window used, 0 passes.
