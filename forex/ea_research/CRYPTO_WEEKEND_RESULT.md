# W: crypto on weekends (BTC + ETH on MT5 broker): result (2026-10-10, local local clock)

Pre-registration `PREREG_CRYPTO_WEEKEND.md` (commit 164922f, before any statistic; amendment for a W3 timing bug found in the first run, which was discarded and its ledger rows removed), script `crypto_weekend.py`, output `CRYPTO_WEEKEND_OUTPUT.txt`. Hold-out NOT opened. MT5 broker has almost no weekend crypto data in 2022, so DEV is in practice 2023-24.

## Verdict: all three fail acceptance 1
| trial | DEV (2023-24 in practice) | VAL 2025 |
|---|---|---|
| W1 long Saturday 01:05 -> Sunday 22:50 | 89 weekends, 55% up, +25.6 bp, t +1.30, worst -673 bp | 52 weekends, 58% up, +20.5 bp, t +0.47, worst -858 bp |
| W2 fade a big Saturday-to-Sunday-noon move | 14 trades, -58.5 bp, t -1.17 | 10 trades, -78.3 bp |
| W3 fade a 2-sd 4-hour move on weekends | 33 trades, 58% wins, +16.0 bp, t +0.93 | 29 trades, 41% wins, +9.0 bp, t +0.24 |
Diagnostic: the same 4-hour fade on WEEKDAYS loses (-19.5 bp, t -2.39 in DEV; -40.9 bp, t -3.64 in 2025): on weekdays a big 4-hour crypto move tends to CONTINUE, on weekends it may revert slightly. Interesting, but the weekend sample (33 + 29 trades) is far too small to prove it.

## Reading
- A weekend long in BTC/ETH was up 55-58% of the time with a positive average, but a single weekend can lose 7-9% (-673 / -858 bp). At MT5 broker's 1%-per-idea size that is about 12,000 USD of notional, worth about 3 USD a weekend on average. It cannot help the test.
- The idea of earning on Saturday and Sunday fails on size, not on existence: weekend crypto moves are large and nearly random, and the spread (8 bp BTC, 16 bp ETH) is paid on each one.
