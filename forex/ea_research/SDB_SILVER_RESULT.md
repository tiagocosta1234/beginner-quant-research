# Frozen SDB on silver (XAGUSD+): result (2026-10-09 ~10:15 local; CORRECTED ~10:19)

**CORRECTION (~10:19):** the first version of this report used a wrong sign when deducing each trade's side from its profit (`np.sign(move)` instead of `+1`), which flipped the sign of long losers and short winners; it showed silver DEV PF 1.07 / t +0.47 and a winning 2024. The numbers below are the corrected ones and agree with the tester's own net per year (all three silver years lose); the verdict (FAIL) is unchanged and firmer.

Pre-registration `PREREG_SDB_SILVER.md`, runner and analysis `sdb_silver_run.py`, deals `sdb_silver/XAGUSD_<year>.csv`. EA 77900 defaults, 0.01 lot, H1, portable MT5 broker tester (tester-modelled ticks before late 2025, "0% real"), swap zeroed.

## Verdict: silver FAILS the DEV bars in every year; round closed (2025 and 2026 not run)
| | 2022 | 2023 | 2024 | DEV 2022-24 (acceptance) |
|---|---|---|---|---|
| SILVER trades / mean bp / PF / per-trade t | 75 / -7.9 / 0.92 / -0.36 | 71 / -19.1 / 0.82 / -0.84 | 69 / -31.6 / 0.72 / -1.38 | **215 / -19.2 / 0.82 / -1.48** (needed PF >= 1.10 and t >= 1.65) |
| GOLD control (same EA, MT5 broker data) | 40 / +37.8 / 1.51 / +1.28 | 33 / -20.8 / 0.80 / -0.62 | 37 / +32.1 / 1.41 / +1.03 | 110 / +18.3 / 1.22 / +1.02 |
Gold 2025 (the control's VAL year): 45 trades, +29.4 bp, PF 1.37, t +1.04. The silver 2025 tester run hung on the MT5 broker tick download (the same failure as GBPUSD+ in `LEAD_ALLPAIRS_RESULT.md`) and was stopped; by the registered rule a DEV failure ends the round.

## Reading
- SDB does NOT replicate on silver: it loses in all three years (tester net -71.5, -206.5, -401.2 USD at 0.01 lot), PF 0.82. Silver is not an SDB market and not a diversifier.
- The control matters more than the test: on gold itself the frozen rule's MT5 broker-data record is PF 1.22 with a per-trade t of only +1.02 in 2022-2024 (one losing year of three) and PF 1.37, t +1.04 in 2025; pooled 2022-25 that is roughly t +1.4, and 2026 is the strong year. The live SDB's edge on gold is therefore real-looking but not statistically established outside 2025-26, consistent with `project-sdb-probably-curve-fit`; the 5-minute EA, not SDB, carries most of the pair's evidence.
