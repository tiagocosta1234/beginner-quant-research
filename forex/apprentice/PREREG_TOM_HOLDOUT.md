# PREREG_TOM_HOLDOUT: turn-of-the-month on untouched years (1993 - May 2019)

Written Mon 26 Oct 2026 ~13:0x local (local clock), AFTER PREREG_SETTLE_TOM (P3 near-miss: ES+NQ TOM 09:30-15:55 ET, 623 trades, +0.051 ATR net, permutation P 0.0126 vs a 0.01 bar, NOT SHOWN)
and BEFORE any number of this holdout was computed. The 2019-06..2026-09 futures sample is NOT used here.

## Rule (same as P3, on daily ETF data)
TOM days = the last trading day of each month and the first 3 trading days of the next. Trade = long at the open, out at the close (= 09:30 -> 16:00 ET).
Data: SPY (1993-02 .. 2019-05-31) and QQQ (1999-03 .. 2019-05-31), Yahoo daily open / close (`futures/data/daily/*_yahoo_daily.csv`).
Days whose open equals the prior close exactly (stale-open data) are dropped and counted. Cost 0.02% of price round trip (about a micro ES / NQ round trip).
Returns in % (open-to-close minus cost).

## Bar (one look)
Pooled SPY + QQQ: TOM mean net > 0 AND TOM minus other-days mean > 0 with a month-block permutation P <= 0.01 (within each month and ETF, re-draw which days count as TOM, 20,000) AND TOM mean net > 0 in at least 60% of the calendar years.
Reported: SPY and QQQ alone, by decade, win rate. If it passes: TOM goes to a pre-registered forward test on Practice (about 4 trades a month), not to money.
