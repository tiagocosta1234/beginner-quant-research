# GN10 result - the late-day reversal on big-move days does not pass development on MT5 broker; hold-out not opened (0 of 1)

Closed 2026-10-18 14:41 local (local clock, second PC PC-2). Pre-registration `PREREG_GN10.md` (commit e8469a5b, amendment 1),
engine `gn10.py` (GN9's `lateday` with `flip=True`), dry run `GN10_DRYRUN.txt`.

| reversal on big-move days (post-hoc, from GN9) | pooled NSDQ+SP+DOW | NSDQ | SP | DOW |
|---|---|---|---|---|
| DEV MT5 broker 2022-24 | +0.058 R (t 1.06), n 468, info +0.093 (t 1.58) | +0.048 | +0.058 | +0.069 |
| VAL MT5 broker 2025 | -0.004 (t -0.06), n 186 | -0.049 | +0.020 | +0.015 |
| CME futures 2020-21 (MT5 broker cost model) | +0.283 (t 2.70), n 138, NQ+ES | +0.203 (NQ) | +0.384 (ES) | - |

**Verdict: FAIL at development; the 2026 hold-out stays sealed** (amendment 1: the repo rule spends the hold-out only on a
candidate that passed development; this one is weak on MT5 broker in 2022-24 and flat in 2025).

## What it shows
- The reversal that looked strong as the mirror of GN9 is much smaller once traded: the last half hour of a big day is so volatile
  that a stop of twice its normal size is hit on 30% of those days, often both ways, so neither side keeps the move.
- It was real in the 2020-21 futures (+0.28 R a trade) and is about zero on MT5 broker since 2022. Like the breakout edge, it belongs to the
  high-volatility years.
- No engine fault: on days without a stop hit the two sides add up to minus two spreads exactly; MT5 broker's late-day spreads are normal.

## Running count
GN1-GN10: 31 of 40 variants of this research window used, 0 passes.
