# Apprentice lessons (Claude trading the trader's setup blind on the desk; the trader grades; written 22 Oct 2026 ~21:1x local)

Rules traded: `desk.py` header (rules card + the trader's refinements, S1 bracket, entry 08:00-08:15 local, one trade a day).

**Grades:**
- A = with the trend, body at least 1 ATR, clean close, volume above the median;
- B = one of those missing;
- C = two or more missing, and is skipped.

| # | Day | Lesson | Changed a rule? |
|---|---|---|---|
| 1 | D001 (MT5 broker CFD) | Jumped from 07:59 to 08:03 and saw the next candles before deciding: the 08:01 long had to be forfeited (it would have hit 1:1 the next minute). **Process first.** The desk now moves one minute at a time. | desk only |
| 2 | F001 | Aimed at the session low (the farthest "whole" gap); price stalled 1.2 points short, reversed, -1.05R. The nearest gap at 1 ATR or more would have paid +1R in 10 minutes. One day is not evidence: **target = the nearest level at least 1 ATR away**, as the S1 rule says, then keep counting. | no (back to the written rule) |
| 3 | F005 | Skipped a C-grade short (third cross in 6 minutes, flat EMA, against the 2-hour trend). In hindsight it would have reached the target (shadow, not counted). **Keep a shadow column for skipped setups**: after about 30 days, compare the R of the A / B trades taken with the C trades skipped, and only keep the grading if it helps. | no |

| 4 | F009-F017 | One-notch downgrades of counter-trend B setups (not pre-declared): 1 saved -1.05 R, 2 missed +0.66 / +0.97. **No more overrides**; the rubric decides. | rule: no overrides |
| 5 | all 64 days | Grade A (big body, volume, trend, no chop) went 0 / 6. Over 2020-2025 (`rubric_backtest.py`) grade A is -0.22 R on 150 setups: big displacement candles on 1-minute gold are slightly worse, not better. | none (descriptive) |
| 6 | all | **The rubric has no edge.** Every card-valid setup is a coin flip (49-51% at 1:1), and futures costs (2 ticks + commission, about 0.1 R at these brackets) make it negative. Code run over 1,328 days 2020-2025: 632 trades, 50.6% wins, -0.114 R (se 0.039), negative in every year. My 28 hand trades (-0.30 R) are that coin flip with bad luck. Any edge has to come from the trader's discretion, which blind batch 2 tests. | none |

## Scoreboard
| Desk | Days | Trades | Wins | R |
|---|---|---|---|---|
| MT5 broker CFD (before the switch) | 1 | 0 | 0 | 0 |
| Gold futures | 5 | 3 | 2 | **+0.98** (F001 -1.05, F003 +1.10, F004 +0.94) (first batch, 21:1x) |
| Gold futures, all of 22 Oct night | 64 (the whole Sep-Nov 2024 pool) | 28 | 11 (39%) | **-8.51** (mean -0.304, se 0.189); A 0 / 6 (-1.10), B 11 / 22 (-0.09) |
| Shadow (card-valid setups skipped) | | 41 | 23 | +0.008 mean (C -0.007, the 3 downgraded B +0.194) |
| Code, same rubric, 2020-2025 | 1,328 | 632 | 50.6% | **-0.114 mean** (se 0.039) |

Skipped and shadowed: F005 C short, about +1R in hindsight.

## Live tool for the London session
- `live.py` reads the chart in TradingView Desktop (CDP 9333, read-only) and applies the same card and rubric to each candle that closes in 07:59-08:14 local.
- It prints the first A / B call (paper) and logs it in `LIVE_LOG.csv` before the outcome.
- Tested with `--replay` on 22 Oct: a 07:59 short B (S1 stop 4103.85, target 4081.48) would have hit the target at 10:00, +0.98 R (hindsight, test only). the trader's own tighter stop on the same candle was stopped at 08:08.
