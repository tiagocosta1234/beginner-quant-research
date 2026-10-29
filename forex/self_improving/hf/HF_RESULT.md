# Frequent-trading family on real ticks: result (2026-10-13)

Pre-registration: PREREG_HF.md. Code: ticks_pull.py (read-only export), hf_data.py, hf_lab.py. Ledgers: data\si_ledgers\HF_real.csv, HF_placebo61..63.csv. Ticks data\ticks (46 symbols, 2025-10-01..2026-10-13), features data\ticks_feat (12 symbols). The family's HOLD (2026-08-16 onwards) was never loaded.

## Setup
12 liquid markets in 4 classes, a decision every minute from ticks only (momentum over 1 s .. 4 h, tick-RV, quote activity, spread level and change, bid/ask up-down counts, day extremes, time, minutes to / since CPI, NFP, FOMC); 300 ms latency; market orders and limit entries (d = 0 and 1 bp, 60 s validity, the MT5 fill rule: a buy limit fills when the ASK reaches it) at H = 1, 5, 15, 60 minutes; XGBoost per cell; windows A 2025-10..2026-02 (training), B 2026-03..05 (early stopping and threshold), VAL 2026-06-01..08-15 (one look); no decisions or exits in server hours 23 and 0. 48 cells; pass = >= 2,000 non-overlapping trades, >= 20 day clusters, net mean > 0 and excess p < 0.05/48.

## Calibration: PASSED
Placebo worlds 61, 62, 63 (labels circularly shifted, features and all real costs and fills kept): 0 of 48 cells pass in each; noise ceiling over 144 cells: max VAL net +0.41 bp, max excess z 2.43. Feature causality: truncating the future changes none of the tick features (SP, 172,216 decisions).

## Real run
0 of 48 cells pass. No cell has a positive net mean on VAL: best -0.35 bp (idx, market order, 15 minutes, 2,184 trades); median -1.27 bp (market -1.06, limit at the touch -1.36, limit at +1 bp -1.35; fx -0.95, idx -0.92, XAUUSD -1.28, BTC -10.99). The best excess z is 2.46 (fx, limit at the touch, 1 minute, p 0.009), inside the placebo ceiling (2.43), and its net is -0.51 bp: whatever timing skill exists is smaller than the spread.

## Verdict
At 1-60 minute horizons on liquid MT5 broker, with real tick spreads and 300 ms of latency, the microstructure information of the quote stream plus time and macro-calendar context does not beat costs: the typical net of a model-selected trade is -1 bp and no cell is positive, the best z is at the noise level. Passive limit entries do not help on an MT5 dealer-model account (fill when the ask arrives, so the cost is paid anyway). The frequent-trading family as designed is closed; the installed system stays.

## What would change it (untested)
Lower costs than a retail CFD spread (not available to us), information not in the quote stream (real trade prints and volume, order book depth, news text, event surprises), horizons below 1 s (latency-bound), or a different venue. A year of ticks is also a single regime.

## Rerun with the corrected clock (2026-10-13 ~11:55): SUPERSEDES the result above
The first run treated the tick epoch as UTC (server hour, weekday, event features and the rollover exclusion were 2-3 hours off); fixed in hf_data.py (lesson L13). Rebuilt features, SDS cycle: engine code bff3ff48af6b, placebo worlds 304, 305, 306 all 0 passing cells (calibrated), real run: 0 of 48 cells (NO_FINDING). Details in data\si_ledgers\HF_sds_hf_real_bff3ff48af6b.csv. The conclusion of the family does not change.
