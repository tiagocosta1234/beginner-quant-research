# PREREG DAY2K-K - which group of FX pairs and indices has a next-day direction we are 80% sure of? (written 2026-10-14, the trader: "analyze every single forex pair and index and determine which group of symbols you're 80% sure you know its direction for the next day")

Selective prediction: the model need not call every day; the question is whether any definable group of symbol-days is called right at least 80% of the time, out of sample. The lab setting does not change the evidence rules: no orders, no live-account change, 2026 sealed.

## Object
Universe: the 28 FX pairs and 6 indices (SP, NSDQ, DOW, DAX, NIKKEI, ASX) = 34 markets. Decision at the 21:55 server bar of day d (all bars up to 21:54, rates/vol macro lagged as in round E); label y = 1 if mid(21:55 bar open of day d+1) > mid(21:55 bar open of day d) (the next trading day's close-to-close move, spread ignored for the accuracy statistic). Training rows for a prediction on day d use only labels known by then (a one-day embargo: label of day d-1 needs day d's price).
Features (ATR20-normalised): 1, 2, 5, 10, 20, 60-day changes, today's range / ATR20, position in the 20-day range, weekday, month-end flag, plus day-level context: mean 1-day change of the 6 indices, USD strength index of the 7 USD pairs, mean 1-day change of all 34; lagged DGS2, DFII10, GVZ, VIX changes; USD calendar surprises of the day and importance-3 USD events tomorrow.
Models (2): L2 logistic regression and depth-2 gradient boosting, pooled over markets, walk-forward with a quarterly refit and an expanding window, scored from 2022-12-01 (DEV' 2022-12..2024-12, VAL 2025, HOLD 2026 sealed).

## Groups and the claim
Groups (44): each of the 34 markets; class x weekday (FX or index x Mon..Fri = 10). Confidence bins (pooled): predictions ranked by |p - 0.5| into the top 1%, 2%, 5%, 10%, 20%, and the full set (reliability curve, hit rate per probability bin).
A CLAIM is a group-model cell with DEV' n >= 40 predictions, DEV' hit rate >= 0.80, and VAL n >= 20 with VAL hit rate >= 0.75. The lab's answer is the number of claims in the real data compared with the number produced by the same procedure on placebo worlds (labels permuted across days, seeds 191-195): the real run counts only if it has strictly more claims than every placebo world AND each claim's VAL hit rate has a one-sided binomial p <= 0.01 against 0.55.

## Gates
Positive control: label leaked as a feature must give hit rate > 95%. Truncation: random rows' features recomputed from bars before 21:55 are identical.

## Honest prior
Published daily-direction accuracy is 50-55% even at the most confident decile; a group at 80% would be a +0.6 R per trade edge. P(a genuine claim) under 2%. The expected finding is that high-confidence predictions are not more accurate than low-confidence ones (a flat reliability curve) and that the groups that reach 80% in 2022-24 on small samples fall back to about 50% in 2025.

## Dry-run record (2026-10-14, before any model result)
1,066 days x 34 markets (28 FX + 6 indices), 35,169 rows with a next-day label, up-rate 51.5%, feature coverage 89-100%. The first build showed 52 markets because importing the round-C module widens the shared pair list (the six indices were counted twice); the market list is now fixed explicitly and the cache rebuilt, before any model was run. Truncation test (previous day's change recomputed from bars before the decision) 25/25. No trial, group or threshold changed.
