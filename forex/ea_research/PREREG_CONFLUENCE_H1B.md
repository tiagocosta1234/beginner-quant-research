# Pre-registration: hourly confluence panel, variant b -- no decisions in the rollover hours (family K2b, four more trials)

Written 2026-10-10 14:01 local (local clock; commit 8b36b30 at 14:01:56, the variant b run came after it), BEFORE any run of variant b. It amends `PREREG_CONFLUENCE_H1.md` (K2). K2's four registered trials ran first (`CONFLUENCE_H1_OUTPUT.txt`) and all FAILED acceptance 1 and 2 with absurd numbers (net Sharpe -3.7 to -13.9, gross +5 to +18, even the shuffled-label control gross +12.9). The reason is an execution-realism defect of K2's design, found by reading the by-hour P&L table and the quoted spreads: a decision at server hour 23 is executed at the first minute of the 00:00 bar, the rollover minute, where the quoted spread is 6 times the normal one on FX (EURUSD 2.8 bp against 0.43 bp, all-market median 8.5 bp against 0.9) and the mid is distorted, so the models learned to trade the distortion (a big gross gain on mids) and paid for it in costs; the same applies to marking a position at the 00:00 open. K2's result stands as reported; K2b removes the defect and nothing else.

## What changes (and only this)
1. Decision hours 22, 23 and 0 (server clock, the hour of the bar that has just closed) are forced FLAT: the position is closed at the first minute of the 23:00 bar (normal spread) and nothing is opened until the decision after the 01:00 bar. So no execution happens at 00:00 or 01:00 first minutes and no position is marked at the 00:00 open.
2. Training rows with those decision hours are removed from every fit (models do not learn the rollover), and the scale s is computed from allowed rows only.
3. Trials are S1b, S4b, G1b, G4b; ledger family confluence_h1b. Everything else (data, features, labels, models, position function, costs, periods, statistics, permutation, acceptance 2-6) is exactly as in `PREREG_CONFLUENCE_H1.md`.
4. Bonferroni: K2 (4) + K2b (4) = 8 trials in this intraday family, so acceptance 1 becomes daily t >= 2.6 (it was 2.4) and net Sharpe >= 1.0. The hold-out 2026 stays closed unless a trial passes 1-4.

## Honest prior
About 2% (unchanged). The repair can only remove a cost artefact; it cannot add an edge. If K2b is also closed, the hourly indicator-confluence axis is closed and no further variant is run on this panel (no tuning of the excluded hours, thresholds or horizons).
