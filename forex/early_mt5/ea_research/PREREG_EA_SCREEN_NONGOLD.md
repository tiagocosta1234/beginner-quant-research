# Pre-registration: Family XS, screen of the 1,220 CodeBase EAs for a NON-GOLD second engine (written 2026-10-11 ~15:20, before reading any per-EA yearly figure)

Source: Round 347 batch (`forex/early_mt5/ea_batch/results/<id>.csv`: deals of each EA on its native symbol, MT5 broker demo data, offline tester; status.csv).
Earlier analysis scored them only against a fast-pass bar; nobody filtered for "steady every year, outside gold". About 1,000 EAs are on
FX / index / oil / silver symbols. With that many, many will look good by luck: the filter is strict and 2026 is a one-look hold-out.

## Data
Every EA whose symbol is NOT XAUUSD, with a result file. Closed P&L = profit + commission + swap of the "out" deals, by month.
DEV = 2022-01..2024-12, VAL = 2025, HOLD = 2026-01..2026-09 (the batch ran to about 2026-10-01).

## Screen (all required, fixed now)
1. At least 100 closed trades in DEV + VAL.
2. Net > 0 in EACH calendar year 2022, 2023, 2024 and 2025.
3. Monthly P&L t-stat over 2022-25 >= 3.5 (about Bonferroni-scaled for ~1,000 EAs: one false pass expected at most by chance;
   a block bootstrap reality check of the best t across all screened EAs is also reported).
4. Profit factor 2022-25 >= 1.2.
Survivors (if any) get ONE look at 2026: pass if 2026 net > 0. Then, before any account test: rerun on MT5 broker data (real ticks / MT5 broker bars)
via forex/early_mt5/ea_batch, check the grid / martingale disqualifier, and the correlation with the pair.
