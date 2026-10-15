# PREREG_ORB11_ICTSTOP - ICT-style dynamic stops on the trader's 30-minute London / NY ORB (written 2026-10-15 local clock 18:04, before any P&L)
the trader: "(original wording omitted)".

## Entries (from ORB11_ENTRY, unchanged)
E1 TOUCH (first touch of the box edge, stop order) and E2 C5 (first 5-minute mid close outside the box, next-minute open). 30-minute box 08:00 London / 09:30 New York, session end 17:00 London / 15:55 New York, capped 22:55 server; all 46 MT5 broker symbols, MT5 broker M1 bid/ask, longs at the ask, shorts at the bid; trades with an initial stop < 2 spreads skipped.

## Structure (causal)
M5 bars on the server clock built from mid M1 prices. A swing low at M5 bar j is a low below the two bars on each side; it is known only from bar j+3 (after bar j+2 has closed). Swing highs mirror it. At entry only bars that have fully closed are used.

## Stops (long side; short mirrors)
- S0 BOX: opposite edge of the box (ORB11 baseline).
- S1 EQ: the box's 50% level (ICT equilibrium).
- S2 SWING: the most recent confirmed M5 swing low below the entry price within the last 24 M5 bars; if none, the box low.
- S3 OB: low of the last bearish M5 candle (mid close < open) among the 12 closed bars before entry (the order block); if it is not below the entry, the box low.
- S4 FVG: a bullish fair value gap among the last closed M5 bars (low of bar c above the high of bar c-2, c within the last 2 closed bars); stop at the low of bar c-2. No FVG -> no trade.
- S5 TRAIL: initial stop S2; afterwards the stop moves up to every swing low confirmed after entry (never down).
- S6 BE+TRAIL: initial stop S0; after +1R the stop moves to the entry price, then trails confirmed swing lows as in S5.
Targets for S0-S4: 1R, 2R, 3R (R = initial stop distance) or none (session end). S5 and S6: no target, session end. 2 entries x (5 x 4 + 2) = 44 rules x 2 sessions x 46 symbols = 4,048 cells; pools session x class: 440.
Stops fill at the level, or at the minute's open if it gapped through; same-minute stop and target: stop first; a stop that moves applies from the next M5 bar.

## Null
One random entry per symbol-session-day (random minute after the box, random side) with the same stop rules (S0 = box width, S1 = half the box width, structure stops as defined).

## Periods and tests
DEV 2022-24, VAL 2025, 2026 already open for the breakout family (non-clean extra look).
Pools pass: DEV+VAL daily t >= 3.69 (one-sided 5% over 440), mean > 0 in DEV, VAL and 2026, above the random null with the same stop. Cells pass: t >= 4.22 (over 4,048), same conditions. Walk-forward: best of 44 per cell on DEV -> VAL / 2026. A passer goes to HistData 2020-21 and MT5 broker real ticks before it is called a candidate.

## Honest prior
ORB11_GRID showed that stop width only changes how much of R the spread takes, and BRK_EXITS that exits do the same on random entries. Structure stops are usually tighter than the box, so they pay more spread per R. Expected: no pass; trailing variants close to the random null.
