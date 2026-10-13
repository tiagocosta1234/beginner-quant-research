# Pre-registration: an ensemble of the weak rules, tested as ONE hypothesis (written 2026-10-13, before any ensemble was evaluated on B or VAL)

the trader: "(original wording omitted)". Diagnosis written first: the rule search demands that EACH rule beat costs alone under a false-discovery control over thousands of tests, so everything weak is thrown away; a real weak edge usually shows up only when many weak signals are combined, and the combination is one hypothesis, not thousands.

## What is combined
The ledger of the MT5-only free-form run (D:\finance\si_ledgers\FF10_mt5real.csv, 185,054 rules, features restricted to what the MT5 broker MT5 offers). From the window-A rows only (A = 2022-01..2023-06; B and VAL are not used to select anything): rules with >= 150 trades, >= 20 clusters, net mean >= +1 bp and excess z >= 2.5 on A; one representative per (class, side, horizon, set of features) = the one with the highest A z, to avoid counting near-identical mutants many times. Ensembles by class (idx, fx, cmd, crypto) and horizon H in {4, 16, 96} bars (1 hour, 4 hours, 1 day): 12 ensembles; members = qualifying representatives with that class and horizon, at most the best 200 by A z.
Signal: at every decision bar vote = sum over members of (side x 1 if the member's conditions hold and the bar is not in the rollover hours). Trade long if vote >= k, short if vote <= -k, k = the 90th percentile of |vote| among bars with a non-zero vote on window A (fixed on A). Entries on the grid of spacing H (one per market per horizon), real bid / ask, the conservative flat carry of the earlier engines, rollover hours excluded.

## Tests (fixed now)
Per ensemble on B (2023-07..2024-12): net mean bp per trade, the gross excess over random timing on the same grid and market (cluster-robust weekly Student-t, one-sided p), trade and cluster counts. An ensemble passes B only if >= 100 trades, >= 20 weekly clusters, net mean >= +3 bp and p < 0.05 / 12. Passing ensembles get one look at VAL (2025) with the same floors (p < 0.05). 2026 stays sealed.
Calibration: the identical pipeline on the placebo worlds of the same ledger family (the MT5-only placebo ledgers FF10_mt5pl81..83 with the same shuffled stacks): their ensembles, built from their A rows, must pass 0 of 36 ensembles on B.

## Expectations written now
The members were selected for high A statistics, which regress on B (the best B z of 17,500 promoted rules was 2.46, below chance); an ensemble of regressing signals is expected to regress too. If the ensemble has positive net on B but not enough to pass, it is reported with its size, not promoted. The most likely outcome is no passing ensemble.
