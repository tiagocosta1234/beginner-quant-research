# Free-form trader v6 (M1 information, price-pattern vocabulary, all available series, MT5 broker environment): result (2026-10-13)

Pre-registration: PREREG_V6_M1.md (plus PREREG_V5_PROP.md and PREREG_FREEFORM.md). Code: ff6_data.py, ff6_agent.py, acct_env.py. Ledgers (outside git): data\si_ledgers\FF10_*. 2026 never loaded.

## What the agent saw
All M1 bid/ask OHLC bars (2021-12..2026-10, 46 symbols) aggregated into 15-minute decision bars with the M1 statistics of each bar (1-minute variance, Parkinson variance, moving minutes, up share, mean / max / last spread, last-5-minute return, largest 1-minute range); decisions at every bar close, entry at the next bar open, exits 15 minutes to 2 days later, real bid and ask at both ends. 87 causal features (checked: cutting the future changes none of the 85 non-cross-sectional ones): price at several scales, micro-structure, time, previous-day and today's levels, round numbers, candle patterns (body and wick shares, range vs median, engulfing, inside bar, run) on 15m and 60m bars, fractal swings and the HH/HL state, the latest unfilled fair-value gap, an order-block proxy, the macro event calendar, the daily macro regime (VIX rank, curve, dollar, VIX9D/VIX, SKEW), crypto sentiment and funding, cross-sectional ranks. Real ticks exist only since 2025-10-01 and were not usable for training.
Environment: MT5 broker Pro 100K rules, USD 500 risk per trade with a USD 1,000 total open-risk cap, stop at 2 volatility units, 0.2 bp slippage, the MT5 broker pass simulator; the agent's elites and operator weights follow the environment score.

## Calibration: PASSED
Placebo worlds 31, 32, 33 (every 15-minute bar shuffled, patterns recomputed on the shuffled bars, calendar and daily macro real): 0 S1 and 0 S2 in each, 40,000 rules each.

## Real run (100 generations): 173,831 rules explored
| | value |
|---|---|
| rules meeting the A floors | 49,729 |
| best A z | 4.88 |
| B tests (promoted from A) | 11,646 |
| best B z (min p) | 2.46 (1.0e-2) |
| BH q = 0.05 needs p <= | 4.3e-6 |
| S1 | **0** |
| S2 | **0** |
| rules scored in the environment on A | 3,614 |
| best environment score on A | 0.111 |
| max P(pass by 44 bd) of a rule alone on A | 11.4% (breach 0.1%); 28 rules above 10% |
| top-500 B rules using a pattern / level feature | 97% |
Window B is where chance is judged: of 11,646 promoted rules the best has z 2.46, LESS than the best of 11,000 null tests would give (about 3.7): the rules that looked best on A regress in B. The best rule by B p (idx short, 4-hour hold, VIX9D/VIX low and long since CPI; net +0.6 bp) is noise.

## Verdict
With M1-derived micro-structure, the classic price-pattern vocabulary (candles, swings, FVG, order blocks, daily levels, round numbers) and every macro and sentiment series we hold, evaluated in the MT5 broker account environment, no rule among 174,000 explored survives a calibrated test. The installed system stays on the account. 2026 not read; nothing reached S3, the add-on test, or the tester.

## What this leaves open
1. Information the data does not have (consensus forecasts / event surprises, real ticks before 2025-10, order flow, positioning beyond the COT files, news text).
2. Decision at every minute and shorter horizons (spread-dominated; not expected to help).
3. A regime layer on the installed system (the part that works), tested in the same environment.
4. Machine learning on the raw 15-minute windows (the second route offered to the trader), with the same placebo and window discipline.
