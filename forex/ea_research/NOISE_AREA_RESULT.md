# NA: noise-area intraday momentum on SP / NSDQ / DOW (MT5 broker M1 bid/ask): result (2026-10-11)

Pre-registration `PREREG_NOISE_AREA.md` (commit 5474ab2), simulator `noise_area.py`, output `NOISE_AREA_OUTPUT.txt`.
**Bug fixed before the valid run:** the first run (commit 8f1165a) took `.values` of a tz-aware series, which gives UTC, so the
"09:30-16:00 New York" session was really 09:30-16:00 UTC. Its numbers (all negative) are void and its ledger rows were removed.
Earlier scripts (index_intraday_mom, leo_ema_pullback, orb_gold, edge_h, macro_ta) use the `.dt` accessors and are not affected.

## Verdict (valid run): NA3 passed development, FAILED the 2026 hold-out; family closed
| variant | DEV 2022-24 bp/day | DEV t | VAL 2025 bp/day | VAL t | HOLD 2026 |
|---|---|---|---|---|---|
| NA1 SP+NSDQ+DOW | +2.87 | +1.89 | +0.73 | +0.25 | not opened |
| NA2 band-only exit | +3.01 | +1.99 | +0.89 | +0.31 | not opened |
| NA3 NSDQ alone | +5.21 | +2.53 | +2.34 | +0.48 | **-1.45 bp/day, t -0.47** |

By year NA3: 2022 +7.5, 2023 +5.1, 2024 +3.1, 2025 +2.3, 2026 -1.5 bp/day: a steadily decaying effect, gone in 2026.
## Reading
The paper's intraday momentum existed on MT5 broker's NSDQ CFD in 2022-23 and faded year by year; the one-look hold-out says it is not there now.
No EA.
