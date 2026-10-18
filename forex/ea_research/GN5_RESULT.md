# GN5 result - Nasdaq overnight-range breakout (GN3 O1) out of time on 2020-21 NQ futures: FAIL (2026-10-18 11:14 local, local clock, second PC)

Pre-registration `PREREG_GN5.md` (7fdf7d47), engine `gn5.py` and checks `GN5_DRYRUN.txt` (25713895, before the OOT number),
output `GN5_OUTPUT.txt`. Data: Databento CME NQ continuous 1-minute futures (new to this rule), MT5 broker cost model (ask = trade price
+ 1.67 points), roll Mondays excluded (8 in 2020-21).

## Engine checks (passed before the OOT number was read)
- Identity: the copied engine reproduces `gn3.trades("O1")` on MT5 broker trade for trade (1,103 trades) and control for control.
- Port: on 2022-24 the futures version earns +0.065 R a trade against +0.102 on MT5 broker (within the +/-0.06 bar), takes the same side
  on 99% of common days, R correlation 0.95.

## Result
| period | data | n | mean R (t) | win | control | information (t) | longs / shorts |
|---|---|---|---|---|---|---|---|
| 2020 | NQ futures | 205 | +0.084 | | | | |
| 2021 | NQ futures | 229 | +0.114 | | | | |
| **2020-21 (the test)** | NQ futures | 434 | **+0.100 (t +1.31)** | 39% | +0.007 | +0.093 (+1.14) | +0.162 / +0.014 |
| 2022-24 (GN3 DEV) | MT5 broker | 708 | +0.102 (t +1.61) | 37% | -0.025 | +0.127 (+1.84) | +0.111 / +0.091 |
| 2025 (GN3 VAL) | MT5 broker | 222 | +0.061 (t +0.57) | | +0.030 | +0.031 | |

**FAIL: t 1.31 < 1.65 (both years are positive).** By the registered rule O1 is closed; it is not re-tuned and its 2026
hold-out stays sealed.

## What it says
- The Nasdaq overnight-range breakout is the most CONSISTENT breakout found on these markets: about +0.1 R a trade in 2020,
  2021, 2022 and 2023, zero in 2024, +0.06 in 2025, and it beats random entries in every one of those periods. But +0.1 R a trade
  on ~220 trades a year is a Sharpe of about 1.5 at best, its yearly t never reaches significance on its own, and on the
  account it breaches more often than it passes at every size (GN3 account view).
- Pooling 2020-25 after the fact would give a t near 2.5; that pooled number is descriptive only (the windows were not
  pre-registered as one test) and is not a pass.
- An edge of this size cannot reach the trader's pass-speed gate (annual Sharpe ~5 or more) no matter how it is sized.

## Running count
GN1 5 + GN2 4 + GN3 4 + GN4 4 + GN5 1 = 18 of 40 variants in this research window.
