# MPROFILE result (2026-10-14 ~22:10): market-profile plays on 46 MT5 broker - NO EDGE
Pre-registration `PREREG_MPROFILE.md` (commit 384fbb73), engine `mprofile.py`, trades `data\si_ledgers\MPROFILE_trades.parquet`, cells `MPROFILE_cells.csv`. 2026 never loaded.

## Dry-run
46 markets; truncation test PASS (EURUSD, XAUUSD, SP, BTCUSD: every trade before the cut identical); hand check EURUSD 2024-07-03 profile POC 1.07434 / VAH 1.07797 / VAL 1.07362 (day range 1.07362-1.08168), 2024-07-04 opened above the VA and stayed there -> DRIVE long 05:05. One fix before P&L: early-close days end at the day's last bar instead of being skipped (skipping them needed a future bar). The first run crashed while saving (a column type), before any statistic was printed; rerun unchanged.

## Cells (net R per trade with real bid/ask; gross = mid; t on the daily portfolio, Newey-West lag 1)
| cell | DEV n | DEV net | DEV gross | DEV t (net) | VAL net | VAL gross | VAL t |
|---|---|---|---|---|---|---|---|
| VA80 (80% rule) | 10,145 | -0.086 | +0.001 | -9.7 | -0.052 | +0.023 | -4.8 |
| DRIVE (open-drive) | 15,155 | -0.114 | -0.001 | -8.6 | -0.082 | -0.005 | -5.4 |
| EDGE (fade VA edge to POC) | 13,193 | -0.309 | +0.032 | -11.3 | -0.361 | +0.002 | -9.2 |
| NPOC (naked POC magnet) | 21,668 | -0.051 | +0.010 | -8.1 | -0.035 | +0.012 | -3.3 |
Placebo worlds (levels moved 0.5-1.5 VA widths, seeds 95-97): DEV t between -13.6 and -1.4, gross between -0.026 and +0.042, i.e. the real cells look exactly like levels drawn at the wrong price. 0 of 4 cells pass any gate.

## Diagnostics (after the run, no new cell)
- Gross t over all markets: VA80 -1.18 / -0.94 (DEV/VAL), DRIVE +0.08 / -1.41, EDGE +2.18 / -0.24, NPOC +0.88 / +0.58. Before costs, price does not respect yesterday's value area or POC any more than it respects a shifted copy of them.
- The 80% rule is slightly WRONG-signed on FX and indices in DEV (gross t -2.6 and -3.1): re-entering the value area does not carry price to the other side.
- Only corner with a DEV gross t above 2.5: EDGE on gold/silver, +0.184 R (t +2.6, 530 trades), which is +0.007 in VAL and still -0.05 R net in DEV. Noise across 20 class x cell corners.
- EDGE's large net loss (-0.31 R) is the cost of its tight stop (half the edge-to-POC distance) against the spread, worst on crypto (-0.8 R).

## Reading
Reading the chart as an auction (time at price, value area, POC) gives no edge on MT5 broker prices 2022-2025: all four classic profile plays are zero before costs and negative after, in both periods, in every year, and no different from the same rules on shifted levels. Together with S/R (swing levels no better than random levels) and ANALOG (shape memory = chance), level- and shape-based chart reading is closed on this data. HOLD stays sealed.
