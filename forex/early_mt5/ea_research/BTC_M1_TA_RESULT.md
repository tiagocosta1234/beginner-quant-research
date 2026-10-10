# Four classic technical-analysis rules on 1-minute BTCUSD (MT5 broker bars): result (2026-10-09 15:43 local, 2026-10-09)

Pre-registration `PREREG_BTC_M1_TA.md` (with Amendment 1 on stop sizing, written before any trial), simulator `btc_m1_ta.py`, output `BTC_M1_TA_OUTPUT.txt`, trial ledger `LEDGER.csv` (family btc_m1_ta; ledger 44 of 44 after the trader's +4 amendment). The 2026 hold-out was NOT opened.
## Verdict: all four rules FAIL acceptance 1 and 2 by a wide margin; family closed; NO EA is delivered
| rule | period | trades | net bp/trade | mid-to-mid gross | PF | daily t |
|---|---|---|---|---|---|---|
| B1 120-bar range breakout | DEV / VAL | 8,542 / 3,540 | -11.45 / -12.06 | +0.44 / -1.37 | 0.59 / 0.52 | -16.6 / -13.5 |
| B2 Bollinger z=3 fade | DEV / VAL | 7,888 / 2,782 | -11.16 / -9.58 | +0.83 / +1.13 | 0.48 / 0.47 | -20.6 / -12.5 |
| B3 EMA20/100 cross | DEV / VAL | 7,895 / 3,136 | -11.98 / -11.55 | -0.17 / -0.82 | 0.54 / 0.51 | -15.5 / -11.0 |
| B4 RSI14 15/85 | DEV / VAL | 1,434 / 450 | -10.13 / -8.42 | +2.10 / +2.11 | 0.57 / 0.55 | -6.4 / -3.9 |
## Reading (CORRECTED 2026-10-09 15:47: the first version added back TWO spreads; a round trip pays ONE spread, half at each fill, plus 2 bp slippage per fill)
- Mid-to-mid gross (before spread and slippage) is about ZERO in every rule and period (-1.4 to +2.1 bp): there is no edge to be eaten by costs. Costs then take about 12 bp a trade (spread 7.9 bp + 4 bp slippage): net -8 to -12 bp, PF about 0.5, daily t between -4 and -21.
- MT5 broker's BTCUSD costs make even a real small edge untradable at these horizons, but here the rules had none.
- Not delivered: an MQL5 EA for any of these rules. The harness (rules, fills, costs) is reusable.
