# X: combine every tested strategy with a fixed selection rule and per-strategy risk limits: result (2026-10-10, local local clock)

Pre-registration `PREREG_COMBINE_ALL.md` (commit ee4356a, before the run), script `combine_all.py`, output `COMBINE_ALL_OUTPUT.txt` (plus the diagnostics below, run after it).

## What the rule picked
760 daily streams (the gold pair's two legs, 272 factory rules, 480 overnight variants, crypto weekend, turn of month, COT, pre-FOMC). Rule: DEV 2022-24 t >= 2 -> 26 streams: 11 gold-night variants, about 12 index-night variants (mostly NSDQ/SP/US above their 200-day mean, NIKKEI below), pre-FOMC, and the XAUUSD 5 minute EA. The ManualSDB leg was NOT selected (DEV t +0.68). Median correlation between the selected streams +0.04 (computed on the streams, but several are near-copies of the same nights).

## Results (each stream scaled to a 300 USD daily sd, floored at -500 a day; book scaled to an 800 USD DEV sd)
| book | 2025 daily Sharpe (annual), max DD | 2026 daily Sharpe (annual), max DD | P(pass in 36 / 52 bd) 2025 | 2026 |
|---|---|---|---|---|
| selected 26 (the registered rule) | 0.345 (5.5), 6,684 | 0.282 (4.5), 7,527 | 75% / 91% | 69% / 85% |
| gold pair only (yardstick, same scaling) | 0.308 (4.9), 5,698 | **0.385 (6.1), 5,663** | 64% / 83% | **85% / 96%** |
| diagnostic: full pair + the 25 others | 0.356 (5.7), 6,717 | 0.297 (4.7), 7,685 | 77% / 93% | 73% / 88% |
| diagnostic: the 25 others without the pair | 0.328 (5.2), 6,687 | 0.267 (4.2), 8,361 | 71% / 89% | 65% / 82% |
(The DEV row of each book is in-sample by construction and is not quoted here; see the output.)

## Reading
- The combined book is NOT better than the pair. In 2026, the only year no selection touched, it has a lower Sharpe (0.28-0.30 vs 0.39) and a deeper drawdown (7.5-7.7k vs 5.7k). In 2025 it is marginally better (0.35 vs 0.31).
- The 25 non-pair streams are mostly one bet: their 2026 daily P&L correlates +0.83 with plain gold nights. "Combining everything" mostly adds more long-gold overnight exposure on top of a gold pair, in two years when gold rose strongly. That is concentration, not diversification.
- The index-night half did not hold in 2026 (the registered confirmation failed: +0.8 bp a night).
- The P(pass) figures here are optimistic for all books: day-level bootstrap with no intraday low and no gap modelling, scaled to an 800 USD daily sd. Several streams are overnight holds whose real risk sits in gaps the guard cannot stop. Use them only to compare the books, not as live odds (the live odds are in `PASS70_RESULT.md`).
- Decision: no change to the live plan. A gold-night overlay would be more of the same gold beta at higher gap risk.
