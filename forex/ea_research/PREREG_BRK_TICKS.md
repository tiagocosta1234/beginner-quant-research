# Pre-registration BRK-TICKS (breakout day, round 13; written 2026-10-15 12:16 local (commit time), before any code or result)
Question: does the tick-level behaviour in the first seconds of a breakout tell real breakouts from false ones? MT5 broker real ticks (`data\ticks\<SYM>\<YYYY-MM>.parquet`, server-clock ms, bid/ask) 2025-10-01..2026-09-30, 46 markets; boxes and session exits from the MT5 broker M1 bars as in round 1.

## Event and entry
Session 30-minute box (round 1). The first TICK after the box end at which the ask reaches the box high (or the bid reaches the box low), before open + 3 h, is the touch. Entry 30 seconds after the touch at the first tick after that moment (ask for longs, bid for shorts); stop at the other side of the box; hold to the session close (M1 exit, capped 22:55 server). R = |entry - stop|; skipped if R < 2 spreads or if price is already back beyond the stop. Base = every such event.

## Features (from ticks, all up to the entry moment)
- f_speed: mid move from the touch to the entry, in the breakout direction, in units of R.
- f_activity: number of ticks in the 30 s after the touch / median ticks per 30 s over the box.
- f_spread: spread at the touch / median spread over the box.
- f_flow: (up-ticks - down-ticks) / ticks of the mid in the 60 s before the touch, times the side.
## Cells (4): T1 f_speed in its top tercile; T2 f_activity top tercile; T3 f_flow >= +0.2; T4 f_spread <= 1.0. Terciles from the previous 250 events of the same market (causal; warm-up excluded).
## Periods and gates
DEV = 2025-10..2026-03, VAL = 2026-04..2026-09 (2026 is open for the breakout family; this round's split is internal to the tick era, 12 months). 1. DEV mean >= +0.05 R and t >= 2.5 (daily portfolio; Bonferroni 4). 2. VAL mean > 0 and t >= 1.65. 3. Beats the base (all events) by >= 0.05 R in DEV and VAL.
## Honest prior
About 5%: the tick-event study (TICK_EVENTS) found surprises absorbed within seconds; breakouts may behave the same.
