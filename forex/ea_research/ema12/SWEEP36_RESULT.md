# SWEEP36 result: a sweep reversal with the trader's confirmation on all 46 MT5 broker (run 20 Oct 2026 16:23-16:24, main PC, local clock)

Pre-registration `PREREG_SWEEP36.md` (sha256 c18545ea4ac44f0c8f8e7f4d5380739ed0d6002c8c7d3d7bcdceefd5f50cdfaa, 16:21:25). Engine `sweep36.py`, checks `SWEEP36_DRYRUN_OUTPUT.txt` (truncation test 80 signals 0 mismatches; the 30 Apr 2025 London case reproduces: a buy confirmed at 08:09 by a displacement candle, entry 08:10, stop at the sweep low). Output `SWEEP36_OUTPUT.txt`, `SWEEP36_TRIALS.csv`, `SWEEP36_MARKETS.csv`. MT5 broker M1 bid / ask, DEV 2022-24, VAL 2025; nothing after 2025-12-31 loaded.

## Result: 0 candidates of 36; every variant loses and the sweep adds nothing
- **All 36 variants lose in development:** median DEV mean R -0.222 a trade (best -0.177), day-clustered t from -44.7 to -11.1 against the +2.77 bar; about 26,000 trades per variant; VAL 2025 median -0.221, 0% above zero.
- **No direction skill:** the inverted side loses the same (-0.223); (rule - inverted) / 2 = -0.002 R at the median, positive in 33% of variants.
- **The sweep adds nothing:** the control with the confirmation only (no sweep required) loses -0.224; the difference rule minus control is +0.0004 R (the sweep helps in 50% of the variants, i.e. a coin flip). By confirmation type: displacement -0.203, gap -0.237, either -0.242; by target 0.5 / 1 / 2 R: -0.225 / -0.224 / -0.221.
- **Without the spread it is a coin flip:** at mid prices the rule is -0.006 R (best variant +0.007, t +0.47); the spread costs 0.22 R a trade at the median, as in the 12 EMA family (the stop at the sweep extreme was supposed to make the spread a smaller share; it did not).
- **Gold:** XAUUSD alone loses -0.065 R (best variant -0.004, t at most -0.07, 553 trades per variant), XAUUSD + NSDQ -0.075; no variant is positive. London is worse than NY (-0.260 against -0.220). No market has a positive median on real quotes (least negative GBPUSD -0.014, EURJPY -0.030, USDJPY -0.041; crypto -0.76 to -0.86).
- **At zero spread 16 of 46 markets have a slightly positive median** (GBPCAD +0.035, GBPNZD +0.028, GBPUSD +0.026 ...): a ceiling MT5 broker's spread removes, picked out of 46 markets; not a candidate.

## What it means
- A mechanical sweep reversal (a new 10-candle extreme against the trade, then a gap or a displacement candle breaking structure in the reversal direction, stop at the sweep extreme) has no edge on any of the 46 markets, and the sweep itself carries no information over a plain confirmation candle.
- Together with the 12 EMA family (2,044 mechanical trials on MT5 broker prices, then the same 1,000 variants re-run with no spread, limit entries and pullbacks: 0 passes) the mechanical versions of both of his setup families are closed. It does not test his discretion: what he adds by hand (which sweep, which block, HTF bias, the day) is exactly what only the blind replay and the forward log can measure.
- The 2026 hold-out stays sealed; nothing goes near the account.
