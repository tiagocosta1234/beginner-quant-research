# London open on micro gold (last week of October 2026)

The final week of the project went back to CME futures, mostly gold (GC / MGC) at the London
open, with one Nasdaq test in the Tokyo session. Every number below is net of costs (fees plus
one tick of slippage per round trip; about 0.32 points on gold) and in R, the stop distance.

## The London-open rule

`london_open_indicator.pine` (TradingView, 1-minute chart) draws one setup a day: a bias from the
15-minute candle before 08:00 London (close and EMA12 slope), a trigger on the first 1-minute
candle that crosses the 1-minute EMA12 on the bias side between 08:00 and 08:14, a stop beyond
the last few candles, and a 1R target. An "A+" setup also needs 2 of 3 confluences (a recent
fair-value gap, the Asia range swept, the 07:00 hourly candle on the bias side).
`daily_trend.pine` adds two filters found afterwards (post-hoc, so untested).

| test | result |
|---|---|
| 2026, GC/NQ/ES/SI, A+ (`LONDON_APLUS_2026_OUTPUT.txt`) | 213 trades, 49% wins, -0.170 R a trade |
| Same rule on 8 micro contracts, Aug-Oct 2026 (`MICROS_BACKTEST_OUTPUT.txt`) | gross +0.12 R, net -0.04 R: costs were 16% of the risk |
| 16-cell filter search, one look at TEST (`PREREG_SIGNAL_SEARCH.md`) | +0.012 R, NOT SHOWN |
| Asia-range sweep and reclaim ("PO3"), 32 cells (`PREREG_PO3_SEARCH.md`) | every cell about -0.10 to -0.13 R; closed |
| Targets in standard deviations of the range (`STDV_PO3_OUTPUT.txt`) | win rates of 15-17%, -0.21 to -0.33 R |
| Target sweep, 0.25R to 1R (`TARGET_SWEEP_OUTPUT.txt`) | win rate rises from 50% to 69% as the target shrinks, the loss per trade grows |

The target sweep is the clearest lesson: a smaller target wins more often but loses more per
trade, because the fixed cost becomes a bigger share of a smaller win.

## Tokyo session on MNQ

`PREREG_TOKYO_MNQ.md` froze three hypotheses on the 00:00-06:00 UTC window before the run: follow
the first 15-minute candle, fade it, or trade a break of the first 30-minute range. On the
2023-2026 TEST period (965 days) they made -0.051, -0.009 and -0.021 R a trade. NOT SHOWN.

## Half-R comparison and test

`HALF_R_OUTPUT.txt` / `HALF_R_GROSS_OUTPUT.txt` compare the rules above at a 0.5R target: a
random 0.5R bracket wins about 65% of the time, so a 65% win rate at half R is the baseline, not
an achievement. Net of costs every rule was at or below zero.

`PREREG_HALFR_FXR.md` (with `PREREG_HALFR_FXR_AMENDMENT1.md`) registers a 200-trade test of a
discretionary half-R setup played on replayed history: the bar is a 74% win rate, a positive mean
R after costs and a bootstrap P of 0.05 or less, scored once by `score_halfr.py`. It was
registered at the end of the project and never run to completion here.

## Files

- `london_aplus_2026.py`, `micros_backtest.py`, `merge_micros.py`: the 2026 and micro-contract backtests
- `signal_search.py`, `po3_search.py`, `stdv_po3.py`: the pre-registered searches
- `tokyo_mnq.py`: the Tokyo test; `score_forward.py`, `score_halfr.py`: scorers for forward and replay logs
- `*_TRADES.csv`, `TOKYO_MNQ_DAYS.csv`: trade-level results (derived, no raw bars)
