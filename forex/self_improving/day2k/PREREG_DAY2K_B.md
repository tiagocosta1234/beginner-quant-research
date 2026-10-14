# PREREG DAY2K-B - a quality score for the one-setup-a-day, 1:1 trade (written 2026-10-14, the trader: "find a better quality setup, exactly one setup a day")

Round 1 (`DAY2K_RESULT.md`, commit 8d89bbf4) found no edge from single-pair momentum / fade signals (24 cells, 0 survivors). This round adds information that round 1 did not use and lets a model rank the 56 candidates (28 pairs x 2 sides) of each day; exactly the top-ranked candidate is taken. Same trade object, same outcome matrix R[day, pair, T, k, side] as round 1 (stop = target = k x ATR20, entry at the open of the bar T+60 s on the executable side, forced exit 21:55, tie in one bar = loss, no decision in server hours 23-0).

## Honest prior
Round 1 and 23 earlier families found nothing; learned rankers on 15-minute bars (family ml) found nothing; confluence of price-only indicators found nothing. P(survivor) before looking: under 5%. If the round is negative, the unused information is the reason to look elsewhere, not another model on the same inputs.

## Features (all causal: bars started <= T-60 s, complete previous days, calendar events published before T; all price features divided by ATR20 of the pair)
Signed (flipped for the short side): m1, m5, m20 (price change over 1/5/20 trading days at the same T), am (since 01:05), pdh and pdl (distance to the previous full day's high and low), asian-range position ((p-lo)/(hi-lo)-0.5 over 01:05..T), cs1 and cs5 (currency strength: for each of the 8 currencies the mean over the pairs that contain it of the signed normalised 1-day / 5-day change; feature = strength(base) - strength(quote)), surp (MT5 calendar: sum of signed weights of events of importance >= 2 published today before T; impact 1 = better than forecast for the currency = +, 2 = worse = -, weight 1 for importance 2, 2 for importance 3; feature = surp(base) - surp(quote)).
Symmetric: range ratio (mean daily range of the last 5 days / ATR20), asian range / ATR20, spread at T / ATR20, tick-volume ratio (tick volume 01:05..T over the mean of the same window in the previous 20 days), n_high (importance-3 events of base or quote in the next 4 hours), weekday.
Two feature sets: FULL (all) and PRICE (no surp, n_high, tick-volume ratio).

## Model and protocol
HistGradientBoostingRegressor (depth 3, 100 iterations, lr 0.06, min leaf 300, L2 1.0), target = R of the candidate, pooled over pairs and both sides. Walk-forward with an expanding window and a refit each calendar quarter; the first 12 months (2021-12..2022-11) are warm-up and never scored. A day's labels are known by 21:55 of that day, so predictions for day d use only days < d. One pick per day = the candidate with the highest predicted R (no threshold). Test periods: DEV' 2022-12-01..2024-12-31, VAL 2025-01-01..2025-12-31, HOLD 2026-01-01..2026-08-14 (calendar and tick-volume files end 2026-08-15; HOLD never loaded in the main run).

## Trials (10) and acceptance
8 ML cells = T {10:05, 16:35} x k {0.4, 0.7} x feature set {FULL, PRICE}; 2 hand cells = currency-strength continuation (the pair with the largest |cs1| traded in the direction of cs1), T {10:05, 16:35}, k 0.4. Bonferroni for 10 trials, one-sided 5%: DEV' block-t (blocks of 5 days) >= 2.58 and mean R above the baseline of the same (T,k) (baseline = mean of all candidates); VAL: mean R > 0, block-t >= 1.65, >= 200 days. A survivor is audited (by pair, side, year, month, ex-best-20-days, spread x2, IC of the score), then HOLD is opened once.

## Gates before any cell is read
- Truncation test: features recomputed from bars (and events) strictly before T equal the matrix for 40 random pair-days.
- Positive control: add the realised label to the feature set; the ranker's DEV' mean R must be clearly positive (> +0.3).
- Placebo worlds (labels permuted across days, seeds 91-93): 0 survivors in each of the three, else nothing is read.
Amendments only before any P&L and written below with the reason.

## Dry-run record and amendment A1 (2026-10-14, before any cell P&L)
- Features built for 1,066 trading days x 28 pairs x 2 T; coverage of every feature 97-100%. Truncation test (bars, tick volume and events strictly before T): 40/40 identical for all features except cs1/cs5 (built from the tested m1/m5), nhigh and surp (surp tested separately, identical).
- Calendar `impact` agrees with the sign of actual - forecast in 87.5% / 87.7% of importance >= 2 events, i.e. it already encodes the currency-relative direction (inverted indicators included), so it is used as is.
- A1 (clarification, no rule changed): `nhigh` counts importance-3 events scheduled in the next 4 hours. Release times are published in advance, so this is known at T; `surp` only uses events already published before T-60 s.
