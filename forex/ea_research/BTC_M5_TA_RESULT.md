# Four classic technical-analysis rules on 5-minute BTCUSD (MT5 broker bars): result (2026-10-09 15:47 local, 2026-10-09)

Pre-registration `PREREG_BTC_M5_TA.md`, simulator `btc_m5_ta.py`, output `BTC_M5_TA_OUTPUT.txt`, trial ledger `LEDGER.csv` (family btc_m5_ta; ledger 48 of 48 after the trader's second +4 amendment). The 2026 hold-out was NOT opened.
## Verdict: all four rules FAIL acceptance 1 and 2; family closed; NO EA is delivered
| rule | period | trades | net bp/trade | mid-to-mid gross | PF | daily t |
|---|---|---|---|---|---|---|
| C1 48-bar Donchian breakout, 24 h trail | DEV / VAL | 1,202 / 496 | -15.10 / -14.86 | -3.20 / -4.18 | 0.82 / 0.78 | -2.3 / -2.0 |
| C2 Bollinger z=2.5 fade | DEV / VAL | 3,597 / 1,350 | -10.92 / -11.90 | +1.01 / -1.18 | 0.70 / 0.62 | -7.5 / -6.0 |
| C3 EMA24/96 trend | DEV / VAL | 1,514 / 574 | -12.12 / -5.57 | -0.41 / +5.15 | 0.75 / 0.86 | -3.2 / -1.2 |
| C4 RSI14 20/80 fade | DEV / VAL | 851 / 292 | -12.70 / -8.28 | -0.70 / +2.41 | 0.72 / 0.76 | -3.3 / -1.7 |
## Reading
- Mid-to-mid gross (before spread and slippage) is about zero again (-4.2 to +5.2 bp, with the sign changing between DEV and VAL): there is no stable edge in classic TA on 5-minute BTC. Costs (about 12 bp: spread 7.9 bp + 4 bp slippage) then turn a zero into -5.6 to -15 bp a trade.
- C3 in 2025 (net -5.6 bp, PF 0.86, t -1.2, gross +5.2 bp) is the closest to break-even, but its DEV is -12.1 bp: not an edge. Together with the 1-minute family (BTC_M1_TA_RESULT.md) and the earlier BTC studies this closes BTC intraday technical analysis on MT5 broker's cost structure.
- Not delivered: an MQL5 EA. A rule that loses 5-15 bp a trade in both periods is not worth running; the harness is reusable.
