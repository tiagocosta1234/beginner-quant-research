# Pre-registration ANALOG: chart pattern memory across every MT5 broker market (written 2026-10-14 ~21:50, before any code or result)
the trader: "you need to trade differently, analyze the chart differently, trade every pair". Untested here: every earlier chart family turned the chart into indicators or hand rules (MA/RSI/ATR/UT Bot/swing levels/FVG/order blocks/confluence), or fed raw bars to a tree/ridge model per market. A discretionary chartist works differently: "I have seen this shape before, and it usually went up". ANALOG makes that causal and testable: the last W hours of a market are a shape; the K most similar past shapes from ALL markets (pooled library, past only) vote on the direction; the trade follows the vote. Pooling every market is what gives the memory enough examples.

## Data, clock, marks
MT5 broker M1 bid/ask, 46 markets (every `forex/data_mt5/*_M1_rates.parquet` except the tick file), server clock, data loaded only before 2026-01-01 (2026 sealed). Hourly marks at minute :05 (prices = open of that minute); marks at server hours 23 and 0 are dropped (rollover rule). Returns are taken between consecutive valid marks of a market (weekend and rollover gaps become one step). vol = std of the last 240 returns (at least 120), known at the mark.

## Signal (per market, decision marks at server 09:05, 13:05, 17:05)
- Shape: the last W returns divided by vol (W in {12, 48}).
- Label of a past shape: mid log return from its mark to the mark H valid steps later, divided by vol (H in {4, 22}; 22 steps is about one day).
- Library for queries in calendar month m: every decision-mark shape of every market whose label was complete before the first second of month m. Euclidean distance, K = 50 nearest.
- Vote = share of the 50 neighbours with label > 0. Long if vote >= 0.60, short if vote <= 0.40, else no trade. One trade per decision mark; overlapping trades allowed (counted in the statistics by day clustering).
- Execution: long at the ask of the entry mark minute, exit at the bid of the mark H steps later (short mirrored); weekends held when the exit falls after one (MT5 broker account is swap-free). P&L per trade in sigma units: side x net log return / (vol x sqrt(H)); also reported in bp.

## Cells and periods
4 cells: W {12, 48} x H {4, 22}. Library warm-up 2022-01..06; DEV 2022-07-01..2024-12-31; VAL 2025-01-01..2025-12-31; HOLD 2026-01-01..2026-09-30 (sealed; opened once only for a cell that passes 1-5).

## Statistics and gates
Daily portfolio series = mean net sigma-P&L of the trades entered that day; t with Newey-West (lag 2).
1. DEV |t| >= 2.50 (Bonferroni for 4 cells) and mean net >= +0.02 sigma per trade in the direction of the sign (a negative cell means "fade the analog" and is gated the same way).
2. VAL same sign, |t| >= 1.65.
3. Same sign in at least 3 of the 4 years 2022H2, 2023, 2024, 2025.
4. Placebo: 3 worlds (seeds 91-93) where each market's library labels are randomly permuted in time (shape-to-outcome link broken, same neighbours, same real trade outcomes); the real cell's |DEV t| must exceed the 95th percentile of |DEV t| over the 12 placebo cells.
5. No single market contributes more than 40% of the DEV net P&L.
Reported, not gated: by market class (FX, metals, indices, crypto), long vs short, vote strength.

## Dry-run (no P&L)
Counts per cell and period, truncation test (shapes and vol at marks before a cut are identical when the data after the cut is removed), library causality check (max label exit time < month start for every batch), hand check of one mark's prices.

## Honest prior
About 3%: the information is still price only, and the tree model on 48 raw 15-minute bars (`self_improving/ml`) and every price family since 2026-10-08 found nothing net of the spread; pooling all markets adds examples, not new information.
