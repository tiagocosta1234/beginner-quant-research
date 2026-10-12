# NQ3 result: the three Nasdaq strategies of the Matio video on MT5 broker NSDQ (2026-10-12)

Pre-registration: PREREG_NQ3.md (declared deviations: TWAP instead of VWAP because the MT5 broker M1 files have no volume, A15 = mean of 15 true ranges, ADX(14) on own bars). USD per 1 NQ (20 USD per point), spread paid, TP/SL minute by minute. Out-of-sample window of the authors = 2023 on.

| Strategy | 2022 | DEV 2023-24 | VAL 2025 | HOLD 2026 | Verdict |
|---|---|---|---|---|---|
| S1 Vault Break | 199 tr, +56 USD, PF 1.13 | 408 tr, win 63%, **+17 USD**, PF 1.04 | 206, +0 USD, PF 1.00 | not opened | fail (needs +30, PF 1.2) |
| S2 VWAP pullback + ADX | 174, -125 USD, PF 0.47 | 422, win 76%, **-82 USD**, PF 0.44 | 219, **-79 USD**, PF 0.58 | not opened | fail, loses every year |
| S3 Overnight bias ORB | 119, +367, PF 1.42 | 210, win 52%, **+385 USD (+19.2 pts)**, PF 1.61, t 2.82 | 104, **+22 USD**, PF 1.02 | 76, **+231 USD**, PF 1.23, t 0.71 | **accepted** (VAL close to zero) |
Video claims: S1 win about 67% with +112 USD per trade, S2 about +121 USD, S3 average +1.4 R: only S3 reproduces in sign.

S3 by year (avg USD per trade): 2022 +367, 2023 +329, 2024 +428, **2025 +22**, 2026 +155. 513 trades in 4.75 years (about 108 a year), median trade +1.0 point, mean +13.5, best +667 points: 20 targets in 513 trades, the profit is carried by a few big winners.
Portfolio of the three at 5 micro each (the video's sizing), guard 1,500, fresh account: **pass 3.2% in 22 business days, 8.4% in 44, 11.3% in 60; breach 12.6% / 36.4% / 48.4%**; worst floating day -4,031 USD; daily correlations S1-S2 0.01, S1-S3 0.25, S2-S3 0.05 (the "< 0.25" claim holds).

## S3 as a leg of the installed system (fresh account, MIX of pools)
| | pass 22 bd | 44 | 60 | breach 44 | breach 60 |
|---|---|---|---|---|---|
| installed (pair x1.5 + ManualDip) | 17.0% | 47.2% | 61.4% | 1.4% | 2.1% |
| + S3 at 0.2 NQ (2 micro) | **19.8%** | **50.4%** | **64.5%** | 2.5% | 3.4% |
| + S3 at 0.3 NQ | 20.7% | 49.9% | 63.1% | 3.9% | 5.2% |
| + S3 at 0.5 NQ | 20.3% | 45.1% | 56.3% | 10.1% | 13.2% |
| + S3 at 1.0 NQ | 12.3% | 23.3% | 27.8% | 42.8% | 51.9% |
S3's daily correlation with the installed pair (FT pool): -0.01. S3 alone: best 17.1% pass in 44 bd at 1 NQ with 27.6% breach.

## Verdict
- The video's claim (about 40% pass alone, 5 days together) is not reproduced: S1 is flat, S2 loses, the three together fail the test far more often than they pass.
- S3 is the only candidate and a weak, lumpy one: strong in 2022-24, about zero in 2025, positive but small in 2026 (t 0.71). As a leg it adds about +3 points of pass probability at 2 micro with 1 to 1.5 points more breach: similar to what ManualDip and the RSI(2) leg add, uncorrelated with the pair.
- Next if the trader wants it: an EA (15 m, one trade a day), an MT5 broker real-tick tester run, then a pass-speed decision. Not built.

## Addendum result: NSDQ+ with a 1.67-point spread floor and slippage (2026-10-12)
S3 at 1 NQ per trade, USD per trade (PF) | totals at 0.3 NQ:
| Slippage on market fills | DEV 2023-24 | VAL 2025 | 2026 Jan-Sep (seen) | 0.3 NQ totals: 2023 / 2024 / 2025 / 2026 to Sep | Rule |
|---|---|---|---|---|---|
| 0 pt (spread floor only) | +379 (1.60) | +22 (1.02) | +231 (1.23) | +8,783 / +15,090 / +691 / +5,278 | accepted |
| **1 pt (central)** | +317 (1.48) | **-10 (0.99)** | +200 (1.19) | +7,940 / +12,057 / **-306** / +4,558 | **not accepted** (VAL < 0) |
| 2 pt | +261 (1.38) | -42 (0.96) | +168 (1.16) | +5,640 / +10,783 / -1,308 / +3,834 | not accepted |
| 3 pt | +219 (1.31) | -74 (0.93) | +136 (1.13) | +4,071 / +9,710 / -2,297 / +3,104 | not accepted |
S1 at 1 pt: DEV -11 USD (PF 0.98); S2 at 1 pt: DEV -107 USD (PF 0.34). Both worse.
Each point of slippage costs about 60 USD per trade at 1 NQ. Verdict: S3 keeps a positive edge in 2022-24 and 2026 but is exactly break-even in 2025 with one point of slippage and loses with more; it is no longer accepted by the registered rule. Needs the real MT5 tester run (real ticks since 2025-09-25, execution delay) before any weight is put on it.
