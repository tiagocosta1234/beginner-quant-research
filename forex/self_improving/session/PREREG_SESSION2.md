# PREREG round 2 - session system, raise P(pass) (2026-10-13, written before the run)
Goal (the trader): a higher pass rate with the same spec. Same simulator (session_lab.run), same signals (SDB + XAU5), same barriers, same MT5 broker rules.
New knobs: MMAX in {6, 10} (cap on the size multiplier); protect p in {1, 0.5} (size multiplied by p once the day PnL is >= +1,000, to avoid giving a nearly won day back).
Grid: L {750, 1000, 1500, 2000}, m0 {2, 3, 4, 6}, k {0, 1, 3}, r {0, 1}, H_stop {0, 3}, MMAX {6, 10}, p {1, 0.5}  (768 configs).
Selection on TRAIN only (FT 2022-24, MT5 broker rules): by block bootstrap of the system's daily results (as session_passrate.py, 20,000 paths): maximise P(pass within 44 business days) subject to breach <= 10% within 250 bd.
The top 5 are then run ONCE on MT5 broker 12 months and FT 2025-26; the verdict is whether any of them beats config D (L1500 m0 3 k1 r0 H3) on the MT5 broker test in P(pass<=44bd) at breach <= 10%. No config is chosen after seeing the test.
Caveats: same data as before (about 12 months of MT5 broker-era gold), replay of tester fills, no swap, no ManualDip.
