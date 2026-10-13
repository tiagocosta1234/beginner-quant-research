# CM1 result: the Bollinger + RSI(2) 4 h rule inverted (short) on crypto (2026-10-12)

Pre-registration: PREREG_CRYPTO_MIRROR.md. Proof window = Binance spot 4 h, 2020-01..2021-11 (unseen), cost = MT5 broker median relative spread per coin once per round trip. Consistency = MT5 broker real fills.

| Window | Trades (per year) | Days | Mean net | PF(day) | t | Indicative Sharpe |
|---|---|---|---|---|---|---|
| **Proof, Binance 2020-01..2021-11** | 252 (131) | 114 | **-104.5 bp** | 0.37 | **-3.90** | -1.10 |
| MT5 broker 2022-01..2024-09 | 239 (87) | 116 | -93.8 bp | 0.44 | -2.66 | -1.40 |
| MT5 broker 2024-10..2026-09 | 225 (112) | 114 | -20.7 bp | 0.79 | -0.74 | -0.72 |

## Verdict: the inverted rule loses in every window (and significantly in two).
Long (MT5 broker) lost -38.5 bp and -29.2 bp; the mirror loses -93.8 bp and -20.7 bp: both sides lose, so the gross edge of this signal on crypto is near zero and the cost is what is left. MT5 broker's crypto spreads are large: BTC 8 bp, ETH 18, XRP 18, BNB 16, BCH 45, SOL 42, ADA 59, LTC 71 bp (median, relative): a 4-hour trade pays 8-71 bp to get in and out, and any edge under about 50 bp per trade disappears on the altcoins. In the 2020-21 bull run the dips the rule sells were bought back up (shorting them lost 104 bp per trade).
Per coin on MT5 broker 2022-26 only BTC (+20 bp) and ETH (+21 bp) are positive, 8 and 18 bp spread; the altcoins lose 53 to 170 bp.
Inverting a losing rule is not an edge: the result needs to beat the spread in the other direction too.
