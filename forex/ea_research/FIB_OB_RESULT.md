# FO result: the trader's Fibonacci 79% + order-block idea on MT5 broker Nasdaq, causal version (2026-10-12)

Pre-registration: PREREG_FIB_OB.md. Original script on Yahoo MNQ, 60 days: 76 trades, +13,997 USD, PF 2.72, win 52.6%, planned RR 4.88 (four lookaheads in the code, only 60 days). MT5 broker NSDQ M1 bid/ask, spread paid, hold-out unopened.

| Variant | DEV 2022-24 | VAL 2025 | Verdict |
|---|---|---|---|
| FO1 limit order at the fib | 1,304 trades, win 23%, mean **-0.196 R**, PF 0.74, t -1.30 (= -127,684 USD at 500 per trade) | 403, win 18%, mean -0.311 R, PF 0.61, t -2.46 | fail |
| FO2 confirmed close, enter next open | 597 trades, win 41%, mean **-0.088 R**, PF 0.83, t -0.76 (= -26,245 USD) | 196, win 36%, mean -0.224 R, PF 0.63, t -2.85 | fail |
SP and DOW descriptive: the same shape (mean R -0.10 to -0.20, PF 0.73-0.82).
FO1 exits: 822 stopped on the fill bar itself, 705 later stops, 420 end-of-day closes, 130 targets (6%). FO2: 431 stops, 390 end-of-day, 130 targets.

## Verdict: loses in every causal version and every year except 2021-22 noise; the Yahoo +14k came from the lookahead.
- The planned reward:risk is large (FO1 averages 15, FO2 3.1) because the 79% fib sits just above the 20-bar low (a tiny stop) and the target is the last hourly swing high; but a win rate of 18-41% cannot pay for it: only 6% of FO1 trades reach the target.
- The original number needs, in code, the order block detected with the next candle, the swing high known two hours early and the fill confirmed by the bar's close. Remove them and the edge is gone.
- Per year (FO2): 2022 +0.04 R, 2023 -0.06, 2024 -0.25, 2025 -0.22, 2026 +0.12 (143 trades, hold-out not opened).
