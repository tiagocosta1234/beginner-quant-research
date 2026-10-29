# ORB11_RESULT - the trader's 30-minute London / New York opening-range breakout with a 1:1 target, all 46 MT5 broker symbols (2026-10-15, local clock 16:05)
Pre-registration `PREREG_ORB11.md` (commit 78622044). Code `orb11.py`, output `ORB11_OUTPUT.txt`, trades `data/si_ledgers/ORB11.parquet`, cells `ORB11_cells.csv`.

## Verdict: 0 of 92 cells pass; both sessions lose in every year
Rule: box = first 30 minutes (08:00-08:30 London, 09:30-10:00 New York), first touch of the high -> long, of the low -> short, stop at the other side, target 1R, else exit at the session end; MT5 broker real bid/ask, M1. 109,024 trades 2021-12..2026-10.
| session | 2022-24 | 2025 | 2026 | random entry, same R (2022-24) | win rate | daily t 2022-25 |
|---|---|---|---|---|---|---|
| London | **-0.067 R** | -0.110 | -0.069 | -0.092 | 46.1% | -10.5 |
| New York | **-0.048 R** | -0.067 | -0.081 | -0.077 | 47.0% | -9.7 |
By year London -0.054 (2022), -0.067, -0.079, -0.110, -0.069; New York -0.026, -0.049, -0.066, -0.067, -0.081: negative every year and getting worse.

By class (2022-01..2026-10, net R a trade / random / win rate): crypto -0.24 / -0.25 / 38% (London), -0.21 / 39% (NY); energy -0.14 / -0.09; FX -0.042 (London), -0.035 (NY) vs random -0.07; metals -0.063 / -0.042; indices -0.080 (London), **+0.006 (NY, the only class at break-even)**.

Best cells (bar t >= 3.06 and positive in 2022-24, 2025 AND 2026): EURUSD NY +0.082 / +0.114 / **-0.043** (t 3.12), USDJPY NY +0.091 / +0.058 / -0.029, NSDQ NY +0.081 / +0.069 / -0.005, XAUUSD London +0.041 / +0.133 / -0.098. Every one of them turns negative in 2026. Only 3 of 92 cells are positive in all three periods (fewer than chance would give).

## Reading
- The breakout is a little better than a random entry with the same stop and target (+0.02-0.04 R), the same finding as this morning, but a 1:1 trade needs a win rate above 50% plus the spread, and it wins 46-47%. 94% of breakouts come back into the box within an hour (BRK_ANATOMY), so a stop at the other side of a 30-minute box is hit often and the 1R target does not pay for it.
- The fill-minute bound (optimistic engine) changes the means by at most 0.003 R.
- No real-tick replay was needed to reject: real MT5 broker ticks are about 0.03 R a trade worse than this M1 engine for breakouts (TICK_GAP_RESULT), so they can only lower these numbers.
- On the account: at 1,000 USD a trade the London leg alone would have lost about 67 USD a trade on average in 2022-24, 110 in 2025.
