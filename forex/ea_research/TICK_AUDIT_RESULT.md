# Tick audit (2026-10-14 ~23:25): the M1 backtester agrees with MT5 broker real ticks
the trader: "you need to be backtesting properly". Engine `tick_audit.py`, trades `D:\finance\si_ledgers\TICK_AUDIT_trades.csv`. The BRK rules B1 (opening-range breakout) and B4 (previous-day high/low breakout) were re-run on M1 bars for 2025-10-01..2025-12-31 (VAL, unsealed) on 8 markets (EURUSD, GBPUSD, USDJPY, XAUUSD, SP, NSDQ, DAX, BTCUSD); every trade was then replayed on MT5 broker's real ticks (fill at the first tick of the entry minute at the ask/bid, stop on the first tick through it at that tick's price, exit at the first tick of the exit minute).

| cell | trades | mean R, M1 engine | mean R, real ticks | per-trade correlation | median abs difference |
|---|---|---|---|---|---|
| B1 | 537 | -0.031 | -0.049 | 0.996 | 0.004 R |
| B4 | 359 | +0.015 | +0.004 | 1.000 | 0.003 R |
By market the two agree to 0.00-0.05 R (table in the script output). Real ticks are slightly WORSE than the M1 engine (-0.018 and -0.011 R a trade: stop slippage), so the M1 backtests of this session are, if anything, slightly optimistic; they do not hide profit. Same direction as the ManualFVG real-tick test (2026-10-12: the M1 model overstated the edge).
