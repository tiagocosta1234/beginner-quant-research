# PREREG_SIGNAL_SEARCH: one finite search for a better filter on the claude.pine London A+ rule

Written Tue 2026-10-27 19:06 (local clock) BEFORE any result. the trader: "lets try to come up with better indicator signals". Base rate first: the rule picks the side better than chance on gold
(mirror -0.2 to -0.3 R) but nets about -0.05 R after realistic costs; 10+ earlier families found nothing; likely outcome: NOT SHOWN. This search ends today.

## Idea
Costs are fixed in points, so the cost share of risk (cost / risk) is what turns a small gross edge (+0.08..+0.12 R) negative. Four filters, each with a stated reason, no thresholds tuned:
F1 cost share <= 12% of risk (risk >= cost / 0.12); F2 strict A+ = FVG (C1) AND hourly EMA (C3) both true instead of any 2 of 3; F3 trigger candle opens 08:00-08:04 (not later);
F4 trade only in the direction of the prior daily trend (prior close vs its SMA20). 16 cells = each filter on or off, on top of the hard rules + A+ (2 of 3).

## Data and costs
Databento GC (2019-09..2026-09), rule as claude.pine (bias candle 07:45 London, trigger 08:00-08:14, stop beyond last 6 candles + 1 tick, risk 1.5-6 pts on gold, 1:1, flat 16:00, stop first).
Replication markets (secondary, not gating): NQ and ES with risk bounds 0.0375%-0.15% of price. Costs per round trip (fee + 1 tick, micros): GC 0.292, NQ 0.860, ES 0.494 points.

## Protocol
DEV = 2019-09..2022-12, TEST = 2023-01..2026-09 (GC). Pick the cell with the best DEV mean net R among cells with >= 60 DEV trades. Run it ONCE on TEST.
Mirror = same entry, opposite side, same stop distance and target.

## Bar (one look)
TEST (GC) n >= 50 AND mean net R > +0.05 AND random-side P <= 0.05 (20,000 flips to the mirror) AND net R > 0 in at least 3 of the 4 TEST years.
Reported, not gating: the same cell on NQ and ES TEST; all 16 cells DEV -> TEST; the unfiltered A+ rule on TEST. If the bar fails the signal search ends; nothing is re-tuned.
