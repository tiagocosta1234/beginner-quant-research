# CD: dip reversal in MT5 broker's crypto CFDs: result (2026-10-11)

Pre-registration `PREREG_CRYPTO_DIP.md` (commit 12c6c14), simulator `crypto_dip.py`, output `CRYPTO_DIP_OUTPUT.txt`. Hold-out NOT opened.

## Verdict: no variant passes; closed
| variant | DEV trades / days | per trade | daily t DEV | VAL per trade | VAL daily t |
|---|---|---|---|---|---|
| CD1 long dips, 8 coins | 152 / 54 | +85 bp (win 60%) | -0.31 | +187 bp | +0.66 |
| CD2 long dips, BTC + ETH | 39 / 25 | +29 bp | +0.17 | +230 bp | +1.96 |
| CD3 short spikes, 8 coins | 234 / 133 | -193 bp (win 39%) | -4.36 | +38 bp | +0.77 |
By year, long dips per trade: 2022 +10, 2023 -113, 2024 +262, 2025 +187 bp: positive on average, far too noisy (54 signal days in 3 years,
crashes cluster), daily t near zero.
## Reading
The index dip mechanism shows up in crypto only as a noisy positive average, not as anything a daily t can confirm. Shorting crypto spikes
loses heavily in 2022-24 (spikes continue), but 2025 reverses that, so the mirror (buy spikes) is not a candidate either (it would have
lost in VAL; it would be a new, unregistered hypothesis anyway). No EA.
