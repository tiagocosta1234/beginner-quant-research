# BRK-ANATOMY (breakout day round 9, 2026-10-15 11:58, descriptive): what happens after a session breakout on MT5 broker
Script `brk_anatomy.py`, rows `D:\finance\si_ledgers\BRK_ANATOMY.parquet`, chart `D:\finance\scratch\charts\BRK_ANATOMY.png`. Same ~54,000 session opening-range breakouts as round 1 (46 markets, 2022-2026-10-02), each compared with a random entry in the same window with the same stop distance. R = distance to the other side of the 30-minute box.

| | breakout | random entry |
|---|---|---|
| mid price back inside the box within 15 / 60 minutes | **89% / 94%** | (n/a) |
| reaches +1R / +2R / +3R before -1R | 43.1% / 23.8% / 13.4% | 39.9% / 20.8% / 11.3% |
| best favourable move in the first hour (R) | 0.63 | 0.54 |
| net result at the session close (R) | -0.054 | -0.077 |
| one spread, in R | 0.092 | 0.088 |
Median time from the fill to the best price of the session: **235 minutes**. Median box: 15 spreads.

By class (breakouts): cost of a spread in R = indices 0.037, FX 0.071, energy 0.103, metals 0.117, crypto 0.215; close result indices +0.036, FX -0.030, metals -0.039, energy -0.144, crypto -0.211.
By year, breakout minus random (the breakout's own information, R): 2022 +0.097, 2023 +0.005, 2024 +0.012, 2025 -0.018, 2026 +0.027 (indices +0.149, +0.101, -0.003, +0.081, -0.045). The cost of a spread in R rose from 0.061 (2022) to 0.106 (2026): boxes got smaller relative to spreads as volatility fell.

## What this explains
1. **Almost every breakout comes back into the box**: 94% within an hour. A stop inside the box (half-box, retest low) is hit by ordinary noise; the stop has to sit at the other side, and the trade has to tolerate a retest. This is why retest entries (round 2) and tight stops lose.
2. **Breakouts are slow**: the best price comes about four hours after the fill, so fixed 1-2R targets cut the few big winners; hold-to-close is the least bad exit (round 1).
3. **The breakout's information was real in 2022 (+0.10 R, indices +0.15) and close to zero since.** That is the whole story of "breakouts change through time": a 2022 high-volatility trend year, not a cycle that can be followed (rounds 4-7, TRB-ADAPT).
4. **Costs are the other half**: a spread is 0.04 R on indices but 0.07-0.22 R elsewhere, and it has grown since 2022. Indices look best mainly because their boxes are large relative to the spread.
