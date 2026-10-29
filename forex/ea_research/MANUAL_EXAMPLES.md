# Manual FX Replay examples - what separates losers from winners (running log)

Started 2026-10-16 (the trader: "é suposto estares a aprender o que distingue as derrotas de vitória").
Each example: decision made with data up to 08:29 local only; features; side chosen; result of BOTH sides on MT5 broker data.
Single trades are anecdotes: every lesson below is checked on the large history before it is written as a rule.

## Examples
| Day | Box (MT5 broker) | Box/ATR | Box/spread | Close pos in box | 5-day trend | Side taken | Result | Other side |
|---|---|---|---|---|---|---|---|---|
| 2023-05-08 Mon | 2022.65/2020.80 ($1.85) | 0.06 | 15 | 0.81 (top) | +0.83 ATR up | Short (sell stop low, TP 1R) | -1R (in 09:04, SL 09:41) | Long also -1R (08:30 -> SL 09:04) |
| 2023-05-09 Tue | 2024.50/2021.69 ($2.81) | 0.09 | 21 | 0.39 (middle) | +1.25 ATR up | Long (buy stop high, TP 2R) | -1R (in 08:47, SL 09:21) | (short not checked) |
| 2023-05-10 Wed (US CPI 13:30) | 2032.03/2028.16 ($3.87) | 0.12 | 29 | 0.17 (bottom) | +0.57 ATR (neutral) | **No trade** (conflicting slices, box < 33x spread, CPI) | 0R | Long -1R (08:59 -> SL 09:28), short -1R (09:28 -> SL 11:39) |
| 2023-05-11 Thu (BoE 12:00, US PPI 13:30) | 2028.35/2021.76 ($6.59) | 0.21 | 66 | 0.59 (middle) | -0.27 ATR (neutral) | LDN3F both stops at 08:39 (1:1) | 0R by the rule (no fill before 10:00; low 2021.94) | FX Replay kept both orders: sell 10:00 -> SL 11:10 (-1R), buy 11:10 -> TP 12:15 (+1R) |

Running score of the decisions: 2 trades -2R, 1 skip that saved 1R, 1 rule day with no fill (0R). All three days were whipsaw days (both sides stopped)
and all three boxes were in the two smallest quarters by box/ATR.

First large-box day (0.21 ATR): no whipsaw inside the window; the real move (up, +1R) came at 11:10, after the
entry window. FX Replay has no OCO and no expiry: orders must be cancelled by hand at fill / at 10:00.

## Lessons checked on history
1. **Tiny boxes get whipsawed.** Gold 2022-26, London 30-min box, each side as an independent stop order:
   | Box / ATR20 | both sides fire | both stopped (whipsaw) | long hits 1R | short hits 1R |
   |---|---|---|---|---|
   | 0.04-0.10 (smallest quarter) | 45% | 29% | 49% | 53% |
   | 0.10-0.13 | 29% | 21% | 49% | 51% |
   | 0.13-0.17 | 26% | 17% | 50% | 48% |
   | 0.17-0.79 (largest quarter) | 12% | 9% | 49% | 48% |
   Both examples were in the smallest quarter. The per-trade 1R hit rate stays near 50% at every box size, so the box
   size does not tell WHICH side wins; it tells how often the day chops both stops, and the spread costs more per R.
2. **Direction choice by box-close position / 5-day trend** (side_stats.py): differences of 0.1-0.3R between long and
   short exist in 40-120-day slices, within about one standard error. Not a reliable separator yet.
3. **From the 45,246-trade study (ldn_features.py):** box/spread, late trigger (> 8 min after 08:30) and not chasing a
   strong 5-day move are the only features consistent across 2022-24, 2025 and 2026; registered as LDN3F (forward).

## Tools
- `data/scratch/ldn_feat/side_stats.py <YYYY-MM-DD> XAUUSD` - single-side stats with data before the day.
- `data/scratch/ldn_feat/whipsaw.py XAUUSD` - whipsaw rate by box size.
