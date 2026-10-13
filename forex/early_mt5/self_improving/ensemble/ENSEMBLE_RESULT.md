# Ensemble of the weak rules as one hypothesis: result (2026-10-13)

Pre-registration: PREREG_ENSEMBLE.md. Code: ens_lab.py. Ledgers: D:\finance\si_ledgers\ENS_real.csv, ENS_placebo81..83.csv. Source ledger: FF10_mt5real.csv (MT5-only free-form run, 185,054 rules). 2026 never used.

## What was done
Members chosen on window A only (>= 150 trades, >= 20 clusters, net >= +1 bp, z >= 2.5; one representative per class, side, horizon and feature set; at most 200 per ensemble by A z). Vote = sum of side x condition-true over members, trade when |vote| >= k (the 90th percentile of non-zero |vote| on A), one entry per H bars, real bid/ask, rollover excluded. 12 ensembles (4 classes x H 4/16/96 bars). Pass on B: >= 100 trades, >= 20 clusters, net >= +3 bp, p < 0.05/12; then one look at 2025.

## Calibration
Placebo worlds 81, 82, 83 (their own A rows, their own shuffled stacks): 0 of 12 ensembles pass in each (best B z 1.85 / 2.03 / 0.08; most ensembles skipped for lack of qualifying members, which is itself the null's signature).

## Real
Only 3 of the 12 ensembles had at least 5 qualifying members:
| ensemble | members | A (in-sample) | B (out of sample) |
|---|---|---|---|
| idx, 1 h | 5 | +5.1 bp, z 4.79 (931 trades) | -1.1 bp, z 0.23 (670 trades, 57 weeks) |
| fx, 1 day | 30 | +14.6 bp, z 3.96 (221) | +1.3 bp, z 1.70, p 0.047 (874, 65 weeks) |
| cmd, 4 h | 111 | +13.6 bp, z 5.39 (373) | +2.0 bp, z 1.91, p 0.030 (392, 69 weeks) |
0 of 12 pass B (best B z 1.91, net +2.0 bp, below the +3 bp floor and the Bonferroni bar 0.0042). Every ensemble loses 85-100% of its in-sample edge out of sample (the regression to the mean the selection implies).

## Verdict
Combining the weak rules does not recover an edge: the votes inherit the selection bias of their members. The two ensembles that keep a small positive B (fx 1 day +1.3 bp, cmd 4 h +2.0 bp, p 0.03-0.05) are what the best of 12 correlated looks gives, and are not candidates. The installed system stays. (Reminder: members come from a search that already regressed on B: best B z of 17,538 promoted rules 2.46.)

## What would be smarter (not done)
Combining signals selected on information-disjoint folds (walk-forward stacking with a rolling refit), a learner trained directly on the MT5 broker pass objective, or per-leg risk allocation of the live system with Bayesian shrinkage on its forward record.
