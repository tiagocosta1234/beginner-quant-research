# R2X result: the daily RSI(2) dip rule on DAX/NIKKEI/ASX and on BTC/ETH (2026-10-12)

Pre-registration: PREREG_R2X.md. Rule unchanged from EV1, each market at its own daily close, MT5 broker bid/ask.

| Trial | DEV 2022-24 | VAL 2025 | HOLD 2026 (opened once) | Verdict |
|---|---|---|---|---|
| R2X1 DAX + NIKKEI + ASX | 56 days, +37.7 bp, PF 1.82, t 1.77 | 21, +10.6 bp, t 0.20 | 21 days, +75.9 bp, PF 2.40, t 1.53 | **nominal pass**, weak: DEV t barely over 1.65, VAL almost zero |
| R2X2 BTC + ETH | 41 days, +20.1 bp, t 0.27 | 17, +60.2 bp, t 0.63 | not opened | fail |

By market 2022-26: NIKKEI 35 trades +97 bp, ASX 32 +19 bp, DAX 38 +14 bp; BTC 40 +72 bp, ETH 30 +7 bp.
Independence: R2X1 entry days coincide within a day with a US RSI(2) day 53% of the time and with a ManualDip day 30%.

## Verdict: R2X1 passes the registered test narrowly; it is a weak leg, not a new engine.
- The effect outside the US is mostly NIKKEI (+97 bp); DAX (+14) and ASX (+19) are barely above their spreads.
- **Breadth does not help the Sharpe:** pooling these five markets with the US block gives DEV Sharpe 1.10 and VAL 1.59, LOWER than the US block alone (1.58 and 2.36). The added trades are worse than the US ones, so adding them dilutes.
- Crypto (BTC +72, ETH +7 bp) is noisy and does not clear DEV.
- Per-trade quality stays in the US indices; the dip effect looks mostly US (and a bit NIKKEI).
