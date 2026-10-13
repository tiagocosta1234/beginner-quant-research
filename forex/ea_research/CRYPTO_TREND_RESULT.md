# Daily trend following on MT5 broker's crypto CFDs: result (2026-10-09 ~09:30 local)

Pre-registration `PREREG_CRYPTO_TREND.md` (with Amendment 1: the crypto M1 history on MT5 broker starts 2022-04-03, so DEV is about 2.6 years), simulator `crypto_trend.py`, ledger `LEDGER.csv`. The 2026 hold-out and the ETH / LTC / XRP replication were NOT opened.

## Verdict: C1 fails the registered bars; round closed
| trial (BTCUSD+) | DEV mean bp/day | daily t | Sharpe | max DD | flips | VAL 2025 mean bp/day | t | Sharpe |
|---|---|---|---|---|---|---|---|---|
| C1 PRIMARY 50-day, long or short | +7.79 | +0.84 | +0.54 | 68.6% | 45 | +3.21 | +0.28 | +0.28 |
| C2 20-day | -0.05 | -0.01 | 0.00 | 92.8% | 99 | -2.88 | -0.25 | -0.25 |
| C3 100-day | +10.33 | +1.22 | +0.78 | 82.1% | 28 | +2.20 | +0.19 | +0.19 |
| C4 long or flat | +12.19 | +1.88 | +1.20 | 31.9% | 44 | +1.91 | +0.29 | +0.29 |
| C5 C1 + 3 ATR trailing stop | +10.48 | +1.29 | +0.82 | 55.8% | 62 | +2.50 | +0.24 | +0.24 |
| C6 C1 volatility-targeted | +10.21 | +1.15 | +0.73 | 53.4% | 45 | +5.26 | +0.39 | +0.39 |
Registered bars for C1: DEV t >= 2.0 (got +0.84), VAL t >= 0.5 (got +0.28). Returns are per unit of notional at unit leverage; the 69% / 82% drawdowns are why MT5 broker notional would have to be 20-40% of equity.
## Reading
BTC trend following has the right sign in DEV and VAL for every variant except the 20-day rule, but the Sharpe is 0.5-0.8 in DEV and 0.2-0.4 in VAL, far below the 1.15 a DEV t of 2.0 needs over 2.6 years, with drawdowns that would break MT5 broker's 8% floor at any useful size. The one variant that looks good in DEV (long-only, t +1.88, Sharpe 1.2) is a bull-market artefact that disappears in VAL (t +0.29) and was not eligible for acceptance. Not accepted, no EA.
