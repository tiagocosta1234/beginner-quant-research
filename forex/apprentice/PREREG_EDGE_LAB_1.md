# PREREG_EDGE_LAB_1: four simple gold-futures ideas, one sealed hold-out

Written 25 Oct 2026 (local clock) BEFORE any result of these ideas was computed. the trader: "work on the edge". Context: the mechanical A+ checklist averaged -0.04 R net over 2019-2026 (`A_PLUS_LONDON.pine`, scratchpad backtest), so it is not an edge by itself. Claude (not the trader) chose these ideas.

## Data and costs (same for every idea)
- Databento GC.F continuous 1-minute bars, 2019-06-19 to 2026-09-25 (`futures/data/databento/futures_GC.F_1m.parquet`), times converted to Europe/London (idea 4 to America/New_York). One trade a day per idea, first signal only. Entry at the CLOSE of the signal bar +/- 0.1 point slippage against the trade. Stops: exit at the stop minus/plus 0.1 point (gap: at the open). Same-bar stop and target counts as a stop. Target needs 0.1 point of trade-through. Commission USD 1.20 round trip per micro (R cost = 1.2 / (risk points x 10)). R net = (exit - entry) x side / risk - commission R. Time exit as stated per idea.
- **DEV** = 2019-06-19 to 2023-12-31 (all tuning-free: the numbers below are fixed now). **HOLD-OUT** = 2024-01-01 to 2026-09-25, sealed: not computed for any idea until a finalist is chosen from DEV by the rule below, and then computed ONCE.

## The ideas (all parameters fixed here)
1. **ASIA_BREAK.** Asia range = high / low of all 1m bars 00:00-07:59 local. Skip if range < 1.5 points. Signal = first 1m bar with a close beyond the range high (long) or low (short), bar open between 08:00 and 10:30. Stop = range midpoint (risk must be 1.5-12 points). Target = entry +/- 1.5 x risk. Time exit 17:00 local.
2. **ASIA_SWEEP_FADE.** A bar between 08:00 and 10:30 whose high exceeds the Asia high by at least 0.5 point (low below the Asia low by at least 0.5 point), then within the next 5 bars the first 1m close back inside the range = signal; short after a high sweep, long after a low sweep. Stop = sweep extreme +/- 0.1 point (risk 1.5-12 points). Target = entry -/+ 1.5 x risk. Time exit 17:00 local.
3. **TREND_PULLBACK.** Bias at 08:00 exactly as in the A+ checklist (last closed 15m close vs 15m EMA12, and 15m EMA12 vs 4 candles earlier; neutral = no trade). From 08:00 to 11:00, on 5-minute candles (local-aligned), first 5m candle that touches the 5m EMA12 (low <= EMA for longs, high >= EMA for shorts) and closes back on the bias side of it and in the bias direction (close > open for longs) = signal at that candle's close. Stop = lowest low (highest high) of the last 6 five-minute candles -/+ 0.1 point (risk 1.5-10 points). Target = entry +/- 2 x risk. Time exit 17:00 local.
4. **NY_MOMENTUM.** America/New_York clock. First 15 minutes of the cash session = 1m bars 09:30-09:44 ET. Direction = sign(close of 09:44 bar - open of 09:30 bar), required magnitude >= 1.5 points. Signal at the 09:44 close, in that direction. Stop = low (high) of those 15 minutes -/+ 0.1 point (risk 1.5-12 points). Target = entry +/- 1.5 x risk. Time exit 12:00 ET.
- **Yardstick (not a candidate):** long at 08:00 local open, exit 11:00 close, to show how much of any result is just gold drifting up.

## Direction skill, not drift
For every idea the mirror trade (same entry, same distances, opposite side) is also simulated. Excess = actual mean R minus the mean R of random-side assignments (20,000 draws, each trade independently its actual or mirror side). P = share of draws at least as good as the actual mean. Gold rose strongly in 2024-2026, so the hold-out must beat the random-side line, not just zero.

## Finalist rule (DEV only; 4 ideas, Bonferroni alpha 0.05 / 4 = 0.0125)
An idea is a finalist only if ALL hold on DEV: at least 150 trades; mean R net >= +0.10; random-side P <= 0.0125; mean R net > 0 in at least 3 of the 4 full calendar years 2020-2023. If none qualifies, the hold-out stays sealed and the verdict is "none of the four has an edge" (reported plainly, no new variants on DEV: ideas 5+ would be a new pre-registration with a new hold-out slice).

## Hold-out rule (one look, finalists only)
Pass = at least 100 trades AND mean R net >= +0.10 AND random-side P <= 0.05 AND mean R net >= 0 for both longs and shorts. Anything else = fail, no re-tuning. A pass is evidence, not proof: it would go into the demo plan as the candidate strategy and would still need its own forward demo gate before any purchase.

## Honest limits
- Continuous front-month series: roll days can create small jumps. Entry/exit prices are idealised (no queue, no partial fills).
- Four ideas, one DEV period and one hold-out: a lucky pass is still possible at about 1 in 20 per finalist.
- None of this proves a withdrawal; it only decides whether an idea earns a place in the demo.
