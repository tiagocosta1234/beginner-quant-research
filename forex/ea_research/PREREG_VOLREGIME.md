# PREREG_VOLREGIME - volatility-regime filter on opening-range breakouts and fades (2026-10-16, local clock 09:55 local)

Written BEFORE any P&L of the filtered streams was computed. Requested by the trader ("test with a volatility regime filter") after the
2026-10-16 session: London/NY 30-minute opening-range breakouts and their fades on all 46 MT5 broker are about zero or negative
(USDJPY London breakout +0.115 R on bars, ~+0.05 after real ticks; NY breakout dead in 2025-26; fades negative on 42-44 of 46),
and following recent winners failed (`follow_recent.py`, scratch). Honest prior: low. Breakout folklore says breakouts work in
expanding/high volatility and fades in quiet regimes; this round tests exactly that and nothing else.

## Streams (unchanged, already defined)
46 MT5 broker x {London box 08:00-08:30 London, entries to 11:00, exit 17:00 London; NY box 09:30-10:00 New York, entries to 12:30,
exit 15:55 NY} x {breakout: stop at the other side of the box; fade: opposite direction at the break, stop one box height away},
no target, one trade a day, MT5 broker M1 bid/ask (`forex/data_mt5/<MKT>_M1_rates.parquet`), server clock Europe/Athens. 184 streams.

## Regime measures (causal: known before the entry, MT5-native data only)
- **V1 box-relative**: today's box height / median box height of the previous 20 trading days of the same stream.
- **V2 daily-range regime**: mean server-day high-low range of the previous 20 days / median of the previous 250 days' ranges.
Each is cut into terciles using thresholds fixed from the DEV period of the same stream (low / mid / high).
Filters: trade only in tercile T. 2 measures x 3 terciles = **6 filters per stream, 1,104 cells**.

## Periods
DEV 2022-01-01..2024-12-31, VAL 2025-01-01..2026-10-02 (MT5 broker data end). The 2026 hold-out was already looked at for these
unfiltered streams today, so VAL here is not untouched: it is reported as VAL, and no cell is called an edge on this round alone.

## Tests and bars
1. **Pooled effect (the main question)**: for breakout streams and fade streams separately, the mean R per trade in each regime
   tercile, pooled across all 46 markets and both sessions, DEV and VAL, with a market-clustered t. A regime effect counts only if
   the same tercile is best in DEV and in VAL and the VAL pooled mean in that tercile is > 0 with clustered t >= 2.
2. **Cell selection**: a cell passes DEV if DEV t >= 3.9 (Bonferroni for 1,104 cells at 5%) with >= 60 DEV trades; it passes VAL if
   VAL mean > 0 with t >= 2. Expect 0 passes under no edge.
3. **Flagships**: USDJPY London breakout and EURJPY London fade by tercile, reported regardless.
Real-tick cost (-0.03..-0.08 R/trade) is not in the bars; any survivor must clear it. No tuning after the run; amendments only
before any P&L, written here with the reason. Variants counted toward the 40-per-window kill rule as one family (VR).
