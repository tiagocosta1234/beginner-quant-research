# Result: ML on raw bars + relative tick volume (2026-10-13)
PREREG_ML_TV.md, no amendments. Calibration: placebo worlds 91, 92, 93 -> 0 of 12 cells each (max VAL z 1.50 / 1.74 / 1.52) -> gate passed.
Real run: **0 of 12 cells pass**; max VAL information coefficient +0.0202, max VAL excess z 0.65 (below the placebo ceiling). Tick volume adds nothing the existing channels (realised variance, spread) did not already contain, as expected. VAL 2025 was seen before; 2026 stays sealed.
Ledgers: data\si_ledgers\ML3_real.csv, ML3_pl91..93.csv.
