# TRENDOPEN result: FAIL on DEV (23 Oct 2026 ~00:5x local, local clock)

Pre-registration: `PREREG_TRENDOPEN.md` (sha256 daf453d7..., committed in 49bb9a0f before the run). Output: `TRENDOPEN_DEV_OUTPUT.txt`. Trades: `TRENDOPEN_DEV_TRADES.csv`.

| DEV 2020-2022 (708 days) | Trades | Mean R after costs | Mirror | Excess | Wins | P |
|---|---|---|---|---|---|---|
| Primary (the trader-style bracket) | 521 | **-0.191** (se 0.032) | -0.114 | -0.039 | 61.0% | 0.917 |
| Secondary 1:1 bracket | 521 | -0.206 (se 0.043) | -0.128 | -0.039 | 46.3% | 0.819 |

- Every year is negative: 2020 -0.257, 2021 -0.224, 2022 -0.100. Longs -0.159, shorts -0.232.
- Trading with the 30-minute trend after a pullback does worse than its mirror at the London open on 1-minute gold. Most of the loss is cost: 2 ticks plus 0.15 points is about 0.1-0.15 R at these brackets.
- **VAL (2023-2025) was never loaded**, as pre-registered.
- The read test's "with the trend" and "resumption 10 / 10" splits were noise. Add this to the list of mechanical forms of the setup with no edge.
