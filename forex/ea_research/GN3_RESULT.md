# GN3 result - gold at the Shanghai open and Nasdaq through its overnight range: 0 of 4 pass (2026-10-18 11:05 local, local clock, second PC)

Pre-registration `PREREG_GN3.md` (f702530f), engine `gn3.py` and dry run `GN3_DRYRUN.txt` (fe08debe, before any P&L; the
reopen-spread check found no artefact, no amendment), output `GN3_OUTPUT.txt`. Control = random entries in the same window with
the same stop distance and exit (random side for the two-sided trials).

| trial | DEV n | DEV mean R (t) | control | information (t) | DEV years 22/23/24 | VAL 2025 n, mean R (t) | verdict |
|---|---|---|---|---|---|---|---|
| A1 gold Shanghai-open box, both sides | 753 | -0.043 (-0.84) | -0.067 | +0.024 (+0.41) | -0.03/-0.04/-0.06 | 249, -0.107 (-1.36) | FAIL |
| A2 gold Shanghai-open box, long only | 522 | +0.023 (+0.35) | -0.025 | +0.047 (+0.61) | +0.02/+0.03/+0.02 | 177, -0.057 (-0.60) | FAIL |
| O1 Nasdaq overnight range, both sides | 708 | +0.102 (+1.61) | -0.025 | +0.127 (+1.84) | +0.19/+0.12/-0.00 | 222, +0.061 (+0.57) | FAIL |
| O2 Nasdaq overnight range, long only | 431 | +0.125 (+1.50) | +0.047 | +0.078 (+0.84) | +0.08/+0.27/+0.02 | 138, -0.061 (-0.53) | FAIL |

The 2026 hold-out stays sealed for all four.

## What it says
- **Gold's Shanghai-open box is noise.** Half the boxes are narrower than 25 spreads; longs about +0.02 R, shorts -0.12 R in
  DEV (the bull market), both negative in 2025. Asian-hours Chinese demand does not show up as a breakout signal.
- **The Nasdaq overnight range is the best breakout level found on these two markets so far, and it is still not an edge.**
  O1 earns +0.10 R a trade in 2022-24 with both sides positive (longs +0.11, shorts +0.09) and beats random entries by
  +0.13 R (t 1.84), but it fades year by year (+0.19, +0.12, 0.00, then +0.06 in 2025), the same decay as every breakout since
  2022 (`BREAKOUT_KNOWLEDGE.md` fact 4). The range is wide (median 123 spreads), so cost is not what holds it back.
- Lead to record, not to trade: O1 can be checked out of time on 2020-21 (HistData NSXUSD on the main PC, allowed by the
  2020-onward rule) as the USDJPY breakout was; it must not be re-tuned on 2022-25.

## Account environment (2022-25, from 95,472, MT5 broker rules)
Best: O1 at $500 a trade 0.1% / 27% by 30 Nov, 0.7% / 36% by 22 Dec, 18.9% / 57% by 30 Jun 2027 (pass / breach). Breach exceeds
pass for every trial, size and date. Not usable.

## Running count
GN1 5 + GN2 4 + GN3 4 = 13 of 40 variants in this research window.
