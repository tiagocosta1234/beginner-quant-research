# ManualFVG (ICT fair value gap, DAX) in the MT5 Strategy Tester on MT5 broker real ticks (2026-10-12)

EA `forex/expert_advisors/ManualFVG.mq5` (0 errors / 0 warnings, portable tester `data\mt5_mt5_tester`, never on the live terminal), DAX+, M15, Model=4 every tick based on real ticks, 2025-10-01 .. 2026-09-30, deposit 100,000, InpRiskUSD = 500. Pre-registration: PREREG_ICT_SCAN.md addendum. Runner `verify_manualfvg_mt5.py`, raw log `MANUALFVG_TESTER_LOG.txt`.

| Run | Gaps placed | Trades | Win | Net | PF | Avg per trade | Worst day | Realised max drawdown |
|---|---|---|---|---|---|---|---|---|
| R0 no execution delay | 526 | 354 | 37% | +10,658 | 1.10 | +30.1 USD (+0.060 R) | -1,074 | 11,215 |
| **R1 250 ms delay** | 526 | 354 | 37% | **+10,668** | **1.10** | +30.1 USD (+0.060 R) | -1,074 | **11,195** |
| Python model, same window, slippage 0 / 1 | – | 447 / 447 | – | +40,066 / +35,179 | – | +0.179 / +0.157 R | – | – |
(The execution delay changes nothing because the entries are resting limit orders; the exits are server-side SL/TP.)

**Registered check (R1: >= 100 trades, net > 0, PF >= 1.15): FAIL** (354 trades, +10,668, PF 1.10).

## Reading
- The real-tick run keeps a small positive edge (+0.06 R, PF 1.10) but only about a third of the Python model (+0.16 to +0.18 R) and 93 fewer trades (354 against 447).
- Likely causes, all in the model: the scan took each minute's bid high as max(open, close), which understates true highs, so it saw gaps (and a more favourable geometry) that the real M15 bars do not have; in the EA a new gap while an order is pending is ignored; fills and stops inside a minute are ordered by assumption in the model and by the real ticks in the tester.
- At 500 USD risk the realised drawdown is 11.2k, above the 8,000 USD static buffer of an MT5 broker account; at 250 USD it would be about 5.6k with about 5.3k net a year (about 0.4% a month). Not a candidate for the pass; the DAX lead from the scan does not survive the real-tick test.
- Lesson recorded: a pattern defined on bar highs/lows (gaps, ranges) must not be judged on M1 proxies; the real-tick tester is the arbiter (it already cut S3 to a thin pass).
