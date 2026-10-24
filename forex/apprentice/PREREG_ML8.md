# PREREG_ML8: how accurate can ANY model be at 1:1 from the 08:00 open? (GC futures 2020-2024)
Written 25 Oct 2026 (local clock = file time) before any outcome. the trader: "make a way to take 1:1s at 8:00 with 90% accuracy, go full open research on the data".
## Question
Using only data known at 07:59 (DIR8's 9 features + asia range / S, prev-day range / S, weekday), can a model pick days where a 1:1 bracket from the 08:00 open wins at a high rate? Report the real ceiling.
## Outcome (label)
Bracket at the 08:00 open; stop D = m x S (S = ATR14 of 15m bars to 07:59), m in {2, 4, 6}; target = D; minute bars 08:00-16:59; target first = win, stop first (or both in a bar) = loss, neither = timeout (counted as no-win for the win rate; R = signed move / D). Long and short labelled separately. Cost 0.4 pts.
## Models (fixed, no tuning)
(a) logistic regression L2 C=1 on standardised features; (b) HistGradientBoostingClassifier(max_depth=3, max_iter=100, learning_rate=0.05, random_state=0). Trained on DEV 2020-2022 only; scored on VAL 2023-2024; never refit on VAL.
## Reporting (all reported, nothing selected on VAL)
For each (m, model): take each day's best side (higher predicted win prob); rank VAL days by it; report win rate (target-first) and mean R of the top 2%, 5%, 10%, 20%, 50%, 100% with n and one-sided binomial P vs the base rate of the same label.
## Bar
PASS = top-10% VAL win rate >= 60% AND binomial P <= 0.05/6 (6 model x m cells; Bonferroni) AND top-10% mean R > 0. A 90% result would need >= 90% at n >= 30 (P < 1e-6 by luck).
## Honest prior
Under 3%: DIR8, G24, BIAS8, EMA15, SWEEP, NEWSBAR, F2PROXY all sit near 50%.
