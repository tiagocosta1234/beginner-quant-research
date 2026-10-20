# PREREG_EMA1000: 1,000 variations of the 12 EMA rule on all 46 MT5 broker (written 2026-10-20 10:08 local, local clock, main PC) BEFORE any P&L of this family exists

the trader 2026-10-20, going to class: "explore different 1000 variations of my strategy in all symbols". Claude designs and runs it unattended. It tests whether the trader's described rule (PREREG_MANUALRULE.md) or a near variant has a MECHANICAL edge on any MT5 broker market; it says nothing about his discretion.

## Declared prior evidence
44 trials on MT5 broker gold and Nasdaq 2022-25 (EMA12_RESULT.md 32, MANUALRULE_RESULT.md 12): 0 candidates, DEV mean R -0.02..-0.15 a trade. The 46-market universe, the timeframes 3m / 5m, the swing high / low target and the 20 / 8 EMA lengths have not been tested before. Honest prior that any variant passes the bars below: about 3%.

## Data and periods (the 2026 days are NEVER loaded)
MT5 broker M1 bid / ask (`forex/data_mt5/<MARKET>_M1_rates.parquet`), server clock, markets = all 46 files. DEV 2022-01-01..2024-12-31, VAL 2025-01-01..2025-12-31. Nothing after 2025-12-31 is read; the sealed 2026-02-01..09-30 days of the blind replay stay untouched. One look at any 2026 data only for a variant that passes everything below, and only after the trader has been told.

## The family: 1,000 variants, drawn once
Full grid of 4,860 cells = EMA length {8, 12, 20} x signal timeframe {1, 3, 5 minutes} x body filter {none; body > bigger wick; body > bigger wick and body >= 0.5 x ATR14} x entry window {first 15, 30, 60 minutes after the open} x target {K1, K2, K3, SW, ATR1} x stop multiple {1.5, 2, 3 x the target distance} x session {London 08:00 London, NY 09:30 New York} x trend filter {none; direction of the last 30 minutes}.
The 1,000 variants are `np.random.default_rng(20261020).choice(4860, 1000, replace=False)` over the grid in itertools.product order of that axis list (ema, tf, body, win, tgt, stop, ses, trend). No variant is added, dropped or retuned after the first P&L is seen. Every variant runs on every market (46) = 46,000 trial series.

## Rule (all choices fixed here)
- Bars of the signal timeframe are built from 1-minute mid candles aligned to the clock (3 / 5 minutes: only complete bars). EMA = EMA of the bar closes over the whole series; ATR14 = mean mid range of the 14 bars before the signal bar; bars with index < 100 are skipped.
- Signal bar t, bar start inside the window: mid open and mid close on opposite sides of the EMA at t (direction = side of the close); body filter as listed; trend filter: direction of the last 30 one-minute closes must equal the signal direction. First qualifying bar a day with a usable target; one trade per market, session and day; weekdays only.
- Entry at the open of the 1-minute bar after the signal bar ends (ask for longs, bid for shorts), skipped if that minute is more than 2 minutes late.
- Targets: K1 / K2 / K3 = the MANUALRULE FVG targets on signal-timeframe bars (nearest unfilled FVG against the trade within the last 90 bars, near edge at least 0.5 x ATR14 beyond the entry; K1 far edge if the gap is at most 1.5 x ATR14 wide else its middle, K2 near edge, K3 far edge); SW = nearest confirmed 5-bar swing high (longs) / low (shorts) within the last 90 bars at least 0.5 x ATR14 beyond the entry; ATR1 = 1.0 x ATR14. A candle without a usable target is skipped and later candles in the window are scanned.
- Stop = stop multiple x the target distance on the other side. Exits on the real side of the book, stop first if both fall in one 1-minute bar, time exit after 60 one-minute bars. R = +1 / stop multiple for a target, -1 for a stop.

## Statistic and acceptance (family of 1,000: one-sided 0.05 / 1000 -> z >= 3.72)
Per variant the trades of all 46 markets are pooled; t is clustered by calendar day (trades of different markets on one day are not independent). A variant is a CANDIDATE only if ALL hold: DEV n >= 3,000, DEV mean R >= +0.03, DEV clustered t >= 3.72; VAL mean R > 0 and clustered t >= 1.65; mean R > 0 in each of 2022, 2023, 2024; and without the single best market (by DEV total R) DEV mean R > 0 and t >= 2.5. Reported but never a bar: per-market tables, the share of markets with positive mean R, the best 20 variants, the distribution of t over the 1,000, and for the top 5 the same entries with a random side (excess over chance).
## Engine checks before the run (dry run, no new P&L)
(1) variant EMA 12 / 1m / body wick+ATR / window 15 / K1 / stop 2 / London and NY must reproduce MANUALRULE_TRIALS.csv (n, mean R, t on DEV) for XAUUSD and NSDQ; (2) truncation test: signals recomputed with the future cut must match on a random sample of trades for several variants; (3) hand check of 3 signals; (4) trades per year and market.
## Kill rule
1,000 variants are logged in the ledger as one window; no second batch on this data after seeing the result; a negative result is reported plainly.
