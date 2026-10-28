# PREREG_PHASE_ORB: an opening-range breakout in the trend's direction, only in high-volatility trend phases

Written Tue 2026-10-27 ~01:1x (local clock) BEFORE any result. the trader: "then bring an indicator that will thrive in our current phase" (gold now:
high volatility, downtrend). claude 5min GC was negative in every phase (OPEN5M_PHASE_OUTPUT.txt).

## Phase (known before the day, each market's own daily chart)
High volatility = prior-day ATR14 > 1.25 x its 250-day median. Trend = prior close below the 50-day average AND the average down > 1% over
20 days (downtrend), or above AND up > 1% (uptrend). The strategy trades ONLY on high-volatility trend days, only in the trend's direction.

## Strategy (one trade per session)
Opening range = first 15 minutes (London 08:00 for GC and SI; New York 09:30 for NQ, ES, GC and SI). Entry = a stop order 1 tick beyond the
range low (downtrend: short) or high (uptrend: long), placed at the range's end, valid until 60 minutes after the open. Stop = the other side of
the range. Target = 1R (1:1). Exit at TP / SL (same bar = SL) / 16:00 London or 15:55 New York. Data: Databento 1m 2019-06..2026-09.
Costs: GC 0.32, SI 0.025, NQ 1.1, ES 0.74 points round trip.

## Bar (one look)
Works iff pooled mean net R > 0 AND random-side P <= 0.05 (20,000 flips of each trade to its mirror: opposite side, same range and times)
AND mean > 0 in at least 3 of the 4 markets AND n >= 150. Reported, not gating: the same rule on days that are NOT high-vol trend days.

## RESULT (one look, Tue 2026-10-27 ~01:1x; `phase_orb.py` -> PHASE_ORB_OUTPUT.txt) -- NOT SHOWN
High-vol trend days: 1,163 trades, 51.3% wins, mean -0.069 R, random-side P 0.22, markets positive 2/4 (GC +0.002, NQ +0.030, ES -0.047,
SI -0.182); gold shorts in high-vol downtrends +0.022 R over 54 trades. Non-phase trend days -0.124 R: the phase makes the breakout less bad,
not profitable after costs.
