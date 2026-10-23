# EMA15B_RESULT: FAIL at DEV (23 Oct 2026, local clock in the commit)

Pre-registration `PREREG_EMA15B.md` (commit e1e0d3ec). It is EMA15 with the trader's minimum target of 2.5 points ($1,000 at 40 MGC), sized so a winner pays about $1,000 (max 40 MGC). Tables in `EMA15B_OUTPUT.txt`, trades in `EMA15B_TRADES.csv`.

| Trial | DEV 2019-07..2022: trades, win, mean R (before costs), $/trade, $/yr, max DD | VAL 2023-24 |
| --- | --- | --- |
| T50 | 431, 49.0%, **-0.074 R** (-0.032), -$73, -$9.0K/yr, DD $34.9K | 256, 42.6%, -0.219 R, -$213, -$27.3K/yr |
| T80 | 457, 50.1%, -0.060 R (-0.018), -$60, -$7.8K/yr, DD $29.3K | 270, 44.4%, -0.177 R, -$23.3K/yr |
| TPD | 541, 49.4%, -0.064 R (-0.023), -$64, -$9.8K/yr, DD $57.1K | 305, 45.9%, -0.150 R, -$22.3K/yr |
| NONE | 649, 49.0%, -0.064 R (-0.023), -$62, -$11.6K/yr, DD $59.7K | 377, 51.2%, -0.040 R, -$7.3K/yr |

- **FAIL at DEV:** no trial is above 0. HOLD 2025 was not opened.
- **The wider minimum target helped costs:** they drop to about 0.04 R a trade (from about 0.08). Median target 3.4-3.8 points, median size 26-29 MGC.
- **The win rate is still about 49% at 1:1,** so it still loses. Before costs it is about -0.02 R in DEV.
- **The trend filters again do worse than no filter on VAL.**
- **At this size the drawdowns ($29-60K) are 15-30 times a Broker 50K's $2,000 trailing limit.**
