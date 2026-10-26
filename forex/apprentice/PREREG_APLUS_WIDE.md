# PREREG_APLUS_WIDE: the A+ London 12 EMA with wider stops (to shrink costs in R)

Written Mon 26 Oct 2026 ~10:5x local (local clock), BEFORE any result of this test was computed. the trader: "test that wider stops on A+, but what's its trade frequency?"
Lead from PREREG_LONDON12_APLUS: A+ at 1:1 on gold, random-side P 0.012 but -0.023 R net (about +0.08 R gross, costs 0.32 pt on ~3-pt stops).

## Signals (unchanged)
The A+ rules of PREREG_LONDON12_APLUS (+ Amendment 1): 15m EMA12 bias at 07:45, first 1m fresh EMA12 cross with body > wick that closes 08:00-08:15, A+ = 2 of 3 confluence (C1 FVG zone, C2 Asia sweep, C3 1h EMA side). Target 1:1, stop first on a tie, flat 16:00.

## Stop variants
- **ORIG:** stop beyond the extreme of the trigger candle and the 5 before (+1 tick); stop band 0.06%-0.24% of price (= 1.5-6 points on gold at 2,500).
- **W2 (PRIMARY):** the same structural stop at TWICE the distance; band 0.12%-0.48% of price. Same signals, half the cost in R.
- **W15:** structural stop over the trigger candle and the 15 before (+1 tick); band 0.12%-0.48%.
- **WATR:** stop distance = max(ORIG distance, 0.5 x prior daily ATR14); no lower band, upper limit 1.0 x ATR.
Costs in points: GC 0.32, NQ 1.1, ES 0.74, SI 0.0112; ticks GC 0.1, NQ 0.25, ES 0.25, SI 0.005.

## Data and what counts
- Databento 1-minute 2019-11 to 2026-09-25: GC, NQ, ES, SI.
- **Gold is DESCRIPTIVE only** (its A+ signals were already seen today).
- **The test is the replication on NQ + ES + SI pooled**, where the A+ rules were never run: W2 passes iff pooled mean net R > 0 AND random-side P <= 0.025 AND n >= 100 AND mean > 0 in at least 4 of the 7 years 2020-2026. Each market alone, each variant, and trades per year are reported (no bar).

## Honest prior
The plan was written for gold; the other markets may not share the effect. A wider 1:1 bracket also needs a bigger move, which lowers the win rate of a real but small edge. Expected: no pass.
