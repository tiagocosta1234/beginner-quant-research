# EMA15_RESULT: FAIL at DEV (23 Oct 2026 22:0x local, local clock)

Pre-registration `PREREG_EMA15.md` (commit 6131c195, sha256 in `PREREG_EMA15.sha256`). Full tables in `EMA15_OUTPUT.txt`, trades in `EMA15_TRADES.csv`.

## The rule
- 15-minute 12 EMA cross in the trend direction.
- Signal bars 08:00-11:45 local; one trade a day.
- Exit 1:1 at the nearest unmitigated FVG edge or clear high/low (at least 0.5 ATR away).
- GC futures, desk costs.

## Results (mean R per trade after costs; before costs in brackets)
| Trial | DEV 2019-07..2022 | VAL 2023-24 |
| --- | --- | --- |
| T50 (above rising EMA50) | 483 trades, 49.3% win, **-0.160 R** (-0.083), t -3.40 | 285, 43.2%, -0.282 R (-0.210) |
| T80 (above rising EMA80) | 507, 48.9%, -0.170 R (-0.095) | 299, 44.8%, -0.250 R (-0.177) |
| TPD (prev-day direction) | 576, 47.2%, -0.192 R (-0.117) | 329, 47.7%, -0.182 R (-0.112) |
| no trend filter | 673, 49.3%, -0.153 R (-0.078) | 383, 52.7%, -0.081 R (-0.010) |
| T50 inverted (fade it) | 483, 47.8%, -0.193 R (-0.116) | 285, 53.7%, -0.065 R (+0.007) |

## Verdict
- **FAIL at DEV.** No trial has a DEV mean above 0; the best is T50 at -0.160 R. HOLD 2025 was not opened.
- **The trend filter makes it worse.**
  - On VAL every trend version is below the same rule with no filter (-0.081 R).
  - The inverted rule is about flat before costs. The direction call is noise.
- **Costs are about 0.07-0.08 R a trade**, because the 1:1 distances to the nearest level are small: a median D of a few dollars.
  - Even before costs every trial is at or below 0.
- **Longs beat shorts in DEV** (gold's uptrend), but they still lose after costs.
- **the trader's live bar is +0.5 R a trade.** The best number here is -0.065 R.
- This joins EMA12 0/32, MANUALRULE 0/12 and EMA1000 0/1,000: the 12 EMA cross does not have an edge on 1, 3, 5 or 15-minute gold bars. Not re-tuned, per the pre-registration.
