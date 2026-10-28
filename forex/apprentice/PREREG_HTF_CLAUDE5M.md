# PREREG_HTF_CLAUDE5M: does a professional higher-timeframe + fundamental bias rescue "claude 5min GC"?

Written Tue 2026-10-27 (local clock) BEFORE any result of this test. the trader: "think about this as a professional trader that adapts to the market
through fundamentals and HTF analysis (daily and weekly)". The indicator alone, replicated 2019-06..2026-09 (`open5m_history.py`): -0.117 R a
trade, 2,808 trades; its own recent results do not predict the next month (`OPEN5M_REGIME_OUTPUT.txt`).

## Trades
Every London (08:00 London) and New York (09:30 New York) 5-minute setup of the indicator's defaults on GC 1m (Databento) resampled to 5m,
2019-06..2026-09, each computed for BOTH sides with the indicator's own stop (|close - extreme| + 0.5 x candle range, floor 0.03 x prior ATR14),
1R target, exits at TP / SL (same bar = SL) / open + 60 min, cost 0.32 pt. One loss ends the day inside each variant (a London trade taken and
lost -> no New York trade that day).

## Biases (all known before the trade day: prior day / last COMPLETED week)
- **W weekly:** last completed week's close above its 10-week average AND the average rising over 4 weeks = up; below and falling = down; else none.
- **D daily:** prior day's close above its 20-day average AND the average rising over 5 days = up; below and falling = down; else none.
- **F fundamentals:** US 10-year real yield (FRED DFII10) down over its last 5 values AND euro futures (6E, inverse dollar) above its 20-day
  average = up; real yield up AND 6E below its average = down; else none.
- **HTF = W and D agree; HTF+F = W, D and F all agree.**

## Variants (5; alpha 0.05 / 5 = 0.01)
V1 W filter; V2 HTF filter; V3 HTF+F filter (take the indicator's setup only when its side equals the bias); V4 HTF override; V5 HTF+F override
(trade the bias side at every setup; the candle only sets stop and target). No bias = no trade.

## Bar (one run, one look)
A variant "works" iff mean net R > 0 AND random P <= 0.01 AND mean > 0 in at least 5 of the 7 years 2020-2026 AND n >= 300.
Random P: filters = 20,000 random subsets of the indicator's own trades of the same size; overrides = 20,000 coin flips of each trade's side.
Prior (honest): the same family of filters on the 15m London version passed 0 of 7 (PREREG_FUNDAMENTALS_GOLD); expected: no pass.

## RESULT (one run, Tue 2026-10-27 ~00:5x; `htf_claude5m.py` -> HTF_CLAUDE5M_OUTPUT.txt) -- 0 of 5 work
Indicator alone -0.117 R (2,808). V1 W filter -0.126 R (1,231, P 0.68); V2 HTF filter -0.121 (830, P 0.57); V3 HTF+F filter -0.098
(350, P 0.34); V4 HTF override -0.197 (1,361, P 0.85); V5 HTF+F override -0.154 (581, P 0.54). Every variant is negative in EVERY year
2019-2026. The weekly / daily / real-yield / dollar context does not change what the first 5-minute candle's 1:1 trade does in the next hour.
