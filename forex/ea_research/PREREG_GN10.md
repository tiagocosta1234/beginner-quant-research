# PREREG GN10 - late-day REVERSAL on big-move days, US indices, decided on the 2026 hold-out only (1 trial)

Registered 2026-10-18 14:39 local (local clock, second PC PC-2), before any 2026 number of this rule was computed.
the trader: "push it and keep testing the remaining 17". GN1-GN9 used 30 of the 40 variants of this research window.

## Status: a POST-HOC hypothesis (said plainly)
GN9 tested late-day CONTINUATION on big-move days and found the opposite on US indices: the last half hour went against the day
in 2022-24 on MT5 broker (NSDQ -0.145 R, t -2.9) and in the 2020-21 CME futures (NQ -0.21, t -2.9; ES -0.40, t -5.1), stronger the
bigger the day; 2025 mixed (NSDQ +0.05, SP -0.18). Those data suggested this rule, so they cannot confirm it. Their mirror
numbers are printed by the dry run for the record (development evidence, post-hoc); **the decision rests only on data not yet
seen: the MT5 broker 2026 hold-out, one look.**

## Rule (GN9's rule with the side flipped; nothing else changes)
- ROD = mid(15:29 New York close) / mid(15:59 close of the previous session) - 1. Big-move day: |ROD| >= the 75th percentile of
  |ROD| on the previous 250 eligible days (at least 60 earlier values).
- On a big-move day, at the 15:30 open trade AGAINST ROD (sell at the bid after an up day, buy at the ask after a down day); exit
  at the 15:58 close (ask for shorts, bid for longs); stop 2 S, S = the 14-day mean absolute mid move 15:29 close -> 15:58 close;
  R = 2 S. Engine `gn9.lateday(..., flip=True)` (`brk_patterns.walk`).
- Markets: the three MT5 broker US indices NSDQ, SP, DOW, pooled (each index trade counts; t clustered by day).
- Possible mechanism (not tested): dealers net long gamma into the close since zero-day options grew (they sell rallies and buy
  dips); closing-auction imbalances published at 15:50 and absorbed.

## Trial (1)
**R1** pooled NSDQ + SP + DOW reversal on big-move days. Descriptive: each index alone; the random-direction control (5 draws,
same entry, stop and exit); normal days.

## Hold-out and acceptance
- HOLD: MT5 broker 2026-01-02 .. 2026-10-16 (about 50-65 big days per index), opened once by `gn10.py --run`.
- PASS if the pooled HOLD mean net R > 0 with day-clustered t >= 1.65 (one-sided, single trial), and the information over the
  random-direction control > 0.
- Account environment (after the look): replay from 95,472 (MT5 broker rules, 5-day block bootstrap of 2022-26 days) at $250 / $500 a
  trade, pooled and NSDQ alone.
- Even on a PASS the rule is only a candidate for a read-only forward paper log: its development was post-hoc and the effect is
  small next to MT5 broker's day limits.

## Dry run (development evidence, post-hoc; no 2026 number)
Identity check (flip=False reproduces GN9 L1 / L2 DEV means), mirror results by index and pooled for DEV 2022-24, VAL 2025 and
the 2020-21 futures, count of 2026 big days (count only).

## Honest prior
About 20%: the reversal showed in two independent periods and both index futures, but 2025 was mixed, the effect is small
(+0.1..+0.3 R before the second spread) and the 2026 sample is short (power about 40% if the effect is real).

## Running count
GN1-GN9 30 + GN10 1 = 31 of 40 variants in this research window.

## Amendments
1. (2026-10-18 14:41, after the dry run, before any 2026 number) The standing repo rule allows the 2026 hold-out only for a candidate that
   passed development. This pre-registration left that gate out because the mirror of GN9 was expected to be clearly positive;
   the exact MT5 broker development evidence printed by the dry run is not: DEV 2022-24 pooled +0.058 R (t 1.06), VAL 2025 -0.004 R;
   only the 2020-21 futures are positive (+0.283 R, t 2.70). By the usual single-trial bar (DEV t >= 1.65 and VAL > 0) it does
   not pass development, so **the hold-out stays sealed and R1 is closed as FAIL (development)**. The variant still counts (31 of
   40). This makes the test stricter and was written before the deciding data were seen.
