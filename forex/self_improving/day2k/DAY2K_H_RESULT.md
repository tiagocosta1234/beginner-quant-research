# DAY2K-H result (2026-10-14): will the rest of the day be bullish or bearish? - NOT PREDICTABLE with this information

Pre-registration `PREREG_DAY2K_H.md` (commit c6552be1), engine `day2kh.py`, cells `D:\finance\si_ledgers\DAY2KH_cells.csv`. Target: sign of mid(21:55 bar open) - mid(T+60 bar open), T in {10:05, 16:35}. Gold (1,005 days) and a pooled model over 34 liquid markets (35,000 rows), logistic regression and gradient boosting, walk-forward from 2022-12, features: own price structure, cross-market morning moves, USD strength, and for gold rates / gold vol / MT5 calendar / flow calendar. HOLD sealed.

## Gates
Leak control 100%; placebo worlds 161-163: 0 survivors (best DEV' t 0.51 / 1.90 / 2.36 against the 2.50 bar).

## Result (8 models)
S1 survivors **0**. Hit rates (share of days or market-days with the direction right), DEV' 2022-12..2024 / VAL 2025: gold T10:05 logistic 51.4% / 54.8%, boosting 54.7% / 51.2%; gold T16:35 logistic 53.0% / 52.8%, boosting 51.8% / 47.2%; pooled 50.1-50.8% / 48.9-51.5%. AUC 0.48-0.55. Best single number, gold T10:05 boosting at 54.7% (t 2.33, below the bar) falls to 51.2% in 2025 (t 0.34). The simple yardsticks sit at the same level: always-up 50.7-52.6% in DEV' (gold was up 56% of the days in 2025 at T10:05), yesterday's direction 49.9-53.8%, 20-day trend 50.8-52.1%, morning-move continuation 49.8-54.2%, fade 45.8-50.2%. Mean signed return of following the model is -0.02..+0.07 ATR per trade, i.e. nothing after costs.

## Reading
With price structure, cross-market moves, rates, gold volatility, USD strength and the calendar, the direction of the rest of a day is predictable at no better than 50-55% in-sample and 47-55% out of sample; neither model beats always-up or the trend yardsticks reliably. That is the ceiling that sits under every 1:1 design in rounds A-G: a 1:1 trade can only win as often as direction can be called, and direction can be called about as often as a slightly weighted coin.
