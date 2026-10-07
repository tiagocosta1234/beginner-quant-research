# S2 (CFTC positioning) and S3 (FOMC pre-announcement drift) pre-registration, written 2026-10-07 before any result

Both use decades of data that no earlier test of ours has touched. k = 5 hypotheses in total (S2: 2, S3: 3): every t-statistic bar below is 2.6.

## S2: speculator positioning (new information, not a price pattern)
Data: CFTC legacy Commitments of Traders, futures only, 1986-2026 (`forex/early_mt5/factor_lab/data/cot/`, public zips). Net position NP = (non-commercial long - non-commercial short) / open interest, weekly as of Tuesday, released Friday 15:30 ET.
Markets (8): EUR, GBP, JPY, CHF, CAD, AUD, NZD (CME currency futures; long = long that currency vs USD) and gold (COMEX). Prices: FRED noon rates for FX (Track A files), Yahoo daily gold futures close (`futures/data/daily_ohlc/GC=F`). FX carry accrual `(r_ccy - r_usd)/52` (OECD 3-month rate of the entry month).
Timing (no look-ahead): the Tuesday report is known on Friday; entry at the Monday after at noon (FX) / close (gold) = report date + 6 days; exit the following Monday; weekly returns. Positions can persist week to week.
- S2-C CONTRARIAN EXTREME: percentile of NP in its own trailing 156 weeks; >= 90th -> short, <= 10th -> long, otherwise flat.
- S2-T POSITIONING TREND: sign of NP(t) - NP(t - 13 weeks): long if positive, short if negative, always in.
Each market is scaled to 10% annual volatility (trailing 26 weekly returns, leverage cap 3) and weighted 1/8 (fixed denominator 8). Costs: 1.2 / 1.5 / 4 bp per unit traded for FX as in Track A, 1.5 bp gold; financing markup 1.5% a year on gross notional.
Phases by entry week: DEV 2000-01..2012-12, VAL 2013-01..2020-12, HOLD 2021-01..2025-12 (rates end 2026-01). HIT: DEV+VAL pooled annualised net Sharpe >= 0.4 AND t >= 2.6; positive in DEV and in VAL; drop each of the 8 markets in turn: Sharpe >= 0.25 for at least 6 of 8; then HOLD net Sharpe > 0 and positive in both halves (2021-23, 2024-25).

## S3: FOMC pre-announcement drift (a known flow mechanism)
Events: `futures/data/events/fomc_statement_dates.csv` (every statement date since 2000; the announcement is at 14:00 ET on that date).
Event return = close(D-1) -> close(D) of the daily series (D = statement date), compared with the mean of all NON-event days of the same series. Net of 3 bp round-trip cost.
- S3-A US equities: S&P 500 cash index (`external_index_daily/spx.csv`), long. (Includes the 2 hours after the announcement; accepted.)
- S3-B European equities: DAX (`external_index_daily/dax.csv`), long: Europe closes at 11:30 ET, so close(D) is BEFORE the announcement: a clean pre-announcement window.
- S3-C USD basket from FRED noon rates: noon(D-1) -> noon(D) (before 14:00 ET); two-sided (no direction was documented): the sign is whatever the DEV+VAL mean shows and must repeat in HOLD.
Phases by event date: DEV 2000-2011, VAL 2012-2020, HOLD 2021-2026. HIT: DEV+VAL pooled mean excess return t >= 2.6 AND positive (S3-C: same sign) in DEV and in VAL; then HOLD: mean net return of the same sign and positive hit rate above 50%. Reported always: n, mean in bp, hit rate, annualised Sharpe at 8 events a year, and the mean at 5x leverage per year (descriptive: what the premium is worth to an account).

## After any hit
Placebo (200 random event-date sets of the same size drawn from non-event days for S3; random-sign for S2), leverage and drawdown fit for an MT5 broker account, then a claim. If nothing passes, both ideas are closed and nothing is tuned.
Dry run: `python -m mt5broker.factor_lab.cot_fomc_test --dry-run` prints coverage and counts only.

## Replication addendum (written 2026-10-07 after the S3-B hit, BEFORE running it; replication, not discovery)
If the DAX result is the pre-announcement drift and not an accident, the two other European cash indices that also close before the 14:00 ET announcement should show the same sign: FTSE 100 (11:30 ET close) and CAC 40 (11:30 ET close). Same definition as S3-B (close(D-1) -> close(D) minus the mean of non-event days, net of 3 bp, long). Also Nikkei 225 for reference (closes 02:00 ET on D: a different, earlier window; expected weaker). REPLICATION PASS: FTSE and CAC each have a positive pooled DEV+VAL excess with t >= 2.0 and the same sign in DEV and VAL. Reported, not a pass criterion: HOLD 2021-2026. Whatever the outcome it is reported; nothing is selected from it.
