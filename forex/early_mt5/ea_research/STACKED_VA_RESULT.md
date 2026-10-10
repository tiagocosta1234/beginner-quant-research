# G: Griff's "stacked value areas" (youtube D9rx8-cXmSs) on 28 FX pairs + 6 indices: result (2026-10-10, local local clock)

Pre-registration `PREREG_STACKED_VA.md` (commit 61b942a, before any P&L), simulator `stacked_va.py`, outputs `STACKED_VA_DRYRUN.txt`, `STACKED_VA_OUTPUT.txt`, ledger family stacked_va. Hold-out NOT opened.

## Verdict: both trials FAIL; the claimed 70% win rate is about 25-30% in reality
| trial | DEV 2022-24 | VAL 2025 |
|---|---|---|
| G1 (with the video's "no reversal against the trend" filter) | 512 trades, win 30.1%, +0.026 R, PF 1.04, t +0.32 | 157 trades, win 25.5%, -0.124 R, PF 0.82 |
| G2 (no trend filter) | 689 trades, win 28.7%, -0.030 R, PF 0.96, t -0.42 | 216 trades, win 23.6%, -0.166 R, PF 0.77 |
Exits (G1, 2022-25): stop 66%, end of day 22%, target 12%. Median stop 11.9 bp, median target 4.2 R. FX about breakeven (+0.03 R over 604 trades), indices lose (-0.35 R over 65). About 14 trades a month across 34 markets.

## Reading
- The rule as shown has no edge. The target (the previous day's extreme, typically 4 R away) is reached on only about 1 trade in 8, so the payoff is a lottery that roughly breaks even before costs and loses after them in 2025.
- The 70% win rate claimed in the video is impossible with a 1:4 target. The two winners shown (1:3.84, 1:4.49) were found in replay, the hindsight selection this repo's rule warns about.
- Per-market extremes (USDCHF +1.4 R, GBPNZD +0.5 R; AUDJPY -0.6 R, ASX -0.7 R) come from 15-30 trades each, which is noise at this sample size. Picking them now would be curve-fitting.
- Related lead unchanged: the plain value-area rejection on NQ (Rounds 184-186) remains the repo's closest miss. The "stacked" refinement did not improve on it.
