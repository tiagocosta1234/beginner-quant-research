# Pre-registration: fit on 2025, validate backwards on 2022-2024 (written 2026-10-13, before any rule was ranked on 2025)
the trader: "(original wording omitted)". Anything can be made to shine in a known year, so the claim is tested in reverse.
Candidates: the unique rules of data\si_ledgers\FF10_mt5real.csv (MT5-only features). FIT window = VAL 2025 (this burns 2025 as a clean window; stated). Per rule on 2025: n>=100, clusters>=20, net mean >= +5 bp; the 20 best by 2025 excess z (one per class/side/H/feature-set) are the "2025 winners".
Backward test: the same rules on window A (2022-01..2023-06) and B (2023-07..2024-12), same cost model, same statistic. A winner is REAL only if net>0 and one-sided p<0.05 on A AND on B separately (n>=50 each). 2026 stays sealed.
Calibration: the identical pipeline on placebo stacks 81-83 (rules fixed, data shuffled): must give 0 real winners in all 3 (else the selection itself is the artefact and the real run is void).
Expectation: 2025 winners look great (the selection guarantees it) and mostly fail backwards; 0 real winners is the most likely outcome.
