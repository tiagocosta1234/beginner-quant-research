# Free-form trader (v4): result (2026-10-13)

Pre-registration: PREREG_FREEFORM.md with Amendments 1-7 (every change and every failed calibration is written there). Code: ff_data.py, ff_agent.py. Ledgers (append-only, outside git): D:\finance\si_ledgers\FF*_*.csv. 2026 (HOLD) never loaded.

## What the agent is
Hourly bars of 46 MT5 broker symbols in 4 classes; 22 causal features; it composes its own rules (side x horizon x 1-3 conditions, class included, an effectively unbounded space); it searches evolutionarily and re-weights its own operators; explore on window A (2022-01..2023-06), confirm promoted rules once on window B (2023-07..2024-12), validate once on 2025; test = cluster-robust (weekly) Student t on the GROSS bid-to-bid excess over random timing on the allowed grid, plus a +3 bp NET floor on B and VAL; Benjamini-Hochberg q = 0.05 over all B tests; no entries in the rollover hours (server 23 and 0); one entry per H bars per market.

## Calibration (the machine is only believed where it is silent in a world without structure)
Seven placebo attempts' worth of worlds; the last design (Amendments 5-7) was checked in worlds 16, 17, 18, 19, 20: 0 S1 and 0 S2 in every one (and 0 / 0 / 0 / 0 in worlds 11, 13, 14, 15 for the previous version). Failed attempts and what each taught: the null must be 'excess over random timing' not 'mean > 0' (drift); adaptive search needs a split between exploration and confirmation; cost avoidance (spread by hour) and a spread leak in the exit price masquerade as skill; z with few clusters needs the Student t; q must match the gate.

## Final real run (FF8_real): 100 generations, 86,048 rules explored
| | real | placebo 19 | placebo 20 |
|---|---|---|---|
| A rules explored | 86,048 | 36,686 | 33,431 |
| B tests (promoted) | 10,412 | 3,210 | 4,596 |
| best A z | 7.28 | 5.06 | 5.44 |
| best B z (min p) | 4.54 (2.8e-4) | 2.71 (6.2e-3) | 1.50 (0.07) |
| S1 (BH q=0.05 + net floor) | **0** | 0 | 0 |
| S2 | **0** | 0 | 0 |
BH at m = 10,412 needs p <= 4.8e-6 for the best rule; the smallest p seen (2.8e-4) is about what the best of 10,000 null tests gives (about 1e-4). Nothing is distinguishable from chance.

## What the earlier runs showed (the useful by-products)
1. Rollover hour (server hour 0): a real quote-structure effect in FX (mid-to-mid +2.49 bp per hour-0 bar across 28 pairs, 10,874 bars; spread 2.2 bp vs 1.1 bp one bar later); net only about +0.8 bp after paying the ask in the window where fills fail: not tradeable, entries there are now forbidden.
2. R3 (fx short, 4-day hold, ma480 high / cs120 low): looked like the best candidate (VAL z 5.6) but was 34 independent entries counted 414 times; one position per pair gives VAL -0.6 bp: falsified.
3. R7 (fx short, 4-day hold after a 24h / 4h spike): non-overlapping A +17.9 bp, B +4.9 bp, VAL +12.3 bp (353 trades, 18 of 28 pairs, winners the JPY crosses); with 1.5 bp/day carry +13.9 / +0.9 / +8.3 bp. Weak; under the final one-entry-per-H test it does not survive (S1 = 0). 2026 not read.

## Verdict
In this search space (46 symbols, hourly, 4-day horizons at most, 22 features, 1-3 conditions) there is no rule that survives a calibrated test with the economic floor. The installed system stays on the account. What was built is a machine that is silent in noise, finds real structure when it exists (the rollover hour), and whose false alarms can be audited; its limits are the information it is given: price and spread only.

## If continued (not started)
New information through the same platform: macro event calendar and surprise, tick-level order flow proxies (tick volume, quote intensity), other asset classes, intraday gold specifically for the live pair, a regime / risk-state layer for the installed system (the lever the audit of R7 hints at: JPY-cross reversals in 2025).
