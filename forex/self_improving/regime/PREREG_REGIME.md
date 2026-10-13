# Pre-registration: a regime layer on the installed system (written 2026-10-13, before any code of it ran)

the trader: "go ahead with the regime layer, then machine learning on the raw bars." This is the first of the two (the second gets its own pre-registration).

## What the layer is
The installed system (ManualSDB 0.18 + XAU5 0.06 = pair x1.5, plus ManualDip x0.75, guard 1,500, CPI news-flat) keeps trading exactly as it does. The layer only chooses, before each server day, a SIZE FACTOR f in {0, 0.5, 1.0, 1.5} that multiplies the whole system's size for that day (f = 1.0 is the installed system). The rule is `if cond(day) then f_on else f_off`, with `cond` = 1 or 2 conditions `feature >= / <= threshold` on daily regime features known before the day starts, f_on != f_off. Nothing on the live account changes from this study; applying any layer would be the trader's decision by hand (lots in the presets).

## Data (the FT 2022-26 pool of the installed system; the MT5 broker 12-month pool overlaps the sealed 2026 and is not used)
Daily series (V realised P&L, B lowest intraday equity, Hi) of the installed system at the four factors, built by combo_grid.pair_series (pair at 1.5 x f) + add_dip (ManualDip at 0.75 x f), guard 1,500, same days for every f. Only days up to 2025-12-31 are loaded: windows A = 2022-01..2023-06 (search), B = 2023-07..2024-12 (confirmation), VAL = 2025. 2026 (HOLD) is never loaded.
Daily features, all strictly before the day: macro regime (VIX rank and 5-day change, 10y-2y slope change, dollar index change, VIX9D/VIX, SKEW rank; FRED and CBOE series with a TWO-business-day lag because FRED publishes a day late), scheduled event flags (CPI, NFP, FOMC today, tomorrow, any), gold state from the XAUUSD 15-minute bars of previous days (5-day vs 60-day realised vol ratio, 20-day return, position in the 60-day range, previous day's range vs its median), the system's own trailing P&L at f = 1 (previous day, 5 days, 20 days), weekday. About 25 features; thresholds from window A quantiles (10, 25, 50, 75, 90%; event flags 0.5).

## Environment and score
The MT5 broker Pro 100K rules exactly as the existing simulator (forex/ea_research/pass70.py): breach if equity-from-day-start <= -2,500 or counted equity <= 92,000, profit counted at most 2,000 a day, target 8,000, pass lock OFF (as the live guard), start counted profit 0. For each start day inside a window whose 44-business-day horizon ends inside the window, the policy is replayed day by day (empirical replay, no bootstrap); P(pass by 44 bd) and P(breach by 44 bd) are the fractions over the starts. Score s = P(pass) - 3 x P(breach); delta s = s(policy) - s(constant f = 1.0) on the same starts.

## Search and tests (fixed now)
Stage A: 100,000 random policies (1-2 conditions, f_on / f_off), delta s on A starts. Promotion: the 200 best by delta s on A with delta pass > 0 and delta breach <= 0 points.
Stage B (each promoted policy once): delta s on B starts; null = common circular time shift of ALL the regime features relative to the series inside the window (300 shifts), the policy re-replayed each time; z = (observed - null mean) / null sd, one-sided p from the normal tail. Benjamini-Hochberg q = 0.05 over the 200 promoted. Economic floor on B: delta pass >= +2 points and delta breach <= +0 points.
Stage VAL (2025, one look per survivor): delta pass >= +2 points, delta breach <= +0, and shift-null p < 0.2.
Replacement-relevant outcome: a policy that passes B and VAL. Then, and only then: HOLD 2026 one look (written decision first), and a check that the live preset change it implies is feasible by hand. Nothing is applied by me.

## Calibration (before the real run)
Five placebo worlds (seeds 41-45): all regime features circularly shifted by one random offset (300-900 days) against the series, then the identical search (100,000 policies, promotion, B and VAL tests). Calibrated only if EVERY world has 0 survivors at B and VAL. If not, the failure is reported and the real run does not start.

## Expectations written now
The installed system is mostly a gold trend/breakout pair; days are few (about 900 in A+B+VAL), the regime features are slowly varying (small effective sample), and 100,000 policies is a large family. The most likely outcome is none. The earlier performance-throttle round (IMPROVE_ROUND: x1.5 / x1.0 by trailing P&L) found a free safety (breach 1.4% -> 0.0% in 2022-26) but no gain in P(pass); this study asks whether macro or gold state can do better.

Calibration gate: PASSED, with a caveat written now. Five placebo worlds (seeds 41-45, regime features rolled against the series), 100,000 policies each, 200 promoted: 0 survivors at B and 0 at VAL in every world. In world 41 the best B z was 6.12 (p 5e-10), i.e. the shift-null statistic alone would have let a false policy through; the economic floors (delta pass >= +2 points, delta breach <= 0) stopped it. The real result is therefore read with the floors as the binding constraint and the z as supporting evidence, and any survivor is described with both. Real run starts after this entry: 100,000 policies, same code, ledger REG_real.csv.
