# PREREG_HIGHER_RR: bigger targets on the two London setups

Written Mon 26 Oct 2026 local (local clock), BEFORE any result of this test was computed. the trader: "try increasing rr ratio".
Idea: if London-open moves trend once they start, a bigger target catches the tail and turns a coin-flip side into positive R even with fewer winners.

## Setups (signals and stops unchanged)
- **IND = the frozen indicator `LONDON_FIRST15_1TO1.pine`:** side = colour of the 08:00-08:15 London candle (doji = no trade), entry at its close, stop beyond the far end + 0.5 x range (floor 0.03 x prior ATR14).
  Markets MGC, MNQ, MES (Databento GC / NQ / ES 1m, 2019-07..2026-09-25) and MYM (MT5 broker US30 1m mid, 2022-01..2026-10-16).
- **APLUS = the A+ London 12 EMA:** signals and ORIG stop exactly as in PREREG_APLUS_WIDE (stop band 0.06-0.24% of price). Markets NQ, ES, SI (gold is excluded: its A+ trades have been looked at today at 1R and 1.5R).

## Targets
T1 (1R, reference), T1.5, **T2 (PRIMARY)**, T3, and EOD (no target, exit at 16:00). Stop first on a tie, flat at 16:00 London for all.
Costs in points: GC 0.32, NQ 1.1, ES 0.74, SI 0.0112, US30 4.4.

## Bar (two primaries, alpha 0.0125 each)
- **IND at T2, pooled MGC+MNQ+MES+MYM:** passes iff mean net R > 0 AND random-side P <= 0.0125 AND mean > 0 in at least 5 of the 7 years 2020-2026.
- **APLUS at T2, pooled NQ+ES+SI:** same, with n >= 100.
Random-side P: 20,000 sign flips of each trade to its mirror (same geometry, other side).
Every market, every target, wins, trades per year, avg winner/loser and 2026 are reported (no bar).

## Honest prior
The 1R tests found ~50% side skill. A bigger target does not add skill; it only pays if the post-08:15 distribution has a fat tail in the trade's direction. Note: IND at 1R on these markets and earlier edge_lab target scans were seen before, so only the T2 primary on fresh combinations counts. Expected: no pass.
