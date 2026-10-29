# DAY2K-G result (2026-10-14): the strongest-trend market of the day, traded with the trend, wide 1:1 held until hit - NO EDGE

Pre-registration `PREREG_DAY2K_G.md` (commit eff3c76b, amendment A1 66b4c854), engine `day2kg.py`, cells `data\si_ledgers\DAY2KG_cells.csv`. 34 liquid markets, trend score L in {20, 60, 120} days / ATR20, pick the market with the largest |score|, trade its direction, stop = target = 1.0 / 1.5 / 2.0 ATR20, held until hit. HOLD unopened.

## Calibration (a failure, then an amendment, both before any real cell was read)
Placebo worlds built by shuffling the days of the scores produced one survivor each in two of three worlds: the shuffled pick mix (BTCUSD, XAUUSD, USDJPY, mostly long) earns the 2023-25 drift, so it is not a null for timing skill. A1 added a same-mix permutation null (picks shuffled among days) as a requirement; the gate then passed (placebos 0/0/0, oracle +0.96..+0.99 R).

## Result (9 cells)
S1 survivors **0**. DEV mean R per trade: -0.026..+0.078; the same-mix shuffled picks earn MORE (+0.034..+0.114): choosing the strongest-trend market at the moment hurts relative to a random pick with the same market and side mix (permutation p 0.78-1.00). Win share of resolved trades 50.2-55.7%. VAL 2025 is positive in every cell (+0.03..+0.32 R, best L60-k2.0 t 3.19) but that is the 2025 gold/BTC/index trend year, and the gold-only yardstick earns more in every cell (VAL +0.07..+0.65 R). By year the picks win 43-65% with no stable pattern.
MT5 broker one-at-a-time cycles at 2,000 risk: pass 36-82% of finished rolling starts but with median 29-202 business days, 100-376 trades in 4 years, and gap losses up to -3,392 (L120-k2.0: 56% wins, 100 trades, median 202 days).

## Reading
An adaptive "trade the strongest trend" selector does not produce a higher chance of a +2,000 than -2,000 trade: it is 50-56% wins, below what gold alone gave in the same years, and no better than random picks with the same mix. Seven registered rounds (A-G) now close the one-setup-a-day 1:1 design on MT5 broker prices.
