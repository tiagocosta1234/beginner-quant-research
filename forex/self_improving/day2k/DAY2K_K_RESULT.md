# DAY2K-K result (2026-10-14): which group of FX pairs and indices has an 80%-sure next-day direction? - NONE

Pre-registration `PREREG_DAY2K_K.md` (commit 8ccf6370), engine `day2kk.py`. 28 FX pairs + SP, NSDQ, DOW, DAX, NIKKEI, ASX; decision at the 21:55 server bar, label = next trading day's close-to-close direction; 19 features incl. multi-horizon returns, range and position, weekday, month end, cross-market context, lagged rates and vol, USD calendar surprises; logistic and boosting pooled models, walk-forward from 2022-12 with a one-day embargo; 44 groups (34 markets, class x weekday). 2026 sealed. No order placed.

## Gates
Leak control 100%; placebos 191-195 for both models: 0 claims, no group reaches 80% (best fake group 59.2%). A shared-state bug (52 markets, indices counted twice) was found in the dry-run and fixed before any model ran.

## Result
**0 groups reach 80% in 2022-24 (n >= 40), 0 claims.** The best groups: ASX 56.1% (VAL 52.5%), SP 55.9% (VAL 56.4%), GBPAUD 54.8% (VAL 44.4%), NZDJPY 54.4% (VAL 52.1%). Pooled hit rate 51.3% (logit) and 49.3% (boosting) in DEV', 51.9% and 52.0% in 2025.
Reliability curve (the key diagnostic): the most confident predictions are NOT more accurate. Top 1% by confidence: logit 46.4% in DEV' and 39.5% in 2025, boosting 52.0% and 40.7%; top 5%: 50.4% / 49.3% and 52.7% / 50.5%; top 20%: 51.3% / 51.9% and 48.9% / 53.2%. A model with real knowledge shows hit rate rising with confidence; here it is flat or falls, i.e. the confidence is noise.

## Reading
For the next day's direction of these 34 markets there is no group, no confidence level, no weekday or market in which the call is right even 60% of the time out of sample, let alone 80%. This is the strongest negative so far: it holds for selective prediction, which is the most favourable framing for a classifier, and the placebo worlds (which produce 54-59% in their best cell) show how far chance alone goes.
