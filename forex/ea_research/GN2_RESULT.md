# GN2 result - gold and Nasdaq breakouts the day after a pullback or a dip: 0 of 4 pass (2026-10-18 10:59 local, local clock, second PC)

Pre-registration `PREREG_GN2.md` (3b804422; amendment 1 before any P&L, 9dabfee5: the 3-day-pullback and dip trials pooled across
the two markets because each had 28-44 DEV trades), engine `gn2.py`, dry run `GN2_DRYRUN.txt`, output `GN2_OUTPUT.txt`.
Long breakout of the morning box (gold London 08:00-08:30, Nasdaq New York 09:30-10:00), stop at the box low, exit at the session
end, on the day after the condition; control = random longs in the same window on the same condition days.

| trial | DEV n | DEV mean R (t) | control | information (t) | vs GN1 base | VAL 2025 n, mean R | verdict |
|---|---|---|---|---|---|---|---|
| P1 gold, uptrend + down day | 163 | +0.035 (+0.20) | +0.053 | -0.017 (-0.08) | +0.125 | 75, -0.061 | FAIL |
| P2 Nasdaq, uptrend + down day | 127 | -0.017 (-0.16) | -0.080 | +0.064 (+0.52) | -0.148 | 56, -0.045 | FAIL |
| P34 both, uptrend + 3-day pullback (z3 <= -1) | 79 | +0.028 (+0.13) | +0.047 | -0.019 (-0.07) | +0.016 | 34, +0.328 | FAIL |
| P56 both, dip (z3 <= -1.5) | 59 | +0.006 (+0.03) | +0.019 | -0.013 (-0.04) | -0.006 | 20, +0.549 | FAIL (also n < 60) |

Descriptive per-market rows (P3-P6) are in the output; none has a t above 0.6 in DEV. The 2026 hold-out stays sealed.

## What it says
- **Waiting for the morning breakout after a weak day adds nothing.** Every information estimate is within +/-0.07 R of zero
  with t below 0.6: on these days a random long in the same window does as well as the breakout.
- **The dip edge does not survive being delayed to the next morning's breakout** (P56 +0.006 R in DEV). ManualDip earns its
  edge by buying the CLOSE of the weak day; by the next morning's box the rebound is either spent or not yet started.
- 2025 looks better for the pooled pullback and dip trials (+0.33 / +0.55 R on 34 / 20 trades), the gold bull year, and the
  2025 controls rose with it.

## Account environment (2022-25, from 95,472, MT5 broker rules)
No configuration passes by 30 Nov, 22 Dec or 30 Jun 2027 in more than 0.6% of paths; breach 0-75%. Not usable.

## Running count
GN1 5 + GN2 4 = 9 of 40 variants in this research window.
