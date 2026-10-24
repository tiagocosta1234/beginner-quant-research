# PREREG_F2PROXY: does a 2R target beat 1:1 on a mechanical proxy of our F1 entries? (GC futures 2020-2025)

Written 24 Oct 2026 ~22:5x local clock, before any outcome was computed. the trader: "wanna backtest it?" after the in-sample replay check (27 entries: 1R mean +0.00, 2R mean +0.21; `rr_target_test_jun2026.py`).

## Data
Databento GC 1-minute (`desk.raw()`, local clock). Weekdays. A day is skipped if 00:00-21:00 has < 900 bars or any minute-to-minute |close change| > 8 (roll / bad data). 2026 is NOT used.
DEV 2020-01-01..2022-12-31, VAL 2023-01-01..2024-12-31 (judged), HOLD 2025 (one look, only if VAL passes).

## Proxy rules (fixed)
- Daily trend: sign(previous day's 21:59 close - mean of the last 20 such closes).
- 1h trend: 1h closes up to 07:59; EMA20 of them; up if last close > EMA and EMA rose over the last 4 bars; down if the mirror; else none.
- Trade only if daily and 1h agree (no "clean level" condition: that part of F1 is discretionary and is NOT tested here).
- Entry 08:00 open. Stop: long = lowest low 00:00-07:59 - 1.0; short = highest high + 1.0. Skip if risk < 5 or > 60 points.
- Exit: stop, target k x risk, or 21:00 close. k in {1.0, 1.5, 2.0, 3.0}. Stop checked before target inside a bar (conservative).
- Cost 0.4 points per trade.

## Bars (VAL, one look)
PASS if mean R(2.0) > mean R(1.0) AND mean R(2.0) > 0 with one-sided t P <= 0.05. Reported, no bar: all k, DEV, long/short split, win rates.
## Honest prior
Most mechanical trend-at-08:00 tests here lost (BIAS8, EMA15, DIR8). Expect mean R near 0 for all k; the point is the RELATIVE effect of the target size.
