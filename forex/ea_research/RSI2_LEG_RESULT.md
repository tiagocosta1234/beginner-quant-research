# RSI(2) leg result: does a third leg (US RSI(2) dips) move P(pass)? (2026-10-12)

Pre-registration: PREREG_RSI2_LEG.md. Leg: 123 trades on 85 days in 2022-26, +67 USD per trade, 12% stopped at 3 sigma, day risk 500 USD x0.75. MIX of the MT5 broker 12-month and FT 2022-26 pools, +560 counted on 12 Oct.

| Config | 30 Nov | 22 Dec | 31 Jan | Breach by 31 Jan |
|---|---|---|---|---|
| 0 live: pair + ManualDip 500 | 42.0% | 58.8% | 75.4% | 2.1% |
| **1 + RSI(2) leg 500** | **43.2%** | **60.4%** | **76.8%** | 2.1% |
| 2 + RSI(2) leg 1000 | 43.0% | 59.9% | 75.9% | 2.6% |
Daily correlation (FT pool): RSI(2) leg vs pair +0.03, ManualDip leg vs pair +0.02, RSI(2) leg vs ManualDip leg +0.15.

## Verdict: +1.5 points by 22 Dec (bar +2.0): not adopted by the registered rule; the leg is real but small.
Criteria: 22 Dec +1.5 (needed +2.0), 30 Nov +1.2 (needed >= 0, met), breach -0.1 (met). A bigger leg (1,000) does not add more, it adds breach. The leg is uncorrelated with both the pair and ManualDip, so it is a clean small add; like ManualDip (+2 to +2.5, bar 3) it can be built if the trader wants every small edge, but it moves the 22 Dec odds from 58.8% to 60.4%, not the order of magnitude a 30-day pass needs.
