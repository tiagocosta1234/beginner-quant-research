# DAY2K result (2026-10-14): one setup per day, 1:1, +/-2,000 USD on 28 FX pairs - NO EDGE

Pre-registration `PREREG_DAY2K.md` (commit ff37067f), engine `day2k.py`, cells in `D:\finance\si_ledgers\DAY2K_cells.csv`. MT5 broker M1 bid/ask, 28 pairs, DEV 2021-12..2024-12 (about 785 trading days per cell), VAL 2025 (about 258). HOLD (2026) never loaded.

## Gates
- Dry-run: server clock confirmed; truncation test 40/40 after amendment A1 (ATR20 definition; no rule changed); hand check matches.
- Positive control (oracle side): +0.37..+0.81 R by cell (the best-resolved cell +0.81; lower elsewhere because unresolved days close at 21:55 with a partial result). The engine sees an edge when there is one.
- Placebo worlds 81-83 (random scores, same pipeline): 0 / 0 / 0 survivors, best DEV t 1.33 / 1.82 / 0.11. Calibrated.

## The 24 cells
S1 survivors: **0**. Every DEV mean is between -0.059 and +0.014 R; none reaches t +2.86 (best DEV t +0.57, AM-cont-T1005-k0.7). Negative DEV t of -2.0 to -2.2 sits on the AM signals at T10:05 fade and T16:35 continuation, i.e. nothing systematic beyond noise and cost. VAL: the best t is +1.93 (M1-fade-T1635-k0.4, DEV -0.029 R) and the worst -3.54 (M1-cont-T1635-k0.4): signs flip between DEV and VAL, which is what noise does. Continuation signals are mostly negative in VAL (M5-cont -1.8..-2.8, M1-cont -2.8..-3.5), fades mostly positive, but the same fades were negative in DEV: not a lead.
No-skill baseline (a random pick) costs -0.017 to -0.030 R per trade: that is the spread, about 60 USD per trade at 2,000 risk.

## "+/-2,000 every day" in practice
Share of trades that end by stop or target before 21:55: T10:05 k0.4 74%, k0.7 31%; T16:35 k0.4 40%, k0.7 9%. A stop 0.4 ATR(20) away is the tightest registered and still leaves 26% of days unresolved (closed at 21:55, partial result). Fixing it by tightening further raises the cost share: spread / (2 D) grows as D shrinks.

## What a coin flip does under the MT5 broker rules (random pair and side each day, 60 worlds, rolling starts, +8,000 target, -8,000 floor, 2,000 counted per day)
| cell | resolved | pass | breach | median days to pass |
| T10:05 k0.4 | 72% | 42.7% | 57.3% | 18 |
| T10:05 k0.7 | 30% | 43.4% | 56.6% | 33 |
| T16:35 k0.4 | 39% | 37.0% | 63.0% | 28 |
With no edge each attempt is about 43% to pass and 57% to breach (451 USD per failed attempt, about 2.3 attempts per pass, about 1,030 USD of fees). That is a gamble, not a strategy, and MT5 broker lists coin-flip / gambling-style betting as prohibited. It is also why the pass-by-date numbers of the gold pair are higher than this: the pair has a measured positive drift; this design has none.

## Reading
Choosing the pair and the side by 5-day momentum, 1-day momentum or the morning move, continued or faded, at the London or New York open, with the stop and target one 0.4-0.7 ATR(20) away, has no edge on 28 FX pairs in 2021-12..2025: the 24 cells are between -0.06 and +0.01 R, the calibration shows the engine can see +0.4..+0.8 R, and placebo worlds produce nothing. Power: 785 days gives SE about 0.035 R, so an edge of +0.10 R (win share 55%) would have shown; below +0.05 R is invisible. Consistent with the earlier families (FX battery 0/616, FX factors, trend/reversal). Nothing to deploy; HOLD stays unopened.
