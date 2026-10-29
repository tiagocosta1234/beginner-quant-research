# Results summary

One line per family of ideas, across both markets. "R" is risk units after costs; every row links
to where the detail lives. Nearly everything is negative or not significant, which is the point
of the repo: these are the honest numbers.

| family | market | best honest result | verdict | detail |
|---|---|---|---|---|
| London-open 1-minute rule (EMA bias + trigger) | gold, NQ, ES, SI | -0.10 to -0.19 R a trade | no edge | `futures/london_open_gold/`, `forex/apprentice/` |
| Same rule, A+ subset, 2019-2026 | gold futures | -0.023 R net (+0.08 gross, side beats random P 0.012) | lead eaten by costs | `forex/apprentice/LONDON12_APLUS_OUTPUT.txt` |
| Blind chart reads at the open | gold | +0.093 R, then +0.026 R on fresh days | not shown, replication failed | `forex/apprentice/README.md` |
| ML direction models (81 features) | 5 markets | AUC 0.49-0.51 | no edge | `forex/apprentice/ML_DIRECTION2_OUTPUT.txt` |
| Larger targets (1.5-3R) | 4 micros | win rates match a random walk | no edge | `forex/apprentice/HIGHER_RR_OUTPUT.txt` |
| Point of control / value area | NQ | closest misses of the engine (rounds 178-186) | not shown out of sample | `futures/engine/INDEX.md` |
| VWAP z-score, time-of-day, S/R bounce | MNQ, MGC | in-sample leads | faded out of sample | `futures/strategies/` |
| Tokyo session (follow, fade, break) | MNQ | -0.051 / -0.009 / -0.021 R | not shown | `futures/london_open_gold/README.md` |
| Breakouts across many markets | MT5 symbols | USD/JPY London about +0.05 to +0.15 R | small, fragile | `forex/ea_research/INDEX.md` |
| Overnight index holding | US index CFDs | +2.8 bp a night vs 50-90 bp noise | real but tiny | `forex/ea_research/OVERNIGHT_RESULT.md` |
| Long-only trend-filtered drift book (D2) | MT5 multi-asset | +24 to +88 USD a day per 100k, hold-out +50.6 | **passed every bar** (needs free holding) | `docs/swap-costs.md` |
| Same book rerun on free daily data, 2010-2026 | 5 indices/ETF | +7.6% a year swap-free, +4.3% with CFD swap; 2010-19 +4.9% | positive in every period, filter adds no return | `drift_book/` |
| Automated rule search (12,000 rules) | 46 MT5 symbols | 0 survivors after calibration | no edge | `forex/self_improving/README.md` |
| Published effects (overnight drift, intraday momentum, turn of month) | ES, NQ, GC, SI | faded since 2021 / failed hold-out | not shown | `forex/apprentice/README.md` |
| Videos tested (NY box breakout, first 5-minute candle vs EMA12) | NQ | 0 of 4 variants each | no edge | `docs/lessons.md` |
